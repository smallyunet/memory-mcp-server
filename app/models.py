from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
import datetime

class Record(Base):
    """Database table for user records."""
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    category = Column(String, default="general")
    summary = Column(Text)
    detail = Column(Text)
    tags = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
