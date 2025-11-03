from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.page import Page
from app.models.block import Block
from app.schemas.block import BlockCreate, BlockUpdate, BlockResponse
from app.core.security import decode_token
from fastapi import Header
from typing import List, Optional

router = APIRouter(prefix="/blocks", tags=["blocks"])

def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
    """Récupère l'utilisateur depuis le JWT token"""
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

@router.post("/pages/{page_id}/blocks", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
def create_block(page_id: int, block_data: BlockCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Créer un block dans une page"""
    # Vérifier que la page appartient à l'user
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    
    new_block = Block(
        page_id=page_id,
        user_id=current_user.id,
        type=block_data.type,
        content=block_data.content,
        order=block_data.order,
        block_metadata=block_data.block_metadata
    )
    db.add(new_block)
    db.commit()
    db.refresh(new_block)
    return new_block

@router.get("/pages/{page_id}/blocks", response_model=List[BlockResponse])
def list_blocks(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Récupérer tous les blocks d'une page"""
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    
    blocks = db.query(Block).filter(
        Block.page_id == page_id,
        Block.is_archived == False
    ).order_by(Block.order).all()
    return blocks

@router.get("/{block_id}", response_model=BlockResponse)
def get_block(block_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Récupérer un block spécifique"""
    block = db.query(Block).filter(
        Block.id == block_id,
        Block.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    return block

@router.put("/{block_id}", response_model=BlockResponse)
def update_block(block_id: int, block_data: BlockUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Modifier un block"""
    block = db.query(Block).filter(
        Block.id == block_id,
        Block.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    
    if block_data.type is not None:
        block.type = block_data.type
    if block_data.content is not None:
        block.content = block_data.content
    if block_data.order is not None:
        block.order = block_data.order
    if block_data.block_metadata is not None:
        block.block_metadata = block_data.block_metadata
    
    db.commit()
    db.refresh(block)
    return block

@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(block_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Supprimer un block (soft delete)"""
    block = db.query(Block).filter(
        Block.id == block_id,
        Block.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    
    block.is_archived = True
    db.commit()

@router.post("/{block_id}/reorder")
def reorder_blocks(block_id: int, new_order: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Réordonner un block (changer sa position)"""
    block = db.query(Block).filter(
        Block.id == block_id,
        Block.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    
    block.order = new_order
    db.commit()
    db.refresh(block)
    return {"message": "Block reordered", "block": BlockResponse.model_validate(block)}