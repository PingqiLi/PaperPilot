from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON

from .paper import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(30), nullable=False)
    status = Column(String(30), default="running")
    title = Column(String(200), nullable=False)

    ruleset_id = Column(Integer)
    paper_id = Column(Integer)
    run_id = Column(Integer)
    digest_id = Column(Integer)
    digest_type = Column(String(30))

    error = Column(Text)
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
