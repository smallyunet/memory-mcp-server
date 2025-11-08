from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
import datetime

class Command(Base):
    """Single-user command memory entries captured via REST API.

    Simplified for single-user mode: no user_id column.
    """
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    command_text = Column(Text, nullable=False)
    tags = Column(String)  # comma-separated list
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True, nullable=False)
