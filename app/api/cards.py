import os

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db import crud
from app.utils.card_database import load_cards_from_json, import_cards_to_db
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
        
@router.get("/search", response_model=List[CardResponse])
def search_cards(
    skip: int = 0, 
    limit: int = 30,
    name: Optional[str] = None,
    card_type: Optional[str] = None,
    monster_type: Optional[str] = None,
    attribute: Optional[str] = None,
    level: Optional[int] = None,
    attack: Optional[int] = None,
    defense: Optional[int] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Search for cards with multiple optional filters
    """
    return crud.search_cards(
        db=db, 
        skip=skip, 
        limit=limit,
        name=name,
        card_type=card_type,
        monster_type=monster_type,
        attribute=attribute,
        level=level,
        attack=attack,
        defense=defense,
        description=description
    )


@router.get("/count")
def get_cards_count(
    name: Optional[str] = None,
    card_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get the total count of cards matching optional filters
    """
    count = crud.get_cards_count(db=db, name=name, card_type=card_type)
    return {"count": count}


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_card_database(
    background_tasks: BackgroundTasks,
    file_path: str = "/app/data/cards.json",
    db: Session = Depends(get_db)
):
    """
    Import card data from JSON file
    This endpoint would typically be admin-only
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card database file not found: {file_path}"
        )
    
    try:
        # Run the import in the background
        background_tasks.add_task(
            import_cards_from_database_file, file_path, db
        )
        
        return {"message": "Card import started. This may take a few minutes."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error importing cards: {str(e)}"
        )


async def import_cards_from_database_file(file_path: str, db: Session):
    """Background task to import cards from a file"""
    try:
        cards_data = load_cards_from_json(file_path)
        imported_count = import_cards_to_db(db, cards_data)
        print(f"Successfully imported {imported_count} cards")
    except Exception as e:
        print(f"Error importing cards: {str(e)}")


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_card_database(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and import a card database JSON file
    This endpoint would typically be admin-only
    """
    # Save uploaded file
    file_path = f"/tmp/{file.filename}"
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            
        # Run the import in the background
        background_tasks.add_task(
            import_cards_from_database_file, file_path, db
        )
        
        return {"message": "Card database uploaded and import started. This may take a few minutes."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading card database: {str(e)}"
        )


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