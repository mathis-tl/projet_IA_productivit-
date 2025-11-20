from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime, date
from app.core.database import Base
import bcrypt

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Gamification fields
    current_streak = Column(Integer, default=0)
    last_task_completed = Column(DateTime, nullable=True)
    days_without_tasks = Column(Integer, default=0)
    inventory = Column(JSON, default=[])  # Liste des objets débloqués

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())