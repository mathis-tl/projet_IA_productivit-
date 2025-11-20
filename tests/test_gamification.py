"""
Tests pour le système de gamification
"""

import pytest
from datetime import datetime, date
from app.models.user import User
from app.services.gamification_service import (
    get_chest_type,
    choose_loot,
    add_to_inventory,
    get_loot_name,
    LOOT_POOL,
    CHEST_PROBABILITIES
)


# ============ TESTS CHEST TYPE ============

def test_chest_type_basic():
    """Streak < 3 → basic"""
    assert get_chest_type(0) == "basic"
    assert get_chest_type(1) == "basic"
    assert get_chest_type(2) == "basic"


def test_chest_type_rare():
    """Streak >= 3 → rare"""
    assert get_chest_type(3) == "rare"
    assert get_chest_type(5) == "rare"
    assert get_chest_type(6) == "rare"


def test_chest_type_epic():
    """Streak >= 7 → epic"""
    assert get_chest_type(7) == "epic"
    assert get_chest_type(10) == "epic"
    assert get_chest_type(13) == "epic"


def test_chest_type_exotic():
    """Streak >= 14 → exotic"""
    assert get_chest_type(14) == "exotic"
    assert get_chest_type(20) == "exotic"
    assert get_chest_type(100) == "exotic"


# ============ TESTS CHOOSE LOOT ============

def test_choose_loot_returns_tuple():
    """choose_loot retourne (rareté, item_id)"""
    rarity, item_id = choose_loot("basic")
    assert isinstance(rarity, str)
    assert isinstance(item_id, str)
    assert rarity in ["commun", "atypique", "rare", "épique", "exotique"]


def test_choose_loot_from_valid_pool():
    """L'item retourné existe dans le pool de sa rareté"""
    for _ in range(10):
        rarity, item_id = choose_loot("basic")
        assert item_id in LOOT_POOL[rarity]


def test_choose_loot_probabilities_basic():
    """Les probabilités du coffre basic sont respectées (statistiquement)"""
    counts = {"commun": 0, "atypique": 0, "rare": 0, "épique": 0, "exotique": 0}
    
    for _ in range(1000):
        rarity, _ = choose_loot("basic")
        counts[rarity] += 1
    
    # Vérifier que commun est le plus fréquent (75%)
    assert counts["commun"] > counts["atypique"] > counts["rare"]


def test_choose_loot_probabilities_exotic():
    """Les probabilités du coffre exotic ont plus d'épique/exotique"""
    counts = {"commun": 0, "atypique": 0, "rare": 0, "épique": 0, "exotique": 0}
    
    for _ in range(1000):
        rarity, _ = choose_loot("exotic")
        counts[rarity] += 1
    
    # Vérifier que exotique/épique sont plus fréquents
    assert counts["exotique"] + counts["épique"] > counts["commun"]


# ============ TESTS INVENTORY ============

def test_add_to_inventory_new_item():
    """Ajouter un nouvel item à l'inventaire"""
    user = User(email="test@test.com", username="test", password_hash="hash", inventory=[])
    success, item = add_to_inventory(user, "fish_blue", "commun")
    
    assert success == True
    assert "fish_blue" in user.inventory
    assert len(user.inventory) == 1


def test_add_to_inventory_duplicate():
    """Si l'item est déjà possédé, reroll un autre"""
    user = User(email="test@test.com", username="test", password_hash="hash", inventory=["fish_blue"])
    success, item = add_to_inventory(user, "fish_blue", "commun")
    
    # Vérifier qu'un autre item est choisi
    assert item in LOOT_POOL["commun"]
    # Et que l'inventaire n'a pas de doublon
    assert user.inventory.count("fish_blue") == 1


def test_add_to_inventory_multiple_items():
    """Ajouter plusieurs items"""
    user = User(email="test@test.com", username="test", password_hash="hash", inventory=[])
    
    add_to_inventory(user, "fish_blue", "commun")
    add_to_inventory(user, "fish_yellow", "atypique")
    add_to_inventory(user, "fish_red", "rare")
    
    assert len(user.inventory) == 3
    assert "fish_blue" in user.inventory
    assert "fish_yellow" in user.inventory
    assert "fish_red" in user.inventory


def test_inventory_no_duplicates():
    """L'inventaire ne doit pas contenir de doublons"""
    user = User(email="test@test.com", username="test", password_hash="hash", inventory=[])
    
    # Ajouter le même item 5 fois
    for _ in range(5):
        add_to_inventory(user, "fish_blue", "commun")
    
    # Vérifier qu'il n'y a pas de doublon
    assert len(user.inventory) == len(set(user.inventory))
    # Vérifier que fish_blue est dans l'inventaire
    assert "fish_blue" in user.inventory


# ============ TESTS LOOT NAMES ============

def test_loot_names_exist():
    """Tous les items du pool ont un nom"""
    for rarity, items in LOOT_POOL.items():
        for item in items:
            name = get_loot_name(item)
            assert name != item  # Au moins un nom français
            assert len(name) > 0


def test_loot_name_unknown_item():
    """Un item inconnu retourne l'ID"""
    name = get_loot_name("unknown_item")
    assert name == "unknown_item"


# ============ TESTS API ENDPOINTS ============

def test_open_chest_endpoint(client, auth_token, db):
    """Tester l'endpoint /rewards/open-chest"""
    # D'abord créer une tâche
    task_response = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"title": "Test task", "priority": "high", "status": "done"}
    )
    task_id = task_response.json()["id"]
    
    # Ensuite ouvrir un coffre
    response = client.post(
        "/rewards/open-chest",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"task_id": task_id}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "chest_type" in data
    assert "rarity" in data
    assert "item_id" in data
    assert "item_name" in data
    assert data["current_streak"] >= 0
    assert data["days_without_tasks"] >= 0


def test_inventory_endpoint(client, auth_token):
    """Tester l'endpoint /rewards/inventory"""
    response = client.get(
        "/rewards/inventory",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    assert "count" in data
    assert isinstance(data["inventory"], list)
    assert data["count"] == len(data["inventory"])


def test_streak_endpoint(client, auth_token):
    """Tester l'endpoint /rewards/streak"""
    response = client.get(
        "/rewards/streak",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "current_streak" in data
    assert "days_without_tasks" in data
    assert "last_task_completed" in data
    assert "next_chest_type" in data
    assert data["next_chest_type"] in ["basic", "rare", "epic", "exotic"]


def test_open_chest_without_auth(client):
    """Ouvrir un coffre sans auth doit échouer"""
    response = client.post(
        "/rewards/open-chest",
        json={"task_id": 1}
    )
    
    assert response.status_code == 401


def test_inventory_without_auth(client):
    """Récupérer l'inventaire sans auth doit échouer"""
    response = client.get("/rewards/inventory")
    
    assert response.status_code == 401


def test_streak_without_auth(client):
    """Récupérer la streak sans auth doit échouer"""
    response = client.get("/rewards/streak")
    
    assert response.status_code == 401
