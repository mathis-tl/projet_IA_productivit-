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
    user = User(email="test_blocks@example.com", username="testuser_blocks")
    user.set_password("testpass123")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

@pytest.fixture
def auth_token(test_user):
    """Créer un JWT token"""
    return create_access_token(test_user.id, test_user.email)

@pytest.fixture
def test_page(test_user, auth_token):
    """Créer une page test"""
    response = client.post(
        "/pages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Test Page"}
    )
    return response.json()

# ========== TEST CREATE BLOCK ==========
def test_create_block_success(auth_token, test_page):
    """Tester la création réussie d'un block"""
    response = client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Mon premier block", "order": 0}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "text"
    assert data["content"] == "Mon premier block"
    assert data["order"] == 0
    assert data["page_id"] == test_page['id']

def test_create_block_with_metadata(auth_token, test_page):
    """Tester la création d'un block avec metadata"""
    response = client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "type": "text",
            "content": "Block avec metadata",
            "order": 1,
            "block_metadata": {"color": "red", "fontSize": 14}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["block_metadata"]["color"] == "red"
    assert data["block_metadata"]["fontSize"] == 14

# ========== TEST LIST BLOCKS ==========
def test_list_blocks_empty(auth_token, test_page):
    """Tester la liste vide des blocks"""
    response = client.get(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []

def test_list_blocks_ordered(auth_token, test_page):
    """Tester que les blocks sont retournés ordonnés"""
    # Créer 3 blocks
    client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Block 1", "order": 2}
    )
    client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Block 0", "order": 0}
    )
    client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Block 1.5", "order": 1}
    )
    
    response = client.get(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    data = response.json()
    assert len(data) == 3
    assert data[0]["order"] == 0
    assert data[1]["order"] == 1
    assert data[2]["order"] == 2

# ========== TEST UPDATE BLOCK ==========
def test_update_block_success(auth_token, test_page):
    """Tester la modification d'un block"""
    # Créer
    create_response = client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Original"}
    )
    block_id = create_response.json()["id"]
    
    # Modifier
    response = client.put(
        f"/blocks/{block_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"content": "Contenu modifié", "type": "heading"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Contenu modifié"
    assert data["type"] == "heading"

# ========== TEST DELETE BLOCK ==========
def test_delete_block_success(auth_token, test_page):
    """Tester la suppression d'un block"""
    # Créer
    create_response = client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "À supprimer"}
    )
    block_id = create_response.json()["id"]
    
    # Supprimer
    response = client.delete(
        f"/blocks/{block_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204

# ========== TEST REORDER BLOCKS ==========
def test_reorder_block(auth_token, test_page):
    """Tester la réorganisation d'un block"""
    # Créer un block
    create_response = client.post(
        f"/blocks/pages/{test_page['id']}/blocks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"type": "text", "content": "Block", "order": 0}
    )
    block_id = create_response.json()["id"]
    
    # Réorganiser
    response = client.post(
        f"/blocks/{block_id}/reorder",
        headers={"Authorization": f"Bearer {auth_token}"},
        params={"new_order": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["block"]["order"] == 5
