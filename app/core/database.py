from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from os import getenv

DATABASE_URL = getenv("DATABASE_URL", "postgresql+psycopg://studypilot:studypilot@db:5432/studypilot")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dépendance sessionDB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()