import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.models.page import Page
from app.models.block import Block
from app.models.link import Link
from app.models.task import Task
from app.core.security import create_access_token
from app.services.page_service import get_page_with_blocks, get_page_backlinks, get_related_pages
from app.services.search_service import full_text_search
from app.services.task_service import get_today_tasks, get_overdue_tasks, get_this_week_tasks
from datetime import datetime, timedelta
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

# ============ TESTS page_service.py ============

def test_page_service_get_page_with_blocks():
    """TEST 1: get_page_with_blocks() retourne page + blocks ordonnés"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer une page
    page = Page(user_id=user.id, title="Test Page", description="Desc")
    db.add(page)
    db.commit()
    db.refresh(page)
    
    # Créer des blocks dans le désordre
    block2 = Block(page_id=page.id, user_id=user.id, type="text", content="Block 2", order=2)
    block1 = Block(page_id=page.id, user_id=user.id, type="text", content="Block 1", order=1)
    block3 = Block(page_id=page.id, user_id=user.id, type="text", content="Block 3", order=3)
    
    db.add_all([block2, block1, block3])
    db.commit()
    
    # Utiliser le service
    retrieved_page, blocks = get_page_with_blocks(db, user.id, page.id)
    
    # Vérifications
    assert retrieved_page.id == page.id
    assert len(blocks) == 3
    assert blocks[0].order == 1  # Triés par order
    assert blocks[1].order == 2
    assert blocks[2].order == 3
    
    db.close()

def test_page_service_get_page_backlinks():
    """TEST 2: get_page_backlinks() retourne liens entrants"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer 3 pages
    page_a = Page(user_id=user.id, title="A")
    page_b = Page(user_id=user.id, title="B")
    page_c = Page(user_id=user.id, title="C")
    db.add_all([page_a, page_b, page_c])
    db.commit()
    
    # Créer liens: A → C, B → C
    link1 = Link(user_id=user.id, source_page_id=page_a.id, target_page_id=page_c.id, type="related")
    link2 = Link(user_id=user.id, source_page_id=page_b.id, target_page_id=page_c.id, type="related")
    db.add_all([link1, link2])
    db.commit()
    
    # Utiliser le service: backlinks de C
    backlinks = get_page_backlinks(db, user.id, page_c.id)
    
    assert len(backlinks) == 2
    assert all(link.target_page_id == page_c.id for link in backlinks)
    
    db.close()

def test_page_service_get_related_pages():
    """TEST 3: get_related_pages() retourne outlinks + backlinks"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer 4 pages: A, B, C, D
    page_a = Page(user_id=user.id, title="A")
    page_b = Page(user_id=user.id, title="B")
    page_c = Page(user_id=user.id, title="C")
    page_d = Page(user_id=user.id, title="D")
    db.add_all([page_a, page_b, page_c, page_d])
    db.commit()
    
    # Liens: A → B, A → C (outlinks), D → A (backlink)
    link1 = Link(user_id=user.id, source_page_id=page_a.id, target_page_id=page_b.id, type="related")
    link2 = Link(user_id=user.id, source_page_id=page_a.id, target_page_id=page_c.id, type="related")
    link3 = Link(user_id=user.id, source_page_id=page_d.id, target_page_id=page_a.id, type="related")
    db.add_all([link1, link2, link3])
    db.commit()
    
    # get_related_pages(A) doit retourner [B, C, D]
    related = get_related_pages(db, user.id, page_a.id)
    related_ids = {p.id for p in related}
    
    assert len(related) == 3
    assert page_b.id in related_ids
    assert page_c.id in related_ids
    assert page_d.id in related_ids
    
    db.close()

def test_page_service_get_page_with_blocks_security():
    """TEST 4: SÉCURITÉ - user2 ne peut pas voir les blocks de user1"""
    db = TestingSessionLocal()
    user1 = create_test_user()
    user2 = create_test_user()
    
    # User1 crée une page
    page = Page(user_id=user1.id, title="Page U1")
    db.add(page)
    db.commit()
    
    # User2 essaie d'accéder
    retrieved_page, blocks = get_page_with_blocks(db, user2.id, page.id)
    
    assert retrieved_page is None
    assert blocks == []
    
    db.close()

# ============ TESTS search_service.py ============

def test_search_pages_by_title():
    """TEST 5: full_text_search() cherche dans Page.title"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer pages
    page1 = Page(user_id=user.id, title="Python tutorial", description="Learn Python")
    page2 = Page(user_id=user.id, title="JavaScript guide", description="Learn JS")
    db.add_all([page1, page2])
    db.commit()
    
    # Recherche
    results = full_text_search(db, user.id, "python")
    
    assert len(results) >= 1
    assert any(r.result_type == "page" and "Python" in r.title for r in results)
    
    db.close()

