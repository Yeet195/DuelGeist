from sqlalchemy import Column, Integer, String, Text, Enum, Boolean
from sqlalchemy.orm import relationship

from app.db.database import Base
import enum


class CardType(enum.Enum):
    MONSTER = "monster"
    SPELL = "spell"
    TRAP = "trap"


class MonsterType(enum.Enum):
    NORMAL = "normal"
    EFFECT = "effect"
    FUSION = "fusion"
    RITUAL = "ritual"
    SYNCHRO = "synchro"
    XYZ = "xyz"
    LINK = "link"


class CardAttribute(enum.Enum):
    DARK = "dark"
    LIGHT = "light"
    EARTH = "earth"
    WATER = "water"
    FIRE = "fire"
    WIND = "wind"
    DIVINE = "divine"


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    card_type = Column(Enum(CardType))
    
    # Monster specific fields
    monster_type = Column(Enum(MonsterType), nullable=True)
    attribute = Column(Enum(CardAttribute), nullable=True)
    level = Column(Integer, nullable=True)
    attack = Column(Integer, nullable=True)
    defense = Column(Integer, nullable=True)
    
    # Spell/Trap specific
    is_continuous = Column(Boolean, default=False, nullable=True)
    is_counter = Column(Boolean, default=False, nullable=True)
    is_equip = Column(Boolean, default=False, nullable=True)
    is_field = Column(Boolean, default=False, nullable=True)
    is_quick_play = Column(Boolean, default=False, nullable=True)
    
    # Card image path (relative to static/images/cards)
    image_path = Column(String, nullable=True)
    
    # Relationships
    deck_cards = relationship("DeckCard", back_populates="card")
    
    def __repr__(self):
        return f"<Card {self.name}>"