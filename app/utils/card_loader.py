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
				# If the main file is not found, try to load from static directory
				alt_path = os.path.join("static", "data", "cards.json")
				if not os.path.exists(alt_path):
					logger.error(f"Alternative card database file not found: {alt_path}")
					return False
				file_path = alt_path
				
			with open(file_path, 'r', encoding='utf-8') as f:
				data = json.load(f)
				
			cards = data.get('data', [])
			
			# Index cards by ID for quick lookup
			self._cards_by_id = {str(card['id']): self._process_card(card) for card in cards}
			self._cards_list = [self._process_card(card) for card in cards]
			self._loaded = True
			
			logger.info(f"Successfully loaded {len(cards)} cards from {file_path}")
			return True
		
		except Exception as e:
			logger.error(f"Failed to load cards from {file_path}: {str(e)}")
			return False
	
	def _process_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Process a card to ensure it has all necessary fields and mappings.
		
		Args:
			card: The card data to process
			
		Returns:
			Processed card data
		"""
		# Ensure card has standard fields, even if they're None
		processed_card = card.copy()
		
		# Add card_type field based on frameType or type
		if 'card_type' not in processed_card:
			if 'frameType' in processed_card:
				ft = processed_card['frameType'].lower()
				if ft in ('normal', 'effect', 'ritual', 'fusion', 'synchro', 'xyz', 'link', 'token'):
					processed_card['card_type'] = 'monster'
				elif ft == 'spell':
					processed_card['card_type'] = 'spell'
				elif ft == 'trap':
					processed_card['card_type'] = 'trap'
				else:
					# Try to determine from type string
					card_type = self._get_card_type_category(processed_card.get('type', ''))
					processed_card['card_type'] = card_type
			else:
				# Try to determine from type string
				card_type = self._get_card_type_category(processed_card.get('type', ''))
				processed_card['card_type'] = card_type
				
		# Set default for fields that might be missing
		defaults = {
			'desc': processed_card.get('desc', ''),
			'description': processed_card.get('desc', ''),  # Add description alias for templates
			'external_id': processed_card.get('id', 0),  # Add external_id for compatibility
			'image_path': f"{processed_card.get('id', 0)}.jpg",  # Set default image path
		}
		
		for key, value in defaults.items():
			if key not in processed_card:
				processed_card[key] = value
				
		return processed_card
	
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
		Search for cards with various filters, always returning the best possible results.
		"""
		# Ensure cards are loaded
		if not self._loaded and not self.load_cards():
			return []
			
		# Handle empty parameters
		skip = max(0, skip)
		limit = max(1, min(1000, limit))
		
		# If all parameters are None, return all cards (with pagination)
		if name is None and card_type is None and monster_type is None and attribute is None and level is None:
			return self._cards_list[skip:skip + limit]
		
		# Make search terms case-insensitive
		if name:
			name = name.lower()
		if card_type and isinstance(card_type, str):
			card_type = card_type.lower()
		if monster_type and isinstance(monster_type, str):
			monster_type = monster_type.lower()
		
		# Cards that match all criteria
		exact_matches = []
		# Cards that match some criteria
		partial_matches = []
		
		for card in self._cards_list:
			# Score how well this card matches (higher is better)
			score = 0
			matches_all = True
			
			# Name matching
			if name:
				card_name = card.get('name', '').lower()
				if name == card_name:
					score += 100  # Exact match
				elif name in card_name:
					score += 50   # Substring match
				elif any(word in card_name for word in name.split()):
					score += 25   # Any word matches
				else:
					matches_all = False
			
			# Card type matching
			if card_type:
				card_type_val = card.get('card_type', '').lower()
				if not card_type_val:
					# Try to determine from type field
					if 'type' in card:
						if 'monster' in card['type'].lower():
							card_type_val = 'monster'
						elif 'spell' in card['type'].lower():
							card_type_val = 'spell'
						elif 'trap' in card['type'].lower():
							card_type_val = 'trap'
							
				if card_type == card_type_val:
					score += 30
				else:
					matches_all = False
			
			# Monster type matching
			if monster_type and (not card_type or card_type == 'monster'):
				found_match = False
				# Check race field
				if 'race' in card and monster_type in card['race'].lower():
					score += 20
					found_match = True
				# Check type field
				elif 'type' in card and monster_type in card['type'].lower():
					score += 15
					found_match = True
				# Check monster_type field
				elif 'monster_type' in card and monster_type in card.get('monster_type', '').lower():
					score += 25
					found_match = True
					
				if not found_match:
					matches_all = False
			
			# Attribute matching
			if attribute:
				attr_value = card.get('attribute', '')
				if isinstance(attr_value, str) and attribute.upper() == attr_value.upper():
					score += 20
				else:
					matches_all = False
			
			# Level matching
			if level is not None:
				card_level = card.get('level')
				# Convert string level to int if needed
				if isinstance(card_level, str):
					try:
						card_level = int(card_level)
					except ValueError:
						card_level = None
						
				if card_level == level:
					score += 20
				else:
					matches_all = False
			
			# Add to appropriate list based on match quality
			if matches_all:
				exact_matches.append(card)
			elif score > 0:
				partial_matches.append((card, score))
		
		# If we have exact matches, return those first
		if exact_matches:
			return exact_matches[skip:skip + limit]
		
		# Otherwise, sort partial matches by score and return
		if partial_matches:
			partial_matches.sort(key=lambda x: x[1], reverse=True)
			return [card for card, _ in partial_matches][skip:skip + limit]
		
		# If no matches at all, try a more lenient search with just the name
		if name:
			lenient_matches = []
			for card in self._cards_list:
				card_name = card.get('name', '').lower()
				# Match if any part of the search is in the name
				if any(part in card_name for part in name.split()):
					lenient_matches.append(card)
			
			if lenient_matches:
				return lenient_matches[skip:skip + limit]
		
		# If still no matches, return some cards to avoid empty results
		return self._cards_list[skip:skip + limit]
	
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
		# Ensure cards are loaded
		if not self._loaded and not self.load_cards():
			return 0
		
		# If no cards are loaded, return 0
		if not self._cards_list:
			return 0
			
		# Sanitize parameters for consistency with search_cards
		def sanitize_str(param):
			if param is None or not isinstance(param, str) or param.strip() == '':
				return None
			return param.strip()
			
		name = sanitize_str(name)
		card_type = sanitize_str(card_type)
		monster_type = sanitize_str(monster_type)
		attribute = sanitize_str(attribute)
		
		# Ensure level is an int or None
		if level is not None:
			try:
				level = int(level)
			except (ValueError, TypeError):
				level = None
				
		# If all parameters are None, return total count
		if all(param is None for param in [name, card_type, monster_type, attribute, level]):
			return len(self._cards_list)
			
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
		# Ensure cards are loaded
		if not self._loaded and not self.load_cards():
			return []
			
		return self._cards_list
		
	@property
	def is_loaded(self) -> bool:
		"""Check if cards have been loaded"""
		return self._loaded

# Create a singleton instance
card_loader = CardLoader()