from datetime import datetime

import structlog

from ..database import SessionLocal
from ..models.task import Task

logger = structlog.get_logger(__name__)


def create_task(
    task_type: str,
    title: str,
    *,
    status: str = "running",
    ruleset_id: int | None = None,
    paper_id: int | None = None,
    run_id: int | None = None,
    digest_type: str | None = None,
    db=None,
) -> Task:
    task = Task(
        task_type=task_type,
        status=status,
        title=title,
        ruleset_id=ruleset_id,
        paper_id=paper_id,
        run_id=run_id,
        digest_type=digest_type,
    )
    if db:
        db.add(task)
        db.commit()
        db.refresh(task)
    else:
        _db = SessionLocal()
        try:
            _db.add(task)
            _db.commit()
            _db.refresh(task)
            task_id = task.id
        finally:
            _db.close()
        task.id = task_id
    return task


def complete_task(task_id: int, *, digest_id: int | None = None):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            if digest_id is not None:
                task.digest_id = digest_id
            db.commit()
    finally:
        db.close()


def fail_task(task_id: int, error: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def update_task(task_id: int, **kwargs):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            db.commit()
    finally:
        db.close()
