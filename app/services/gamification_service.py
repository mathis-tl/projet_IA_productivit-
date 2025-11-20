"""
Service de gamification - Streaks, coffres, loots, inventaire
"""

import random
from datetime import datetime, date
from typing import Tuple

# ============ LOOT POOLS ============

LOOT_POOL = {
    "commun": ["fish_blue", "small_plant", "bubble_small"],
    "atypique": ["fish_yellow", "coral_blue", "plant_medium"],
    "rare": ["fish_red", "coral_large", "plant_big"],
    "épique": ["fish_shiny", "statue_small", "coral_pink"],
    "exotique": ["fish_dragon", "coral_gold", "plant_glow"]
}

LOOT_NAMES = {
    "fish_blue": "Petit Poisson Bleu",
    "small_plant": "Petite Plante",
    "bubble_small": "Petite Bulle",
    "fish_yellow": "Poisson Jaune",
    "coral_blue": "Corail Bleu",
    "plant_medium": "Plante Moyenne",
    "fish_red": "Poisson Rouge",
    "coral_large": "Grand Corail",
    "plant_big": "Grande Plante",
    "fish_shiny": "Poisson Scintillant",
    "statue_small": "Petite Statue",
    "coral_pink": "Corail Rose",
    "fish_dragon": "Poisson Dragon",
    "coral_gold": "Corail Doré",
    "plant_glow": "Plante Lumineuse"
}

# ============ PROBABILITÉS DES COFFRES ============

CHEST_PROBABILITIES = {
    "basic": {"commun": 0.75, "atypique": 0.15, "rare": 0.07, "épique": 0.02, "exotique": 0.01},
    "rare": {"commun": 0.50, "atypique": 0.25, "rare": 0.15, "épique": 0.07, "exotique": 0.03},
    "epic": {"commun": 0.30, "atypique": 0.25, "rare": 0.20, "épique": 0.15, "exotique": 0.10},
    "exotic": {"commun": 0.05, "atypique": 0.10, "rare": 0.20, "épique": 0.30, "exotique": 0.35}
}


# ============ FONCTIONS ============

def get_today() -> date:
    """Retourne la date d'aujourd'hui"""
    return date.today()


def update_streak(user, today: date = None) -> dict:
    """
    Mets à jour la streak selon les règles officielles.
    
    Règles :
    1. Si au moins 1 tâche prévue aujourd'hui :
       - Si ≥ 1 complétée → streak += 1
       - Si aucune complétée → streak = 0
    2. Si aucune tâche prévue aujourd'hui :
       - streak inchangée
       - days_without_tasks += 1
    3. Si days_without_tasks >= 3 → streak = 0
    4. Dès qu'une tâche est complétée :
       - days_without_tasks = 0
    
    Retourne : {current_streak, days_without_tasks}
    """
    if today is None:
        today = get_today()
    
    # On retourne simplement l'état actuel pour now
    # La logique d'update se fera lors du complete_task
    return {
        "current_streak": user.current_streak,
        "days_without_tasks": user.days_without_tasks
    }


def get_chest_type(streak: int) -> str:
    """
    Retourne le type de coffre selon la streak.
    
    < 3 → basic
    ≥ 3 → rare
    ≥ 7 → epic
    ≥ 14 → exotic
    """
    if streak >= 14:
        return "exotic"
    elif streak >= 7:
        return "epic"
    elif streak >= 3:
        return "rare"
    else:
        return "basic"


def choose_loot(chest_type: str) -> Tuple[str, str]:
    """
    Choisit aléatoirement une rareté selon les probas du coffre.
    Puis choisit un item de cette rareté.
    
    Retourne (rareté, item_id)
    """
    if chest_type not in CHEST_PROBABILITIES:
        chest_type = "basic"
    
    probas = CHEST_PROBABILITIES[chest_type]
    rarities = list(probas.keys())
    weights = [probas[r] for r in rarities]
    
    # Choisir rareté selon les probas
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    
    # Choisir item aléatoire de cette rareté
    items = LOOT_POOL.get(chosen_rarity, [])
    chosen_item = random.choice(items) if items else "fish_blue"
    
    return chosen_rarity, chosen_item


def add_to_inventory(user, item_id: str, rarity: str) -> Tuple[bool, str]:
    """
    Ajoute l'item à l'inventaire.
    Si item déjà possédé → reroll un autre item de la même rareté.
    
    Retourne (success, item_id_final)
    """
    if user.inventory is None:
        user.inventory = []
    
    # Si item déjà possédé, reroll
    if item_id in user.inventory:
        items_of_rarity = LOOT_POOL.get(rarity, [])
        available_items = [i for i in items_of_rarity if i not in user.inventory]
        
        if available_items:
            item_id = random.choice(available_items)
        else:
            # Tous les items de cette rareté sont possédés, reroll rareté inférieure
            return False, item_id  # Pour l'instant, pas de reroll rareté
    
    # Ajouter à l'inventaire
    if item_id not in user.inventory:
        user.inventory.append(item_id)
    
    return True, item_id


def get_loot_name(item_id: str) -> str:
    """Retourne le nom lisible d'un item"""
    return LOOT_NAMES.get(item_id, item_id)
