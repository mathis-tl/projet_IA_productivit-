import sys
from pathlib import Path

# Ajoute la racine du projet au PYTHONPATH EN PREMIER
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Créer engine SQLite pour tests AVANT d'importer app
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# PATCH: remplacer le engine et SessionLocal du core.database AVANT d'importer app
import app.core.database
app.core.database.engine = test_engine
app.core.database.SessionLocal = TestingSessionLocal

# Maintenant importer app (qui utilisera notre engine SQLite)
from app.core.database import Base, get_db
from app.main import app

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    """Crée et nettoie la DB avant/après chaque test"""
    # Nettoie avant le test
    Base.metadata.drop_all(bind=test_engine)
    # Crée les tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Nettoie après le test
    Base.metadata.drop_all(bind=test_engine)

# Override la dépendance
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Client de test FastAPI"""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def db():
    """Session DB pour les tests"""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def auth_token(client, db):
    """Crée un utilisateur et retourne son token JWT"""
    from app.models.user import User
    
    # Créer un utilisateur
    signup_response = client.post(
        "/auth/signup",
        json={"email": "test@example.com", "username": "testuser", "password": "pass123"}
    )
    
    # Se connecter pour avoir un token
    login_response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "pass123"}
    )
    
    return login_response.json()["access_token"]
