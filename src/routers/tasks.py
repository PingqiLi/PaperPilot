from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RuleSet, Run, Task
from ..services.task_manager import create_task
from ..services.pipeline import run_initialize, run_track

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: str
    status: str
    title: str
    ruleset_id: Optional[int] = None
    paper_id: Optional[int] = None
    run_id: Optional[int] = None
    digest_id: Optional[int] = None
    digest_type: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    progress: Optional[dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]


def _enrich_progress(task: Task, db: Session) -> dict[str, Any] | None:
    if task.run_id:
        run = db.query(Run).filter(Run.id == task.run_id).first()
        if run and run.progress:
            return dict(run.progress)
    return None


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.filter(Task.status.in_(statuses))
    total = query.count()
    rows = query.order_by(Task.created_at.desc()).limit(limit).all()

    items = []
    for task in rows:
        resp = TaskResponse.model_validate(task)
        resp.progress = _enrich_progress(task, db)
        items.append(resp)
    return TaskListResponse(total=total, items=items)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = TaskResponse.model_validate(task)
    resp.progress = _enrich_progress(task, db)
    return resp


RETRYABLE_TYPES = {"topic_init": "initialize", "track": "track"}


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "failed":
        raise HTTPException(status_code=400, detail="只能重试失败的任务")
    run_type = RETRYABLE_TYPES.get(task.task_type)
    if not run_type or not task.ruleset_id:
        raise HTTPException(status_code=400, detail="该任务类型不支持重试")

    ruleset = db.query(RuleSet).filter(RuleSet.id == task.ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="关联的规则集不存在")

    active_run = db.query(Run).filter(
        Run.ruleset_id == task.ruleset_id,
        Run.status.in_(["pending", "running"]),
    ).first()
    if active_run:
        raise HTTPException(status_code=409, detail="该主题已有运行中的任务")

    run = Run(ruleset_id=task.ruleset_id, run_type=run_type)
    db.add(run)
    db.commit()
    db.refresh(run)

    type_label = "Initialize" if run_type == "initialize" else "Track"
    new_task = create_task(
        task.task_type, f"{type_label}: {ruleset.name}",
        ruleset_id=task.ruleset_id, run_id=run.id,
    )

    if run_type == "initialize":
        background_tasks.add_task(run_initialize, run.id, task.ruleset_id, new_task.id)
    else:
        background_tasks.add_task(run_track, run.id, task.ruleset_id, new_task.id)

    resp = TaskResponse(
        id=new_task.id,
        task_type=new_task.task_type,
        status=new_task.status,
        title=new_task.title,
        ruleset_id=new_task.ruleset_id,
        run_id=new_task.run_id,
        created_at=new_task.created_at or datetime.now(timezone.utc),
    )
    resp.progress = _enrich_progress(new_task, db)
    return resp
