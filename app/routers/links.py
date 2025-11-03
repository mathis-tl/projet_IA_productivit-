from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.page import Page
from app.models.link import Link
from app.schemas.link import LinkCreate, LinkResponse
from app.core.security import decode_token
from fastapi import Header
from typing import List, Optional

router = APIRouter(prefix="/links", tags=["links"])

def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> User:
    """
    Récupère l'utilisateur depuis le JWT token.
    
    Cette fonction est réutilisable dans tous les endpoints pour protéger les routes.
    Elle extrait le token du header Authorization, le valide, et retourne l'user.
    """
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

@router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_link(link_data: LinkCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Créer un lien entre deux pages.
    
    LOGIQUE MÉTIER:
    1. Valider que source_page_id EXISTE et APPARTIENT à l'user
    2. Valider que target_page_id EXISTE et APPARTIENT à l'user
    3. Vérifier qu'un lien identique n'existe pas déjà (prevent duplicates)
    4. Créer et retourner le lien
    
    EXEMPLE:
    POST /links
    {"source_page_id": 1, "target_page_id": 2, "type": "related"}
    → Crée un lien Page1 → Page2 (type: related)
    
    SÉCURITÉ:
    - L'user ne peut lier que SES PROPRES pages
    - On vérifie user_id sur source ET target
    """
    
    # ÉTAPE 1: Vérifier que la page SOURCE existe ET appartient à l'user
    source_page = db.query(Page).filter(
        Page.id == link_data.source_page_id,
        Page.user_id == current_user.id
    ).first()
    
    if not source_page:
        # La page source n'existe pas OU n'appartient pas à l'user
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source page not found"
        )
    
    # ÉTAPE 2: Vérifier que la page TARGET existe ET appartient à l'user
    target_page = db.query(Page).filter(
        Page.id == link_data.target_page_id,
        Page.user_id == current_user.id
    ).first()
    
    if not target_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target page not found"
        )
    
    # ÉTAPE 3: Vérifier qu'un lien identique n'existe pas
    # (source_page_id + target_page_id + type uniques)
    existing_link = db.query(Link).filter(
        Link.source_page_id == link_data.source_page_id,
        Link.target_page_id == link_data.target_page_id,
        Link.type == link_data.type,
        Link.user_id == current_user.id
    ).first()
    
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link already exists"
        )
    
    # ÉTAPE 4: Créer le lien
    new_link = Link(
        user_id=current_user.id,
        source_page_id=link_data.source_page_id,
        target_page_id=link_data.target_page_id,
        type=link_data.type
    )
    
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    
    return new_link

@router.get("", response_model=List[LinkResponse])
def list_links(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupérer TOUS les liens de l'utilisateur.
    
    LOGIQUE:
    - Requêter tous les liens WHERE user_id = current_user.id
    - Retourner la liste
    
    EXEMPLE:
    GET /links
    → [
      {"id": 1, "user_id": 1, "source_page_id": 1, "target_page_id": 2, "type": "related", ...},
      {"id": 2, "user_id": 1, "source_page_id": 1, "target_page_id": 3, "type": "implements", ...}
    ]
    """
    
    links = db.query(Link).filter(Link.user_id == current_user.id).all()
    return links

@router.get("/pages/{page_id}", response_model=List[LinkResponse])
def get_page_links(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupérer les LIENS SORTANTS d'une page.
    
    LOGIQUE:
    1. Vérifier que la page APPARTIENT à l'user
    2. Requêter tous les liens WHERE source_page_id = page_id
    3. Retourner la liste
    
    CONCEPT: OUTLINKS vs BACKLINKS
    - OUTLINKS: liens que CETTE PAGE fait vers d'autres
      → WHERE source_page_id = page_id
    - BACKLINKS: liens que d'AUTRES pages font VERS celle-ci
      → WHERE target_page_id = page_id
    
    EXEMPLE:
    GET /links/pages/1
    → Tous les liens QUE la page 1 crée VERS d'autres pages
    → Page1 → Page2, Page1 → Page5, etc.
    """
    
    # ÉTAPE 1: Vérifier que la page appartient à l'user
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # ÉTAPE 2: Requêter les liens SORTANTS (source_page_id = page_id)
    links = db.query(Link).filter(
        Link.source_page_id == page_id,
        Link.user_id == current_user.id
    ).all()
    
    return links

@router.get("/pages/{page_id}/backlinks", response_model=List[LinkResponse])
def get_page_backlinks(page_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupérer les BACKLINKS d'une page (pages qui LIENT VERS celle-ci).
    
    LOGIQUE:
    1. Vérifier que la page APPARTIENT à l'user
    2. Requêter tous les liens WHERE target_page_id = page_id
    3. Retourner la liste
    
    DIFFÉRENCE AVEC get_page_links():
    - get_page_links(): liens SORTANTS (cette page → d'autres)
      WHERE source_page_id = page_id
    - get_page_backlinks(): liens ENTRANTS (d'autres pages → cette page)
      WHERE target_page_id = page_id
    
    EXEMPLE:
    GET /links/pages/2/backlinks
    → Tous les liens QUI POINTENT VERS la page 2
    → Page1 → Page2, Page5 → Page2, etc.
    
    USE CASE: Voir "qui cite cette page" (comme Wikipedia backlinks)
    """
    
    # ÉTAPE 1: Vérifier que la page appartient à l'user
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.user_id == current_user.id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # ÉTAPE 2: Requêter les liens ENTRANTS (target_page_id = page_id)
    backlinks = db.query(Link).filter(
        Link.target_page_id == page_id,
        Link.user_id == current_user.id
    ).all()
    
    return backlinks

@router.get("/{link_id}", response_model=LinkResponse)
def get_link(link_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupérer un lien spécifique par ID.
    
    LOGIQUE:
    1. Requêter le lien par ID
    2. Vérifier qu'il APPARTIENT à l'user (link.user_id == current_user.id)
    3. Retourner le lien ou 404
    
    SÉCURITÉ:
    - On vérifie DEUX fois: ID ET user_id
    - Impossible d'accéder aux liens d'un autre user
    
    EXEMPLE:
    GET /links/5
    → {"id": 5, "user_id": 1, "source_page_id": 1, "target_page_id": 3, ...}
    """
    
    link = db.query(Link).filter(
        Link.id == link_id,
        Link.user_id == current_user.id
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    return link

@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Supprimer un lien.
    
    LOGIQUE:
    1. Requêter le lien
    2. Vérifier qu'il appartient à l'user
    3. Supprimer (hard delete, pas de is_archived sur Link)
    4. Retourner 204 NO CONTENT (pas de body)
    
    NOTES:
    - Status code 204 = SUCCESS, pas de body à retourner
    - On fait un HARD DELETE car les liens ne sont pas "importants" pour audit
    - Contrairement à pages/blocks/tasks (soft delete avec is_archived)
    
    EXEMPLE:
    DELETE /links/5
    → Status 204 (succès, pas de body)
    """
    
    link = db.query(Link).filter(
        Link.id == link_id,
        Link.user_id == current_user.id
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    db.delete(link)
    db.commit()
