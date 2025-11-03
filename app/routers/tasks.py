from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import (
    get_today_tasks,
    get_overdue_tasks,
    get_this_week_tasks
)

router = APIRouter(prefix="/tasks")


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> User:
    # Check token
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_task = Task(
        user_id=current_user.id,
        page_id=task_data.page_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority,
        status=task_data.status,
        tags=task_data.tags,
        sub_checklist=task_data.sub_checklist,
        recurrence=task_data.recurrence
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None),
    priority_filter: Optional[str] = Query(None),
    page_id: Optional[int] = Query(None)
):
    query = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.is_archived == False
    )
    
    if status_filter and status_filter in ["todo", "in_progress", "done", "cancelled"]:
        query = query.filter(Task.status == status_filter)
    
    if priority_filter and priority_filter in ["low", "medium", "high", "urgent"]:
        query = query.filter(Task.priority == priority_filter)
    
    if page_id:
        query = query.filter(Task.page_id == page_id)
    
    return query.order_by(Task.created_at.desc()).all()


@router.get("/today", response_model=List[TaskResponse])
def today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_today_tasks(db, current_user.id)


@router.get("/overdue", response_model=List[TaskResponse])
def overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_overdue_tasks(db, current_user.id)


@router.get("/this-week", response_model=List[TaskResponse])
def this_week(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_this_week_tasks(db, current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id,
        Task.is_archived == False
    ).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task.is_archived = True
    db.commit()


@router.post("/{task_id}/status", response_model=TaskResponse)
def update_status(
    task_id: int,
    new_status: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    valid_statuses = ["todo", "in_progress", "done", "cancelled"]
    
    if new_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task.status = new_status
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/checklist", response_model=TaskResponse)
def update_checklist(
    task_id: int,
    checklist: List[dict] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task.sub_checklist = checklist
    db.commit()
    db.refresh(task)
    return task