#!/usr/bin/env python3
"""
Debug script to test card database loading and search functionality.
Run this script independently to verify card loading and search is working correctly.
"""
import os
import json
import sys
from typing import Dict, List, Any, Optional

def load_cards(file_path):
    """Load cards from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('data', [])
    except Exception as e:
        print(f"Error loading cards: {e}")
        return []

def name_matches(card_name, search_term):
    """Check if card name matches search term"""
    if not search_term or not card_name:
        return not search_term
    
    card_name_lower = card_name.lower()
    search_term_lower = search_term.lower()
    
    # Direct substring match
    if search_term_lower in card_name_lower:
        print(f"  Match: '{search_term_lower}' found in '{card_name_lower}'")
        return True
    
    # Word matching
    search_words = search_term_lower.split()
    if all(word in card_name_lower for word in search_words):
        print(f"  Match: All words {search_words} found in '{card_name_lower}'")
        return True
    
    print(f"  No match: '{search_term_lower}' not in '{card_name_lower}'")
    return False

def get_card_type_category(card_type):
    """Get card type category (monster, spell, trap)"""
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

def search_cards(cards, name=None, card_type=None):
    """Search cards by name and type"""
    results = []
    
    print(f"\nSearching for name='{name}', type='{card_type}'")
    
    for card in cards:
        # Apply name filter
        if name:
            if not name_matches(card.get('name', ''), name):
                continue
        
        # Apply card type filter
        if card_type:
            card_category = get_card_type_category(card.get('type', ''))
            if card_category != card_type.lower():
                print(f"  Type mismatch: Card '{card.get('name')}' type '{card.get('type')}' doesn't match '{card_type}'")
                continue
        
        # Card passed all filters
        print(f"  ✓ Found match: {card.get('name')}")
        results.append(card)
    
    return results

def main():
    """Main function"""
    # Check if data/cards.json exists
    file_path = "data/cards.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please create this file first.")
        return 1
    
    # Load cards
    print(f"Loading cards from {file_path}...")
    cards = load_cards(file_path)
    print(f"Loaded {len(cards)} cards.")
    
    # Print a few examples to verify data structure
    print("\nSample cards:")
    for i, card in enumerate(cards[:3]):
        print(f"{i+1}. {card.get('name')} - Type: {card.get('type')}")
    
    # Test some searches
    search_cards(cards, name="Dark")
    search_cards(cards, name="Magician")
    search_cards(cards, name="Dark Magician")
    
    search_cards(cards, card_type="monster")
    search_cards(cards, card_type="spell")
    search_cards(cards, card_type="trap")
    
    # Combined search
    search_cards(cards, name="Dark", card_type="monster")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())