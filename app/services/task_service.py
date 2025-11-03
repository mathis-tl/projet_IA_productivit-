"""Task service"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.models.task import Task


def get_today_tasks(db: Session, user_id: int) -> List[Task]:
    today = datetime.today().date()
    day_start = datetime.combine(today, datetime.min.time())
    day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())
    
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_archived == False,
        Task.due_date >= day_start,
        Task.due_date < day_end
    ).all()


def get_overdue_tasks(db: Session, user_id: int) -> List[Task]:
    today = datetime.today().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_archived == False,
        Task.due_date < today_start,
        Task.status != 'done'
    ).all()


def get_this_week_tasks(db: Session, user_id: int) -> List[Task]:
    today = datetime.today().date()
    days_until_end = (6 - today.weekday()) % 7
    if days_until_end == 0:
        days_until_end = 7
    
    week_end = today + timedelta(days=days_until_end)
    day_start = datetime.combine(today, datetime.min.time())
    end_time = datetime.combine(week_end, datetime.max.time())
    
    return db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_archived == False,
        Task.due_date >= day_start,
        Task.due_date <= end_time
    ).all()
