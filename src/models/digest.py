from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from .paper import Base


class Digest(Base):
    __tablename__ = "digests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"), nullable=False)
    digest_type = Column(String(20), nullable=False)
    content = Column(JSON, nullable=False)
    paper_count = Column(Integer, default=0)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    ruleset = relationship("RuleSet", backref="digests")
