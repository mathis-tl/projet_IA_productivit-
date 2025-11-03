"""Task model"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from datetime import datetime
from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True, index=True)
    
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True, index=True)
    priority = Column(String, default="medium")
    status = Column(String, default="todo")
    
    tags = Column(JSON, nullable=True)
    sub_checklist = Column(JSON, nullable=True)
    recurrence = Column(String, nullable=True)
    ai_suggested = Column(Boolean, default=False)
    
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)