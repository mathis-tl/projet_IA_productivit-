import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.models.page import Page
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

# Fonction helper pour créer un user ET son token (en BD, pas via API)
def create_user_and_get_token():
    """
    Crée un user DIRECTEMENT en BD et génère un token JWT.
    
    POURQUOI PAS /auth/signup?
    - /signup crée l'user dans une session
    - Puis on ferme la session
    - Quand /pages cherche l'user, c'est une nouvelle session qui ne le voit pas
    
    SOLUTION:
    - Créer directement en BD avec la même SessionLocal
    - Générer le token avec create_access_token()
    - Même user est visible à /pages car même session
    """
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
def create_page(token, title="Test Page"):
    """
    Crée une page via l'API /pages.
    Retourne l'ID de la page créée.
    """
    response = client.post(
        "/pages",
        json={"title": title, "description": "Description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    # Debug: affiche la réponse en cas d'erreur
    if response.status_code != 201:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.json()}")
    return response.json()["id"]

# ============ TESTS ============

def test_create_link_success():
    """
    TEST 1: Créer un lien avec succès.
    
    LOGIQUE:
    1. Créer un user
    2. Créer 2 pages (source et target)
    3. POST /links avec source_page_id et target_page_id
    4. Vérifier que status = 201 Created
    5. Vérifier que le lien contient les bonnes données
    """
    token = create_user_and_get_token()
    page1_id = create_page(token, "Page 1")
    page2_id = create_page(token, "Page 2")
    
    response = client.post(
        "/links",
        json={
            "source_page_id": page1_id,
            "target_page_id": page2_id,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    link = response.json()
    assert link["source_page_id"] == page1_id
    assert link["target_page_id"] == page2_id
    assert link["type"] == "related"
    assert "id" in link

def test_create_link_invalid_source_page():
    """
    TEST 2: Créer un lien avec une page SOURCE invalide.
    
    LOGIQUE:
    1. Créer un user
    2. Créer 1 page (target)
    3. POST /links avec source_page_id = 9999 (inexistent)
    4. Vérifier que status = 404 "Source page not found"
    """
    token = create_user_and_get_token()
    page_id = create_page(token)
    
    response = client.post(
        "/links",
        json={
            "source_page_id": 9999,  # ← N'existe pas
            "target_page_id": page_id,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert "Source page not found" in response.json()["detail"]

def test_create_link_invalid_target_page():
    """
    TEST 3: Créer un lien avec une page TARGET invalide.
    
    LOGIQUE:
    1. Créer un user
    2. Créer 1 page (source)
    3. POST /links avec target_page_id = 9999 (inexistent)
    4. Vérifier que status = 404 "Target page not found"
    """
    token = create_user_and_get_token()
    page_id = create_page(token)
    
    response = client.post(
        "/links",
        json={
            "source_page_id": page_id,
            "target_page_id": 9999,  # ← N'existe pas
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert "Target page not found" in response.json()["detail"]

def test_create_duplicate_link():
    """
    TEST 4: Créer un lien EN DOUBLON (même source, target, type).
    
    LOGIQUE:
    1. Créer un user
    2. Créer 2 pages
    3. POST /links (premier lien)
    4. POST /links (même lien) → doit échouer
    5. Vérifier que status = 400 "Link already exists"
    """
    token = create_user_and_get_token()
    page1_id = create_page(token, "Page 1")
    page2_id = create_page(token, "Page 2")
    
    # Créer le premier lien
    client.post(
        "/links",
        json={
            "source_page_id": page1_id,
            "target_page_id": page2_id,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Créer le même lien (doublon)
    response = client.post(
        "/links",
        json={
            "source_page_id": page1_id,
            "target_page_id": page2_id,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "Link already exists" in response.json()["detail"]

def test_get_page_links_outlinks():
    """
    TEST 5: Récupérer les liens SORTANTS d'une page (outlinks).
    
    LOGIQUE:
    1. Créer 3 pages: A, B, C
    2. Créer liens: A → B, A → C
    3. GET /links/pages/A
    4. Vérifier qu'on reçoit 2 liens (A → B et A → C)
    5. Vérifier que target_page_id = B et C
    """
    token = create_user_and_get_token()
    page_a = create_page(token, "Page A")
    page_b = create_page(token, "Page B")
    page_c = create_page(token, "Page C")
    
    # Créer liens: A → B, A → C
    client.post(
        "/links",
        json={"source_page_id": page_a, "target_page_id": page_b, "type": "related"},
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        "/links",
        json={"source_page_id": page_a, "target_page_id": page_c, "type": "implements"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    response = client.get(
        f"/links/pages/{page_a}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    links = response.json()
    assert len(links) == 2
    assert all(link["source_page_id"] == page_a for link in links)

def test_get_page_backlinks():
    """
    TEST 6: Récupérer les BACKLINKS d'une page (liens entrants).
    
    LOGIQUE:
    1. Créer 3 pages: A, B, C
    2. Créer liens: A → C, B → C (deux pages pointent VERS C)
    3. GET /links/pages/C/backlinks
    4. Vérifier qu'on reçoit 2 liens
    5. Vérifier que source_page_id = A et B, target_page_id = C
    
    DIFFÉRENCE AVEC test_get_page_links_outlinks():
    - outlinks: ← liens SORTANTS (la page crée des liens)
    - backlinks: ← liens ENTRANTS (d'autres pages pointent vers celle-ci)
    """
    token = create_user_and_get_token()
    page_a = create_page(token, "Page A")
    page_b = create_page(token, "Page B")
    page_c = create_page(token, "Page C")
    
    # Créer liens: A → C, B → C
    client.post(
        "/links",
        json={"source_page_id": page_a, "target_page_id": page_c, "type": "related"},
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        "/links",
        json={"source_page_id": page_b, "target_page_id": page_c, "type": "implements"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    response = client.get(
        f"/links/pages/{page_c}/backlinks",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    links = response.json()
    assert len(links) == 2
    assert all(link["target_page_id"] == page_c for link in links)

def test_delete_link_success():
    """
    TEST 7: Supprimer un lien avec succès.
    
    LOGIQUE:
    1. Créer un user
    2. Créer 2 pages et un lien
    3. DELETE /links/{link_id}
    4. Vérifier que status = 204 No Content (pas de body)
    5. GET /links/{link_id} → doit retourner 404 (le lien est supprimé)
    """
    token = create_user_and_get_token()
    page1_id = create_page(token)
    page2_id = create_page(token)
    
    # Créer un lien
    create_response = client.post(
        "/links",
        json={
            "source_page_id": page1_id,
            "target_page_id": page2_id,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    link_id = create_response.json()["id"]
    
    # Supprimer le lien
    delete_response = client.delete(
        f"/links/{link_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert delete_response.status_code == 204
    
    # Vérifier que le lien n'existe plus
    get_response = client.get(
        f"/links/{link_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404

def test_cross_user_isolation():
    """
    TEST 8: SÉCURITÉ - Un user ne peut pas accéder aux liens d'un autre user.
    
    LOGIQUE:
    1. Créer USER 1 avec 2 pages et 1 lien
    2. Créer USER 2
    3. USER 2 essaie de GET /links/{link_id} de USER 1
    4. Doit retourner 404 (le lien n'existe pas pour USER 2)
    5. USER 2 essaie de DELETE /links/{link_id} de USER 1
    6. Doit retourner 404
    
    SÉCURITÉ:
    - Chaque user ne voit que SES propres liens
    - Les FKs (source/target pages) AUSSI vérifiées avec user_id
    """
    # USER 1
    token1 = create_user_and_get_token()
    page1_u1 = create_page(token1, "Page 1 User 1")
    page2_u1 = create_page(token1, "Page 2 User 1")
    
    link_response = client.post(
        "/links",
        json={
            "source_page_id": page1_u1,
            "target_page_id": page2_u1,
            "type": "related"
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    link_id = link_response.json()["id"]
    
    # USER 2
    token2 = create_user_and_get_token()
    
    # USER 2 essaie d'accéder au lien de USER 1
    get_response = client.get(
        f"/links/{link_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert get_response.status_code == 404
    
    # USER 2 essaie de supprimer le lien de USER 1
    delete_response = client.delete(
        f"/links/{link_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert delete_response.status_code == 404
