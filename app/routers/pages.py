from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.page import Page
from app.schemas.page import PageCreate, PageUpdate, PageResponse
from app.core.security import decode_token
from app.services.search_service import full_text_search
from fastapi import Header
from typing import List, Optional

router = APIRouter(prefix="/pages", tags=["pages"])

def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
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

# Crée une page
@router.post("", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
def create_page(page_data: PageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_page = Page(
        user_id=current_user.id,
        title=page_data.title,
        description=page_data.description,
        icon=page_data.icon
    )
    db.add(new_page)
    db.commit()
    db.refresh(new_page)
    return new_page

@router.get("", response_model=List[PageResponse])
def list_pages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Récupérer toutes les pages de l'utilisateur (non archivées)
    pages = db.query(Page).filter(
        Page.user_id == current_user.id,
        Page.is_archived == False
    ).all()
    return pages

@router.get("/{page_id}", response_model=PageResponse)
def get_page(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Récup une page spécifique par ID
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page

@router.put("/{page_id}", response_model=PageResponse)
    # Maj les champs de la page
def update_page(page_id: int, page_data: PageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    
    if page_data.title is not None:
        page.title = page_data.title
    if page_data.description is not None:
        page.description = page_data.description
    if page_data.icon is not None:
        page.icon = page_data.icon
    
    db.commit()
    db.refresh(page)
    return page

@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    
    page.is_archived = True
    db.commit()

@router.get("/search/query", tags=["search"])
#recherche dans les pages/block
def search_pages(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    results = full_text_search(db, current_user.id, q)
    
    # Convertir les résultats en dict pour JSON
    return [
        {
            "result_type": r.result_type,
            "id": r.id,
            "title": r.title,
            "snippet": r.snippet
        }
        for r in results
    ]