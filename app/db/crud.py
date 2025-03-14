from sqlalchemy.orm import Session, relationship
from sqlalchemy import or_, Column, Integer, String, Text, Enum, Boolean
from typing import List, Dict, Any, Optional
import hashlib

from app.models.user import User
from app.models.card import Card, CardType, MonsterType, CardAttribute
from app.models.deck import Deck, DeckCard
from app.models.game import GameModel, GameStatus
from app.db.database import Base

import enum


# User operations
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: Dict[str, Any]):
    # Hash the password - in production, use a proper password hashing library
    hashed_password = hashlib.sha256(user["password"].encode()).hexdigest()
    
    db_user = User(
        username=user["username"],
        email=user["email"],
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: Dict[str, Any]):
    db_user = get_user(db, user_id)
    
    for key, value in user.items():
        if hasattr(db_user, key) and key != "id" and key != "hashed_password":
            setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    db.delete(db_user)
    db.commit()
    return db_user


# Card operations
def get_card(db: Session, card_id: int):
    return db.query(Card).filter(Card.id == card_id).first()


def get_cards(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    name: Optional[str] = None,
    card_type: Optional[str] = None,
    attribute: Optional[str] = None,
    level: Optional[int] = None
):
    query = db.query(Card)
    
    if name:
        query = query.filter(Card.name.ilike(f"%{name}%"))
    
    if card_type:
        query = query.filter(Card.card_type == card_type)
    
    if attribute:
        query = query.filter(Card.attribute == attribute)
    
    if level:
        query = query.filter(Card.level == level)
    
    return query.offset(skip).limit(limit).all()


def create_monster_card(db: Session, card: Dict[str, Any]):
    # Convert string enums to actual enum values
    card_type = CardType.MONSTER
    monster_type = getattr(MonsterType, card["monster_type"].upper())
    attribute = getattr(CardAttribute, card["attribute"].upper())
    
    db_card = Card(
        name=card["name"],
        description=card["description"],
        card_type=card_type,
        monster_type=monster_type,
        attribute=attribute,
        level=card["level"],
        attack=card["attack"],
        defense=card["defense"]
    )
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def create_spell_trap_card(db: Session, card: Dict[str, Any]):
    # Convert string enums to actual enum values
    card_type = CardType.SPELL if card["card_type"] == "spell" else CardType.TRAP
    
    db_card = Card(
        name=card["name"],
        description=card["description"],
        card_type=card_type,
        is_continuous=card.get("is_continuous", False),
        is_counter=card.get("is_counter", False),
        is_equip=card.get("is_equip", False),
        is_field=card.get("is_field", False),
        is_quick_play=card.get("is_quick_play", False)
    )
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


# Deck operations
def get_deck(db: Session, deck_id: int):
    return db.query(Deck).filter(Deck.id == deck_id).first()


def get_decks(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None):
    query = db.query(Deck)
    
    if user_id:
        # Get user's decks
        query = query.filter(Deck.owner_id == user_id)
    else:
        # Get public decks
        query = query.filter(Deck.is_public == True)
    
    return query.offset(skip).limit(limit).all()


def create_deck(db: Session, deck: Dict[str, Any], user_id: int):
    db_deck = Deck(
        name=deck["name"],
        description=deck["description"],
        is_public=deck["is_public"],
        owner_id=user_id
    )
    
    db.add(db_deck)
    db.commit()
    db.refresh(db_deck)
    
    # Add cards to the deck
    for card in deck.get("cards", []):
        db_deck_card = DeckCard(
            deck_id=db_deck.id,
            card_id=card["card_id"],
            quantity=card["quantity"],
            is_main_deck=card.get("is_main_deck", True),
            is_extra_deck=card.get("is_extra_deck", False),
            is_side_deck=card.get("is_side_deck", False)
        )
        db.add(db_deck_card)
    
    db.commit()
    db.refresh(db_deck)
    return db_deck


def update_deck(db: Session, deck_id: int, deck: Dict[str, Any]):
    db_deck = get_deck(db, deck_id)
    
    # Update basic deck info
    db_deck.name = deck["name"]
    db_deck.description = deck["description"]
    db_deck.is_public = deck["is_public"]
    
    # Remove all existing cards from the deck
    db.query(DeckCard).filter(DeckCard.deck_id == deck_id).delete()
    
    # Add updated cards to the deck
    for card in deck.get("cards", []):
        db_deck_card = DeckCard(
            deck_id=db_deck.id,
            card_id=card["card_id"],
            quantity=card["quantity"],
            is_main_deck=card.get("is_main_deck", True),
            is_extra_deck=card.get("is_extra_deck", False),
            is_side_deck=card.get("is_side_deck", False)
        )
        db.add(db_deck_card)
    
    db.commit()
    db.refresh(db_deck)
    return db_deck


def delete_deck(db: Session, deck_id: int):
    # Delete all cards in the deck
    db.query(DeckCard).filter(DeckCard.deck_id == deck_id).delete()
    
    # Delete the deck itself
    db_deck = get_deck(db, deck_id)
    db.delete(db_deck)
    db.commit()
    return db_deck


# Game operations
def get_game(db: Session, game_id: int):
    return db.query(GameModel).filter(GameModel.id == game_id).first()


def create_game(db: Session):
    db_game = GameModel(status=GameStatus.WAITING)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


def update_game_state(db: Session, game_id: int, game_state: Dict[str, Any], action_history: List[Dict[str, Any]] = None):
    db_game = get_game(db, game_id)
    
    if not db_game:
        return None
    
    db_game.game_state = game_state
    
    if action_history:
        db_game.action_history = action_history
    
    db.commit()
    db.refresh(db_game)
    return db_game


def join_game(db: Session, game_id: int, user_id: int):
    db_game = get_game(db, game_id)
    
    if not db_game:
        return None
    
    # Assign the user to an empty player slot
    if db_game.player1_id is None:
        db_game.player1_id = user_id
    elif db_game.player2_id is None:
        db_game.player2_id = user_id
        # If both players are now assigned, change status to active
        db_game.status = GameStatus.ACTIVE
    else:
        # No empty slots
        return None
    
    db.commit()
    db.refresh(db_game)
    return db_game


def complete_game(db: Session, game_id: int, winner_id: int):
    from datetime import datetime
    
    db_game = get_game(db, game_id)
    
    if not db_game:
        return None
    
    db_game.status = GameStatus.COMPLETED
    db_game.winner_id = winner_id
    db_game.completed_at = datetime.now()
    
    db.commit()
    db.refresh(db_game)
    return db_game