from app.db.database import Base
from app.models.user import User
from app.models.card import Card
from app.models.deck import Deck, DeckCard
from app.models.game import GameModel

# Import all models here so that Base.metadata includes them
# The variables here are for imports to work correctly
__all__ = ['User', 'Card', 'Deck', 'DeckCard', 'GameModel']