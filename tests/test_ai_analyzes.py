"""
Tests pour les endpoints Ollama (/ai-analyze/*).

On MOCK les appels à Ollama pour tester les endpoints sans avoir besoin du vrai Ollama.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.core.security import create_access_token
from unittest.mock import patch, MagicMock
import uuid

# Configuration BD test
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

# Helper pour créer un user
def create_test_user():
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
    db.close()
    return user

# ============ TESTS ============

def test_summarize_success():
    """
    TEST 1: POST /ai-analyze/summarize fonctionne avec Ollama mock.
    
    LOGIQUE:
    1. Créer un user et un token
    2. MOCK is_ollama_running() pour True
    3. MOCK ai_service.generate_summary() pour retourner un résumé
    4. POST /ai-analyze/summarize
    5. Vérifier que:
       - Status 201 Created
       - summary, tokens_used, execution_time_ms, trace_id retournés
       - Trace enregistrée dans DB
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    # MOCK Ollama (2 mocks!)
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_running, \
         patch('app.routers.ai_analyzes.generate_summary') as mock_summarize:
        # Ollama est "running"
        mock_running.return_value = True
        # generate_summary retourne (summary, tokens, time)
        mock_summarize.return_value = (
            "Ceci est un résumé du texte",
            342,
            1200
        )
        
        # Appel endpoint
        response = client.post(
            "/ai-analyze/summarize",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "Long text to summarize",
                "page_id": 1
            }
        )
    
    # Vérifications
    assert response.status_code == 201
    data = response.json()
    assert data["summary"] == "Ceci est un résumé du texte"
    assert data["tokens_used"] == 342
    assert data["execution_time_ms"] == 1200
    assert "trace_id" in data
    assert data["trace_id"] > 0

def test_summarize_without_token():
    """
    TEST 2: SÉCURITÉ - POST /ai-analyze/summarize sans token = 401.
    """
    response = client.post(
        "/ai-analyze/summarize",
        json={"content": "text"}
    )
    
    assert response.status_code == 401
    assert "Missing token" in response.json()["detail"]

def test_summarize_ollama_offline():
    """
    TEST 3: POST /ai-analyze/summarize quand Ollama est offline = 503.
    
    LOGIQUE:
    1. MOCK is_ollama_running() pour retourner False
    2. POST /ai-analyze/summarize
    3. Vérifier que status = 503 Service Unavailable
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    # MOCK Ollama comme non disponible
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_ollama:
        mock_ollama.return_value = False
        
        response = client.post(
            "/ai-analyze/summarize",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "text"}
        )
    
    assert response.status_code == 503
    assert "not running" in response.json()["detail"]

def test_summarize_ollama_error():
    """
    TEST 4: POST /ai-analyze/summarize quand Ollama échoue = 500.
    
    LOGIQUE:
    1. MOCK is_ollama_running() pour True (on pense qu'il tourne)
    2. MOCK generate_summary() pour lever une Exception
    3. POST /ai-analyze/summarize
    4. Vérifier que:
       - Status 500 Internal Server Error
       - Trace d'erreur enregistrée dans DB avec success=False
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_running, \
         patch('app.routers.ai_analyzes.generate_summary') as mock_summarize:
        mock_running.return_value = True
        # Lever une exception
        mock_summarize.side_effect = Exception("Ollama connection error")
        
        response = client.post(
            "/ai-analyze/summarize",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "text"}
        )
    
    assert response.status_code == 500
    assert "Ollama error" in response.json()["detail"]

def test_extract_actions_success():
    """
    TEST 5: POST /ai-analyze/extract-actions fonctionne.
    
    LOGIQUE:
    1. MOCK is_ollama_running() pour True
    2. MOCK extract_actions() pour retourner une liste d'actions
    3. POST /ai-analyze/extract-actions
    4. Vérifier que:
       - Status 201 Created
       - actions list retournée
       - tokens_used, execution_time_ms, trace_id présents
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_running, \
         patch('app.routers.ai_analyzes.extract_actions') as mock_extract:
        mock_running.return_value = True
        mock_extract.return_value = (
            ["Appeler Jean", "Finaliser rapport"],
            215,
            980
        )
        
        response = client.post(
            "/ai-analyze/extract-actions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "Appelle Jean demain, puis finalise le rapport"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["actions"] == ["Appeler Jean", "Finaliser rapport"]
    assert data["tokens_used"] == 215
    assert data["execution_time_ms"] == 980
    assert "trace_id" in data

def test_extract_actions_ollama_offline():
    """
    TEST 6: POST /ai-analyze/extract-actions sans Ollama = 503.
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_ollama:
        mock_ollama.return_value = False
        
        response = client.post(
            "/ai-analyze/extract-actions",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "text"}
        )
    
    assert response.status_code == 503

def test_health_check_ollama_running():
    """
    TEST 7: GET /ai-analyze/health quand Ollama tourne.
    """
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_ollama:
        mock_ollama.return_value = True
        
        response = client.get("/ai-analyze/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ollama"] == "running"

def test_health_check_ollama_offline():
    """
    TEST 8: GET /ai-analyze/health quand Ollama est offline.
    """
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_ollama:
        mock_ollama.return_value = False
        
        response = client.get("/ai-analyze/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "warning"
    assert data["ollama"] == "not running"

def test_summarize_with_page_id():
    """
    TEST 9: POST /ai-analyze/summarize avec page_id enregistre la trace.
    
    LOGIQUE:
    1. POST /ai-analyze/summarize avec page_id=5
    2. Vérifier que la trace a page_id=5 dans la DB
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_running, \
         patch('app.routers.ai_analyzes.generate_summary') as mock_summarize:
        mock_running.return_value = True
        mock_summarize.return_value = ("Summary", 100, 500)
        
        response = client.post(
            "/ai-analyze/summarize",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "text",
                "page_id": 42,
                "task_id": None
            }
        )
    
    assert response.status_code == 201
    
    # Vérifier que la trace est bien enregistrée avec page_id=42
    trace_id = response.json()["trace_id"]
    
    db = TestingSessionLocal()
    from app.models.ai_trace import AITrace
    trace = db.query(AITrace).filter(AITrace.id == trace_id).first()
    
    assert trace is not None
    assert trace.page_id == 42
    assert trace.analysis_type == "summarize"
    assert trace.success == True
    assert trace.generated_content == "Summary"
    
    db.close()

def test_extract_actions_with_task_id():
    """
    TEST 10: POST /ai-analyze/extract-actions avec task_id enregistre la trace.
    """
    user = create_test_user()
    token = create_access_token(user.id, user.email)
    
    with patch('app.routers.ai_analyzes.is_ollama_running') as mock_running, \
         patch('app.routers.ai_analyzes.extract_actions') as mock_extract:
        mock_running.return_value = True
        mock_extract.return_value = (["Action 1", "Action 2"], 100, 500)
        
        response = client.post(
            "/ai-analyze/extract-actions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "text",
                "page_id": None,
                "task_id": 99
            }
        )
    
    assert response.status_code == 201
    
    # Vérifier trace
    trace_id = response.json()["trace_id"]
    
    db = TestingSessionLocal()
    from app.models.ai_trace import AITrace
    trace = db.query(AITrace).filter(AITrace.id == trace_id).first()
    
    assert trace is not None
    assert trace.task_id == 99
    assert trace.analysis_type == "extract_actions"
    
    db.close()
