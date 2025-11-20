"""
Router pour les récompenses de gamification (streaks, coffres, loots, inventaire)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.task import Task
from app.services.gamification_service import (
    get_chest_type,
    choose_loot,
    add_to_inventory,
    get_loot_name
)

router = APIRouter(prefix="/rewards", tags=["rewards"])


# ============ SCHEMAS ============

class OpenChestRequest(BaseModel):
    task_id: int


class OpenChestResponse(BaseModel):
    chest_type: str
    rarity: str
    item_id: str
    item_name: str
    current_streak: int
    days_without_tasks: int
    inventory_count: int


class InventoryResponse(BaseModel):
    inventory: List[str]
    count: int


class StreakResponse(BaseModel):
    current_streak: int
    days_without_tasks: int
    last_task_completed: Optional[str]
    next_chest_type: str


# ============ DEPENDENCIES ============

def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> User:
    """Récupère l'utilisateur courant via JWT"""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


# ============ ENDPOINTS ============

@router.post("/open-chest", response_model=OpenChestResponse, status_code=status.HTTP_201_CREATED)
def open_chest(
    request: OpenChestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ouvre un coffre après complétude d'une tâche.
    
    Détermine le type de coffre selon la streak.
    Génère un loot aléatoire selon les probabilités.
    Ajoute l'item à l'inventaire.
    """
    
    # Vérifier que la tâche existe et appartient à l'utilisateur
    task = db.query(Task).filter(
        Task.id == request.task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Déterminer le type de coffre selon la streak
    chest_type = get_chest_type(current_user.current_streak)
    
    # Choisir un loot aléatoire
    rarity, item_id = choose_loot(chest_type)
    
    # Ajouter à l'inventaire
    success, final_item_id = add_to_inventory(current_user, item_id, rarity)
    
    # Mettre à jour l'inventaire en BD
    db.commit()
    
    return OpenChestResponse(
        chest_type=chest_type,
        rarity=rarity,
        item_id=final_item_id,
        item_name=get_loot_name(final_item_id),
        current_streak=current_user.current_streak,
        days_without_tasks=current_user.days_without_tasks,
        inventory_count=len(current_user.inventory) if current_user.inventory else 0
    )


@router.get("/inventory", response_model=InventoryResponse)
def get_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne tous les objets débloqués de l'utilisateur.
    """
    inventory = current_user.inventory if current_user.inventory else []
    
    return InventoryResponse(
        inventory=inventory,
        count=len(inventory)
    )


@router.get("/streak", response_model=StreakResponse)
def get_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne l'état actuel du streak (lazy update).
    """
    next_chest = get_chest_type(current_user.current_streak)
    
    return StreakResponse(
        current_streak=current_user.current_streak,
        days_without_tasks=current_user.days_without_tasks,
        last_task_completed=current_user.last_task_completed.isoformat() if current_user.last_task_completed else None,
        next_chest_type=next_chest
    )
