from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from .paper import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False)
    error = Column(Text)
    digest_id = Column(Integer, ForeignKey("digests.id"))
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"))
    topic_name = Column(String(200))
    digest_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
