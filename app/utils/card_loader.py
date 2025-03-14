import json
import os
from typing import Dict, List, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

class CardLoader:
    """
    Utility class to load and access card data from a JSON file
    rather than storing it in the database.
    """
    
    _instance = None
    _cards_by_id = {}
    _cards_list = []
    _loaded = False
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure we only load the data once"""
        if cls._instance is None:
            cls._instance = super(CardLoader, cls).__new__(cls)
        return cls._instance
    
    def load_cards(self, file_path: str = "data/cards.json") -> bool:
        """
        Load card data from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing card data
            
        Returns:
            True if successfully loaded, False otherwise
        """
        if self._loaded:
            return True
            
        try:
            if not os.path.exists(file_path):
                logger.error(f"Card database file not found: {file_path}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            cards = data.get('data', [])
            
            # Index cards by ID for quick lookup
            self._cards_by_id = {str(card['id']): card for card in cards}
            self._cards_list = cards
            self._loaded = True
            
            logger.info(f"Successfully loaded {len(cards)} cards from {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load cards from {file_path}: {str(e)}")
            return False
    
    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a card by its ID.
        
        Args:
            card_id: The card ID to look up
            
        Returns:
            The card data or None if not found
        """
        return self._cards_by_id.get(str(card_id))
    
    def _name_matches(self, card_name: str, search_term: str) -> bool:
        """
        Check if card name matches the search term.
        
        Args:
            card_name: The card name to check
            search_term: The search term to match
            
        Returns:
            True if card name matches search term
        """
        if not search_term or not card_name:
            return not search_term  # Empty search matches everything
        
        # Convert to lowercase for case-insensitive matching
        card_name_lower = card_name.lower()
        search_term_lower = search_term.lower()
        
        # Direct substring match
        if search_term_lower in card_name_lower:
            return True
        
        # Split search term into words and check if all words are in the card name
        # This allows for non-consecutive word matching
        search_words = search_term_lower.split()
        if all(word in card_name_lower for word in search_words):
            return True
            
        return False
    
    def _get_card_type_category(self, card_type: str) -> str:
        """
        Determine if a card is a monster, spell, or trap based on its type.
        
        Args:
            card_type: The card type string from the JSON
            
        Returns:
            'monster', 'spell', or 'trap'
        """
        if not card_type:
            return ''
            
        card_type_lower = card_type.lower()
        
        if 'monster' in card_type_lower:
            return 'monster'
        elif 'spell' in card_type_lower:
            return 'spell'
        elif 'trap' in card_type_lower:
            return 'trap'
        else:
            return ''
    
    def search_cards(self, 
                    name: Optional[str] = None,
                    card_type: Optional[str] = None,
                    monster_type: Optional[str] = None,
                    attribute: Optional[str] = None,
                    level: Optional[int] = None,
                    skip: int = 0,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for cards with various filters.
        
        Args:
            name: Filter by card name (partial match)
            card_type: Filter by card type (monster, spell, trap)
            monster_type: Filter by monster type (Normal, Effect, etc.)
            attribute: Filter by attribute (DARK, LIGHT, etc.)
            level: Filter by monster level/rank
            skip: Number of results to skip (for pagination)
            limit: Maximum number of results to return
            
        Returns:
            List of matching card dictionaries
        """
        results = []
        
        # Debug logging
        logger.debug(f"Search parameters: name={name}, card_type={card_type}, monster_type={monster_type}, attribute={attribute}, level={level}")
        
        for card in self._cards_list:
            # Apply name filter
            if name and not self._name_matches(card.get('name', ''), name):
                continue
            
            # Apply card type filter
            if card_type:
                card_category = self._get_card_type_category(card.get('type', ''))
                if card_category != card_type.lower():
                    continue
            
            # Apply monster-specific filters only to monster cards
            if self._get_card_type_category(card.get('type', '')) == 'monster':
                # Apply monster type filter
                if monster_type and monster_type.lower() not in card.get('race', '').lower():
                    continue
                    
                # Apply attribute filter
                if attribute and attribute.upper() != card.get('attribute', ''):
                    continue
                    
                # Apply level filter
                if level is not None and card.get('level', 0) != level:
                    continue
            elif monster_type or attribute or (level is not None):
                # Skip non-monster cards if any monster-specific filters are applied
                continue
                
            results.append(card)
        
        # Debug logging
        logger.debug(f"Found {len(results)} matching cards")
        
        # Apply pagination
        paginated_results = results[skip:skip + limit]
        return paginated_results
    
    def count_cards(self,
                   name: Optional[str] = None,
                   card_type: Optional[str] = None,
                   monster_type: Optional[str] = None,
                   attribute: Optional[str] = None,
                   level: Optional[int] = None) -> int:
        """
        Count cards matching the given filters.
        
        Args:
            name: Filter by card name (partial match)
            card_type: Filter by card type (Monster, Spell, Trap)
            monster_type: Filter by monster type
            attribute: Filter by attribute
            level: Filter by level
            
        Returns:
            Count of matching cards
        """
        # Use the same search logic as search_cards but just count the results
        results = self.search_cards(
            name=name,
            card_type=card_type,
            monster_type=monster_type,
            attribute=attribute,
            level=level,
            skip=0,
            limit=len(self._cards_list)  # No limit
        )
        
        return len(results)
    
    def get_all_cards(self) -> List[Dict[str, Any]]:
        """Get all cards as a list"""
        return self._cards_list
        
    @property
    def is_loaded(self) -> bool:
        """Check if cards have been loaded"""
        return self._loaded

# Create a singleton instance
card_loader = CardLoader()