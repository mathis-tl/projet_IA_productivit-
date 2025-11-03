import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.models.page import Page
from app.core.security import create_access_token

# Utiliser la même DB que conftest.py
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def test_user():
    """Créer un utilisateur test"""
    db = TestingSessionLocal()
    user = User(email="test_pages@example.com", username="testuser_pages")
    user.set_password("testpass123")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

@pytest.fixture
def auth_token(test_user):
    """Créer un JWT token pour l'utilisateur test"""
    return create_access_token(test_user.id, test_user.email)

# ========== TEST CREATE PAGE ==========
def test_create_page_success(auth_token):
    """Tester la création réussie d'une page"""
    response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Ma Page", "description": "Description", "icon": "📝"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Ma Page"
    assert data["description"] == "Description"
    assert data["icon"] == "📝"
    assert data["is_archived"] == False
    assert "id" in data
    assert "created_at" in data

def test_create_page_missing_token():
    """Tester la création sans token"""
    response = client.post(
        "/pages",
        json={"title": "Ma Page"}
    )
    assert response.status_code == 401

def test_create_page_invalid_token(auth_token):
    """Tester avec un token invalide"""
    response = client.post(
        "/pages",
        headers={"Authorization": "Bearer invalid_token"},
        json={"title": "Ma Page"}
    )
    assert response.status_code == 401

# ========== TEST LIST PAGES ==========
def test_list_pages_empty(auth_token, test_user):
    """Tester la liste vide de pages"""
    response = client.get(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []

def test_list_pages_success(auth_token, test_user):
    """Tester la liste des pages de l'utilisateur"""
    # Créer 3 pages
    client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Page 1"}
    )
    client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Page 2"}
    )
    client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Page 3"}
    )
    
    response = client.get(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "Page 1"
    assert data[1]["title"] == "Page 2"
    assert data[2]["title"] == "Page 3"

def test_list_pages_excludes_archived(auth_token, test_user):
    """Tester que les pages archivées ne sont pas listées"""
    # Créer et archiver une page
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test_pages@example.com").first()
    page = Page(user_id=user.id, title="Page archivée", is_archived=True)
    db.add(page)
    db.commit()
    db.close()
    
    # Créer une page normale
    client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Page normale"}
    )
    
    response = client.get(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Page normale"

# ========== TEST GET PAGE ==========
def test_get_page_success(auth_token, test_user):
    """Tester la récupération d'une page spécifique"""
    # Créer une page
    create_response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Ma Page"}
    )
    page_id = create_response.json()["id"]
    
    # Récupérer
    response = client.get(
        f"/pages/{page_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == page_id
    assert data["title"] == "Ma Page"

def test_get_page_not_found(auth_token):
    """Tester la récupération d'une page inexistante"""
    response = client.get(
        "/pages/999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_get_page_unauthorized(auth_token, test_user):
    """Tester qu'on ne peut pas accéder aux pages d'un autre utilisateur"""
    # Créer une page pour le user test
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test_pages@example.com").first()
    page = Page(user_id=user.id, title="Page privée")
    db.add(page)
    db.commit()
    page_id = page.id
    db.close()
    
    # Créer un autre utilisateur
    db = TestingSessionLocal()
    other_user = User(email="other_pages@example.com", username="otheruser_pages")
    other_user.set_password("pass")
    db.add(other_user)
    db.commit()
    other_user_id = other_user.id
    other_user_email = other_user.email
    db.close()
    
    other_token = create_access_token(other_user_id, other_user_email)
    
    # Essayer d'accéder à la page du premier user
    response = client.get(
        f"/pages/{page_id}",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert response.status_code == 404

# ========== TEST UPDATE PAGE ==========
def test_update_page_success(auth_token, test_user):
    """Tester la modification d'une page"""
    # Créer
    create_response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Titre original", "icon": "📝"}
    )
    page_id = create_response.json()["id"]
    
    # Modifier
    response = client.put(
        f"/pages/{page_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Titre modifié", "icon": "🎯"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Titre modifié"
    assert data["icon"] == "🎯"

def test_update_page_partial(auth_token, test_user):
    """Tester la modification partielle d'une page"""
    # Créer
    create_response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Original", "description": "Desc original", "icon": "📝"}
    )
    page_id = create_response.json()["id"]
    
    # Modifier seulement le titre
    response = client.put(
        f"/pages/{page_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Nouveau titre"}
    )
    data = response.json()
    assert data["title"] == "Nouveau titre"
    assert data["description"] == "Desc original"  # Non modifiée
    assert data["icon"] == "📝"  # Non modifiée

def test_update_page_not_found(auth_token):
    """Tester la modification d'une page inexistante"""
    response = client.put(
        "/pages/999",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Nouveau"}
    )
    assert response.status_code == 404

# ========== TEST DELETE PAGE ==========
def test_delete_page_success(auth_token, test_user):
    """Tester la suppression (soft delete) d'une page"""
    # Créer
    create_response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "À supprimer"}
    )
    page_id = create_response.json()["id"]
    
    # Supprimer
    response = client.delete(
        f"/pages/{page_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    
    # Vérifier que la page est archivée (soft delete)
    get_response = client.get(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert len(get_response.json()) == 0

def test_delete_page_not_found(auth_token):
    """Tester la suppression d'une page inexistante"""
    response = client.delete(
        "/pages/999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404
