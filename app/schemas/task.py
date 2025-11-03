"""Pydantic schemas for task request/response validation."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any


from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any

# Schemas tâches

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    page_id: Optional[int] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"
    status: str = "todo"
    tags: Optional[List[str]] = None
    sub_checklist: Optional[List[dict[str, Any]]] = None
    recurrence: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    page_id: Optional[int] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    sub_checklist: Optional[List[dict[str, Any]]] = None
    recurrence: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    user_id: int
    page_id: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    status: str
    tags: Optional[List[str]]
    sub_checklist: Optional[List[dict[str, Any]]]
    recurrence: Optional[str]
    ai_suggested: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    page_id: Optional[int] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    sub_checklist: Optional[List[dict[str, Any]]] = None
    recurrence: Optional[str] = None


class TaskResponse(BaseModel):
    """Schema for task responses from API."""
    
    id: int
    user_id: int
    page_id: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    status: str
    tags: Optional[List[str]]
    sub_checklist: Optional[List[dict[str, Any]]]
    recurrence: Optional[str]
    ai_suggested: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)