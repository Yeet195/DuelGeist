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
		
		Args:
			name: Filter by card name (partial match)
			card_type: Filter by card type (monster, spell, trap)
			monster_type: Filter by monster type (Normal, Effect, etc.) or race
			attribute: Filter by attribute (DARK, LIGHT, etc.)
			level: Filter by monster level/rank
			skip: Number of results to skip (for pagination)
			limit: Maximum number of results to return
			
		Returns:
			List of matching card dictionaries
		"""
		# Ensure cards are loaded
		if not self._loaded and not self.load_cards():
			return []
			
		# Handle empty or invalid parameters
		skip = max(0, skip if isinstance(skip, int) else 0)
		limit = max(1, min(1000, limit if isinstance(limit, int) else 100))
		
		# Sanitize string parameters - empty strings, None, or non-string values should be treated as None
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
			
		# If all parameters are None, return all cards (with pagination)
		if all(param is None for param in [name, card_type, monster_type, attribute, level]):
			logger.debug("All search parameters are empty, returning all cards")
			paginated_results = self._cards_list[skip:skip + limit]
			return paginated_results
		
		# Dictionary to track all matched cards and their match scores
		# Higher score = better match
		scored_cards = {}
		
		# First pass: look for exact matches to all criteria
		exact_matches = []
		
		for card in self._cards_list:
			# Calculate match score for this card
			score = 0
			
			# Check name match - highest priority
			name_match = False
			if name:
				# Different levels of name matching
				card_name = card.get('name', '').lower()
				search_name = name.lower()
				
				if card_name == search_name:  # Exact match
					score += 100
					name_match = True
				elif card_name.startswith(search_name):  # Starts with search term
					score += 75
					name_match = True
				elif search_name in card_name:  # Contains search term
					score += 50
					name_match = True
				elif self._name_matches(card_name, search_name):  # Word match
					score += 25
					name_match = True
					
				# If name is provided but doesn't match at all, this card is irrelevant
				if not name_match:
					continue
			
			# Check card type
			card_type_match = False
			if card_type:
				# Determine the card's type in multiple ways to be more robust
				card_type_value = card_type.lower()
				
				# Method 1: Check the card_type field we added during processing
				if 'card_type' in card and card_type_value == card['card_type'].lower():
					score += 20
					card_type_match = True
				
				# Method 2: Check the frameType field
				elif 'frameType' in card:
					ft = card['frameType'].lower()
					if card_type_value == 'monster' and ft in ('normal', 'effect', 'ritual', 'fusion', 'synchro', 'xyz', 'link', 'token'):
						score += 15
						card_type_match = True
					elif card_type_value == ft:
						score += 20
						card_type_match = True
				
				# Method 3: Check the type string
				elif 'type' in card:
					type_str = card['type'].lower()
					if (card_type_value == 'monster' and 'monster' in type_str) or \
					(card_type_value == 'spell' and 'spell' in type_str) or \
					(card_type_value == 'trap' and 'trap' in type_str):
						score += 15
						card_type_match = True
				
				# If card_type is provided but doesn't match at all, consider skipping
				if card_type_match:
					score += 10  # Bonus for matching card type
				elif card_type in ['monster', 'spell', 'trap']:
					continue  # Skip if it's a main type and doesn't match
			
			# Determine if this is a monster card for monster-specific filters
			is_monster = False
			if 'card_type' in card and card['card_type'] == 'monster':
				is_monster = True
			elif 'frameType' in card and card['frameType'].lower() in ('normal', 'effect', 'ritual', 'fusion', 'synchro', 'xyz', 'link', 'token'):
				is_monster = True
			elif 'type' in card and 'monster' in card['type'].lower():
				is_monster = True
			
			# If we have monster-specific filters but this is not a monster, skip
			if (monster_type or attribute or level is not None) and not is_monster:
				continue
			
			# Only apply monster filters to monster cards
			if is_monster:
				# Check monster type/race
				monster_type_match = False
				if monster_type:
					# Try to match in race or type fields
					monster_type_value = monster_type.lower()
					
					# Check race field
					if 'race' in card and monster_type_value in card['race'].lower():
						score += 15
						monster_type_match = True
					
					# Check type field (may contain type info)
					elif 'type' in card and monster_type_value in card['type'].lower():
						score += 10
						monster_type_match = True
					
					# If monster_type is provided but doesn't match at all, this may not be what they want
					if not monster_type_match:
						score -= 5  # Penalty but don't exclude completely
				
				# Check attribute
				attribute_match = False
				if attribute:
					# Try exact attribute match
					if 'attribute' in card and attribute.upper() == card['attribute'].upper():
						score += 15
						attribute_match = True
					
					# If attribute is provided but doesn't match at all, this may not be what they want
					if not attribute_match:
						score -= 5  # Penalty but don't exclude completely
				
				# Check level
				level_match = False
				if level is not None:
					# Cast level to int with fallback for missing or non-int values
					try:
						card_level = int(card.get('level', 0))
					except (ValueError, TypeError):
						card_level = 0
						
					if card_level == level:
						score += 15
						level_match = True
					elif card_level > 0:  # Card has a level but doesn't match
						score -= 5  # Penalty but don't exclude completely
			
			# Only add cards with a positive score
			if score > 0:
				# Record the card and its score
				scored_cards[card['id']] = (card, score)
				
				# Keep track of exact matches
				if (not name or name_match) and \
				(not card_type or card_type_match) and \
				(not monster_type or monster_type_match) and \
				(not attribute or attribute_match) and \
				(level is None or level_match):
					exact_matches.append(card)
		
		# If we have exact matches, return those first
		if exact_matches:
			logger.debug(f"Found {len(exact_matches)} exact matches")
			# Sort by name for consistency
			exact_matches.sort(key=lambda c: c.get('name', ''))
			return exact_matches[skip:skip + limit]
		
		# Sort results by score (highest first)
		sorted_results = [
			card for _, card in sorted(
				[(score, card) for card, score in scored_cards.values()],
				key=lambda x: x[0], 
				reverse=True
			)
		]
		
		# If we have results from scoring, return those
		if sorted_results:
			logger.debug(f"Found {len(sorted_results)} scored matches")
			return sorted_results[skip:skip + limit]
		
		# Last resort - fuzzy search if we have a name
		if name and len(name) > 1:
			logger.debug(f"Performing fuzzy search for name: {name}")
			fuzzy_results = []
			name_parts = name.lower().split()
			
			for card in self._cards_list:
				card_name = card.get('name', '').lower()
				
				# Check if any part of the search is in the card name
				if any(part in card_name for part in name_parts):
					fuzzy_results.append(card)
			
			if fuzzy_results:
				# Sort by name length (shorter names tend to be more relevant when doing fuzzy match)
				fuzzy_results.sort(key=lambda c: len(c.get('name', '')))
				return fuzzy_results[skip:skip + limit]
		
		# If we still have no results, return a sample of all cards
		logger.debug("No matches found, returning sample of all cards")
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