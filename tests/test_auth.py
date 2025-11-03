import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.config import settings
import uuid

# Engine de test (SQLite en mémoire, plus rapide)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override la dépendance get_db
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_signup_success():
    """Test : créer un utilisateur avec succès"""
    unique_id = str(uuid.uuid4())[:8]
    response = client.post("/auth/signup", json={
        "email": f"signup_{unique_id}@example.com",
        "username": f"testuser_signup_{unique_id}",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == f"signup_{unique_id}@example.com"
    assert data["username"] == f"testuser_signup_{unique_id}"
    assert "id" in data
    assert "password_hash" not in data  # Le password ne doit pas être retourné

def test_signup_duplicate_email():
    """Test : impossible de créer 2 users avec le même email"""
    unique_id = str(uuid.uuid4())[:8]
    email = f"duplicate_{unique_id}@example.com"
    client.post("/auth/signup", json={
        "email": email,
        "username": f"user1_dup_{unique_id}",
        "password": "password123"
    })
    response = client.post("/auth/signup", json={
        "email": email,
        "username": f"user2_dup_{unique_id}",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "Email déjà utilisé" in response.json()["detail"]

def test_login_success():
    """Test : se connecter avec succès"""
    unique_id = str(uuid.uuid4())[:8]
    email = f"login_{unique_id}@example.com"
    username = f"loginuser_{unique_id}"
    client.post("/auth/signup", json={
        "email": email,
        "username": username,
        "password": "password123"
    })
    response = client.post("/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    """Test : impossible de se connecter avec un mauvais password"""
    unique_id = str(uuid.uuid4())[:8]
    email = f"wrongpass_{unique_id}@example.com"
    username = f"wronguser_{unique_id}"
    client.post("/auth/signup", json={
        "email": email,
        "username": username,
        "password": "correctpassword"
    })
    response = client.post("/auth/login", json={
        "email": email,
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"]

def test_health_z():
    """Test : l'endpoint health fonctionne"""
    response = client.get("/health/z")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"