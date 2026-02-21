from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Run, Task

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
