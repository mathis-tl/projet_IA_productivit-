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
from app.core.security import create_access_token
from datetime import datetime, timedelta

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
    user = User(email="test_tasks@example.com", username="testuser_tasks")
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

# ========== TEST CREATE TASK ==========
def test_create_task_success(auth_token):
    """Tester la création réussie d'une tâche"""
    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Ma première tâche", "priority": "high", "status": "todo"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Ma première tâche"
    assert data["priority"] == "high"
    assert data["status"] == "todo"
    assert data["ai_suggested"] == False

def test_create_task_with_tags(auth_token):
    """Tester la création d'une tâche avec tags"""
    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "title": "Tâche urgente",
            "tags": ["travail", "urgent", "à faire aujourd'hui"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["tags"]) == 3
    assert "urgent" in data["tags"]

def test_create_task_with_checklist(auth_token):
    """Tester la création d'une tâche avec sub-checklist"""
    checklist = [
        {"id": 1, "text": "Étape 1", "done": False},
        {"id": 2, "text": "Étape 2", "done": False}
    ]
    response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche avec checklist", "sub_checklist": checklist}
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["sub_checklist"]) == 2
    assert data["sub_checklist"][0]["text"] == "Étape 1"

# ========== TEST LIST TASKS ==========
def test_list_tasks_empty(auth_token):
    """Tester la liste vide des tâches"""
    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []

def test_list_tasks_success(auth_token):
    """Tester la liste des tâches"""
    # Créer 3 tâches
    client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche 1"}
    )
    client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche 2"}
    )
    client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche 3"}
    )
    
    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

#TEST FILTER
def test_filter_tasks_by_priority(auth_token):
    """Tester le filtrage par priorité"""
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "Low", "priority": "low"})
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "High 1", "priority": "high"})
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "High 2", "priority": "high"})
    
    response = client.get(
        "/tasks?priority_filter=high",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    data = response.json()
    assert len(data) == 2
    assert all(t["priority"] == "high" for t in data)

def test_filter_tasks_by_status(auth_token):
    """Tester le filtrage par statut"""
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "Todo", "status": "todo"})
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "Done 1", "status": "done"})
    client.post("/tasks", headers={"Authorization": f"Bearer {auth_token}"}, json={"title": "Done 2", "status": "done"})
    
    response = client.get(
        "/tasks?status_filter=done",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    data = response.json()
    assert len(data) == 2
    assert all(t["status"] == "done" for t in data)

#TEST UPDATE TASK
def test_update_task_success(auth_token):
    """Tester la modification d'une tâche"""
    # Créer
    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche originale", "priority": "low"}
    )
    task_id = create_response.json()["id"]
    
    # Modifier
    response = client.put(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche modifiée", "priority": "high"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Tâche modifiée"
    assert data["priority"] == "high"

#TEST UPDATE TASK STATUS
def test_update_task_status(auth_token):
    """Tester le changement de statut d'une tâche"""
    # Créer
    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche", "status": "todo"}
    )
    task_id = create_response.json()["id"]
    # Changer le statut
    response = client.post(
        f"/tasks/{task_id}/status?new_status=in_progress",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"

# TEST UPDATE CHECKLIST
def test_update_task_checklist(auth_token):
    """Tester la mise à jour de la checklist"""
    # Créer
    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Tâche avec checklist"}
    )
    task_id = create_response.json()["id"]
    
    # Maj checklist
    new_checklist = [
        {"id": 1, "text": "Fait", "done": True},
        {"id": 2, "text": "À faire", "done": False}
    ]
    response = client.post(
        f"/tasks/{task_id}/checklist",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=new_checklist
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sub_checklist"][0]["done"] == True
    assert data["sub_checklist"][1]["done"] == False

#TEST DELETE TASK
def test_delete_task_success(auth_token):
    """Tester la suppression d'une tâche"""
    # Créer
    create_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "À supprimer"}
    )
    task_id = create_response.json()["id"]
     # Supp
    response = client.delete(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    
    # Vérif tâche pas listée
    list_response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert len(list_response.json()) == 0


# TEST CREATE TASK FROM TEXT (NLP)
def test_create_task_from_text_simple(auth_token):
    """Créer une tâche simple via texte"""
    response = client.post(
        "/tasks/from-text",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Appeler Jean demain"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Appeler Jean demain"
    assert data["status"] == "todo"
    assert data["ai_suggested"] == True


def test_create_task_from_text_with_priority(auth_token):
    """Créer une tâche avec priorité détectée via NLP"""
    response = client.post(
        "/tasks/from-text",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Urgent: finir le rapport aujourd'hui"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "high"  # "urgent" → priorité haute


def test_create_task_from_text_with_date(auth_token):
    """Créer une tâche avec date détectée si possible"""
    response = client.post(
        "/tasks/from-text",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Réunion demain à 14h avec l'équipe"}
    )
    assert response.status_code == 201
    data = response.json()
    # Peut avoir une date ou pas, selon la détection spacy
    # On vérifie juste que la tâche est créée
    assert data["title"] is not None


def test_create_task_from_text_low_priority(auth_token):
    """Créer une tâche avec basse priorité"""
    response = client.post(
        "/tasks/from-text",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Quand tu peux: lire cet article"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "low"


def test_create_task_from_text_with_entities(auth_token):
    """Créer une tâche avec entités (personnes, lieux, etc.)"""
    response = client.post(
        "/tasks/from-text",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Appeler Marie et Pierre à Paris pour le projet"}
    )
    assert response.status_code == 201
    data = response.json()
    # Description devrait contenir les entités extraites
    assert "description" in data
    assert len(data["description"]) > 0