def test_search_blocks_by_content():
    """TEST 6: full_text_search() cherche dans Block.content"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer page + block
    page = Page(user_id=user.id, title="My Page")
    db.add(page)
    db.commit()
    
    block = Block(page_id=page.id, user_id=user.id, type="text", content="This is about FastAPI framework")
    db.add(block)
    db.commit()
    
    # Recherche
    results = full_text_search(db, user.id, "FastAPI")
    
    assert len(results) >= 1
    assert any(r.result_type == "block" and "FastAPI" in r.snippet for r in results)
    
    db.close()

def test_search_no_results():
    """TEST 7: full_text_search() retourne [] si rien trouvé"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    # Créer page
    page = Page(user_id=user.id, title="Python tutorial")
    db.add(page)
    db.commit()
    
    # Recherche
    results = full_text_search(db, user.id, "nonexistent_text")
    
    assert len(results) == 0
    
    db.close()

# ============ TESTS task_service.py ============

def test_get_today_tasks():
    """TEST 8: get_today_tasks() retourne tâches d'aujourd'hui"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)
    
    # Créer tâches
    task_today = Task(user_id=user.id, title="Today", due_date=today, status="todo")
    task_tomorrow = Task(user_id=user.id, title="Tomorrow", due_date=tomorrow, status="todo")
    task_yesterday = Task(user_id=user.id, title="Yesterday", due_date=yesterday, status="todo")
    
    db.add_all([task_today, task_tomorrow, task_yesterday])
    db.commit()
    
    # Utiliser le service
    today_tasks = get_today_tasks(db, user.id)
    
    assert len(today_tasks) >= 1
    assert any(t.title == "Today" for t in today_tasks)
    assert not any(t.title == "Tomorrow" for t in today_tasks)
    
    db.close()

def test_get_overdue_tasks():
    """TEST 9: get_overdue_tasks() retourne tâches en retard"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    # Créer tâches
    task_overdue = Task(user_id=user.id, title="Overdue", due_date=yesterday, status="todo")
    task_done_overdue = Task(user_id=user.id, title="Done Overdue", due_date=yesterday, status="done")
    task_future = Task(user_id=user.id, title="Future", due_date=tomorrow, status="todo")
    
    db.add_all([task_overdue, task_done_overdue, task_future])
    db.commit()
    
    # Utiliser le service
    overdue_tasks = get_overdue_tasks(db, user.id)
    
    # Seulement "Overdue" (pas "Done" ni "Future")
    assert any(t.title == "Overdue" for t in overdue_tasks)
    assert not any(t.title == "Done Overdue" for t in overdue_tasks)  # Pas les done
    assert not any(t.title == "Future" for t in overdue_tasks)
    
    db.close()

def test_get_this_week_tasks():
    """TEST 10: get_this_week_tasks() retourne tâches de cette semaine"""
    db = TestingSessionLocal()
    user = create_test_user()
    
    today = datetime.today()
    in_3_days = today + timedelta(days=3)
    next_week = today + timedelta(days=8)
    
    # Créer tâches
    task_week = Task(user_id=user.id, title="This week", due_date=in_3_days, status="todo")
    task_next_week = Task(user_id=user.id, title="Next week", due_date=next_week, status="todo")
    
    db.add_all([task_week, task_next_week])
    db.commit()
    
    # Utiliser le service
    week_tasks = get_this_week_tasks(db, user.id)
    
    assert any(t.title == "This week" for t in week_tasks)
    
    db.close()
