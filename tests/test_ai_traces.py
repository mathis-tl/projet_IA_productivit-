import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.models.page import Page
from app.models.task import Task
from app.core.security import create_access_token
import uuid

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

# Client HTTP pour faire les requêtes
client = TestClient(app)

# Fonction helper pour créer un user ET son token
def create_user_and_get_token():
    """Crée un user directement en BD et génère un token JWT."""
    unique_id = str(uuid.uuid4())[:8]
    db = TestingSessionLocal()
    
    user = User(
        email=f"user{unique_id}@test.com",
        username=f"user{unique_id}"
    )
    user.set_password("password123")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user.id, user.email)
    db.close()
    
    return token

# Fonction helper pour créer une page
def create_page(token):
    """Crée une page via l'API /pages. Retourne l'ID de la page créée."""
    response = client.post(
        "/pages",
        json={"title": "Test Page", "description": "Description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["id"]

# Fonction helper pour créer une tâche
def create_task(token, page_id=None):
    """Crée une tâche via l'API /tasks. Retourne l'ID de la tâche créée."""
    response = client.post(
        "/tasks",
        json={
            "title": "Test Task",
            "description": "Description",
            "page_id": page_id,
            "status": "todo",
            "priority": "medium"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["id"]

# ============ TESTS ============

def test_create_ai_trace_success():
    """
    TEST 1: Logger une trace IA avec succès.
    
    LOGIQUE:
    1. Créer un user
    2. POST /ai-traces avec analysis_type, generated_content, success=True
    3. Vérifier status = 201 Created
    4. Vérifier que la trace contient les bonnes données
    """
    token = create_user_and_get_token()
    page_id = create_page(token)
    
    response = client.post(
        "/ai-traces",
        json={
            "page_id": page_id,
            "analysis_type": "summarize",
            "source_blocks": [1, 2, 3],
            "generated_content": "Summary of the page content",
            "model_used": "mistral:7b",
            "tokens_used": 234,
            "execution_time_ms": 1234,
            "success": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    trace = response.json()
    assert trace["analysis_type"] == "summarize"
    assert trace["generated_content"] == "Summary of the page content"
    assert trace["success"] is True
    assert trace["error_message"] is None
    assert "id" in trace

def test_create_ai_trace_with_error():
    """
    TEST 2: Logger une trace IA avec erreur (success=False).
    
    LOGIQUE:
    1. Créer un user
    2. POST /ai-traces avec success=False et error_message
    3. Vérifier que la trace enregistre l'erreur
    
    USE CASE:
    - Si l'analyse IA a échoué (timeout, modèle crash, etc.)
    - On veut tracer POURQUOI ça a échoué
    """
    token = create_user_and_get_token()
    page_id = create_page(token)
    
    response = client.post(
        "/ai-traces",
        json={
            "page_id": page_id,
            "analysis_type": "summarize",
            "source_blocks": [1, 2],
            "generated_content": "",  # Pas de contenu (l'analyse a échoué)
            "model_used": "mistral:7b",
            "success": False,
            "error_message": "Model timeout after 30 seconds"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    trace = response.json()
    assert trace["success"] is False
    assert trace["error_message"] == "Model timeout after 30 seconds"

def test_create_ai_trace_for_task():
    """
    TEST 3: Logger une trace IA pour une TÂCHE (pas une page).
    
    LOGIQUE:
    1. Créer une tâche
    2. POST /ai-traces avec task_id (pas page_id)
    3. Vérifier que task_id est enregistré
    
    USE CASE:
    - NLP: parser une description de tâche "demain 14h réunion" → {"date": "2025-10-23", "time": "14:00"}
    - On trace quelle analyse IA a été utilisée sur cette tâche
    """
    token = create_user_and_get_token()
    task_id = create_task(token)
    
    response = client.post(
        "/ai-traces",
        json={
            "task_id": task_id,
            "page_id": None,
            "analysis_type": "parse_calendar",
            "generated_content": '{"date": "2025-10-23", "time": "14:00"}',
            "model_used": "spacy:fr",
            "success": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    trace = response.json()
    assert trace["task_id"] == task_id
    assert trace["page_id"] is None

def test_list_ai_traces():
    """
    TEST 4: Récupérer TOUTES les traces IA de l'utilisateur.
    
    LOGIQUE:
    1. Créer 3 traces différentes
    2. GET /ai-traces
    3. Vérifier qu'on reçoit 3 traces
    4. Vérifier qu'elles sont triées par created_at DESC (plus récentes d'abord)
    """
    token = create_user_and_get_token()
    page_id = create_page(token)
    
    # Créer 3 traces
    for i in range(3):
        client.post(
            "/ai-traces",
            json={
                "page_id": page_id,
                "analysis_type": f"analysis_{i}",
                "generated_content": f"Content {i}",
                "success": True
            },
            headers={"Authorization": f"Bearer {token}"}
        )
    
    response = client.get(
        "/ai-traces",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    traces = response.json()
    assert len(traces) == 3
    # Vérifier que c'est trié DESC (trace 2 d'abord, puis 1, puis 0)
    assert "content" in traces[0]["generated_content"].lower()

def test_get_traces_for_page():
    """
    TEST 5: Récupérer les traces IA d'une PAGE spécifique.
    
    LOGIQUE:
    1. Créer 2 pages
    2. Créer 2 traces pour page 1, 1 trace pour page 2
    3. GET /ai-traces/page/{page_id}
    4. Vérifier qu'on reçoit UNIQUEMENT les traces de cette page
    
    USE CASE:
    - Afficher l'historique "Voir ce qui a été généré" pour cette page
    """
    token = create_user_and_get_token()
    page1_id = create_page(token)
    page2_id = create_page(token)
    
    # Créer 2 traces pour page 1
    client.post(
        "/ai-traces",
        json={
            "page_id": page1_id,
            "analysis_type": "summarize",
            "generated_content": "Summary 1",
            "success": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        "/ai-traces",
        json={
            "page_id": page1_id,
            "analysis_type": "checklist",
            "generated_content": "Checklist 1",
            "success": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Créer 1 trace pour page 2
    client.post(
        "/ai-traces",
        json={
            "page_id": page2_id,
            "analysis_type": "summarize",
            "generated_content": "Summary 2",
            "success": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    response = client.get(
        f"/ai-traces/page/{page1_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    traces = response.json()
    assert len(traces) == 2
    assert all(trace["page_id"] == page1_id for trace in traces)

def test_cross_user_isolation():
    """
    TEST 6: SÉCURITÉ - Un user ne peut pas accéder aux traces d'un autre user.
    
    LOGIQUE:
    1. USER 1 crée une trace
    2. USER 2 essaie de GET /ai-traces/{trace_id} de USER 1
    3. Doit retourner 404
    4. USER 2 essaie de GET /ai-traces (should be empty for USER 2)
    
    SÉCURITÉ:
    - Chaque user ne voit que SES propres traces
    """
    # USER 1
    token1 = create_user_and_get_token()
    page1_id = create_page(token1)
    
    trace_response = client.post(
        "/ai-traces",
        json={
            "page_id": page1_id,
            "analysis_type": "summarize",
            "generated_content": "Summary 1",
            "success": True
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    trace_id = trace_response.json()["id"]
    
    # USER 2
    token2 = create_user_and_get_token()
    
    # USER 2 essaie d'accéder à la trace de USER 1
    response = client.get(
        f"/ai-traces/{trace_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 404
    
    # USER 2 liste ses traces (doit être vide)
    list_response = client.get(
        "/ai-traces",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert len(list_response.json()) == 0
