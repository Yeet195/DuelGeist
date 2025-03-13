from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db import crud
from app.models.card import CardType, MonsterType, CardAttribute
from pydantic import BaseModel

router = APIRouter()


class CardBase(BaseModel):
    name: str
    description: str
    card_type: str  # Use string for API, convert to enum in implementation


class MonsterCardCreate(CardBase):
    monster_type: str
    attribute: str
    level: int
    attack: int
    defense: int


class SpellTrapCardCreate(CardBase):
    is_continuous: bool = False
    is_counter: bool = False
    is_equip: bool = False
    is_field: bool = False
    is_quick_play: bool = False


class CardResponse(CardBase):
    id: int
    
    # Monster fields (may be null for spell/trap)
    monster_type: Optional[str] = None
    attribute: Optional[str] = None
    level: Optional[int] = None
    attack: Optional[int] = None
    defense: Optional[int] = None
    
    # Spell/Trap fields (may be null for monsters)
    is_continuous: Optional[bool] = None
    is_counter: Optional[bool] = None
    is_equip: Optional[bool] = None
    is_field: Optional[bool] = None
    is_quick_play: Optional[bool] = None
    
    # Image path
    image_path: Optional[str] = None

    class Config:
        orm_mode = True


@router.get("/", response_model=List[CardResponse])
def read_cards(
    skip: int = 0, 
    limit: int = 100,
    name: Optional[str] = None,
    card_type: Optional[str] = None,
    attribute: Optional[str] = None,
    level: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return crud.get_cards(db, 
                          skip=skip, 
                          limit=limit, 
                          name=name, 
                          card_type=card_type,
                          attribute=attribute,
                          level=level)


@router.get("/{card_id}", response_model=CardResponse)
def read_card(card_id: int, db: Session = Depends(get_db)):
    db_card = crud.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return db_card


@router.post("/monster", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_monster_card(card: MonsterCardCreate, db: Session = Depends(get_db)):
    # In a real app, check admin permissions
    return crud.create_monster_card(db=db, card=card)


@router.post("/spell", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_spell_card(card: SpellTrapCardCreate, db: Session = Depends(get_db)):
    # In a real app, check admin permissions
    card_dict = card.dict()
    card_dict["card_type"] = "spell"
    return crud.create_spell_trap_card(db=db, card=card_dict)


@router.post("/trap", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_trap_card(card: SpellTrapCardCreate, db: Session = Depends(get_db)):
    # In a real app, check admin permissions
    card_dict = card.dict()
    card_dict["card_type"] = "trap"
    return crud.create_spell_trap_card(db=db, card=card_dict)