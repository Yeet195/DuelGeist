from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from fastapi import Depends, HTTPException, status
from app.api.auth import get_current_user

from app.models.user import User
from app.db.database import get_db
from app.db import crud
from pydantic import BaseModel

router = APIRouter()


class DeckCardBase(BaseModel):
    card_id: int
    quantity: int = 1
    is_main_deck: bool = True
    is_extra_deck: bool = False
    is_side_deck: bool = False


class DeckBase(BaseModel):
    name: str
    description: str = None
    is_public: bool = False


class DeckCreate(DeckBase):
    cards: List[DeckCardBase] = []


class DeckCardResponse(DeckCardBase):
    id: int
    deck_id: int

    class Config:
        orm_mode = True


class DeckResponse(DeckBase):
    id: int
    owner_id: int
    cards: List[DeckCardResponse] = []

    class Config:
        orm_mode = True


@router.post("/", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
def create_deck(
    deck: DeckCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new deck for the authenticated user"""
    try:
        print(f"Creating deck: {deck}")
        print(f"User ID: {current_user.id}")
        return crud.create_deck(db=db, deck=deck, user_id=current_user.id)
    except Exception as e:
        print(f"Error creating deck: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deck: {str(e)}"
        )


@router.get("/", response_model=List[DeckResponse])
def read_decks(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all public decks or user's decks if user_id is provided"""
    return crud.get_decks(db, skip=skip, limit=limit, user_id=current_user.id)


@router.get("/{deck_id}", response_model=DeckResponse)
def read_deck(
    deck_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_deck = crud.get_deck(db, deck_id=deck_id)
    if db_deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Check if user has permission to access this deck
    if not db_deck.is_public and db_deck.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this deck"
        )
    
    return db_deck


@router.put("/{deck_id}", response_model=DeckResponse)
def update_deck(
    deck_id: int, 
    deck: DeckCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_deck = crud.get_deck(db, deck_id=deck_id)
    if db_deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Check if user is the owner
    if db_deck.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this deck"
        )
    
    return crud.update_deck(db=db, deck_id=deck_id, deck=deck)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_deck = crud.get_deck(db, deck_id=deck_id)
    if db_deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Check if user is the owner
    if db_deck.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this deck"
        )
    
    crud.delete_deck(db=db, deck_id=deck_id)
    return {"detail": "Deck deleted"}