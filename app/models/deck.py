from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="decks")
    cards = relationship("DeckCard", back_populates="deck")
    
    def __repr__(self):
        return f"<Deck {self.name}>"


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"))
    card_id = Column(Integer, ForeignKey("cards.id"))
    quantity = Column(Integer, default=1)
    is_main_deck = Column(Boolean, default=True)
    is_extra_deck = Column(Boolean, default=False)
    is_side_deck = Column(Boolean, default=False)

    # Relationships
    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card", back_populates="deck_cards")
    
    def __repr__(self):
        return f"<DeckCard {self.deck_id}:{self.card_id}>"