import json
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.card import Card, CardType, MonsterType, CardAttribute
from app.db import crud

def load_cards_from_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Load card data from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing card data
        
    Returns:
        List of card dictionaries
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Card database file not found: {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return data.get('data', [])
    
def import_cards_to_db(db: Session, cards_data: List[Dict[str, Any]]) -> int:
    """
    Import cards from parsed JSON data into the database.
    
    Args:
        db: Database session
        cards_data: List of card dictionaries from the JSON file
        
    Returns:
        Number of cards imported
    """
    imported_count = 0
    
    for card_data in cards_data:
        # Check if card already exists
        existing_card = crud.get_card_by_external_id(db, external_id=card_data['id'])
        if existing_card:
            continue
            
        # Determine card type
        card_type = None
        monster_type = None
        attribute = None
        
        if 'type' in card_data:
            type_lower = card_data['type'].lower()
            if 'monster' in type_lower:
                card_type = CardType.MONSTER
                
                # Determine monster type
                if 'normal' in type_lower:
                    monster_type = MonsterType.NORMAL
                elif 'fusion' in type_lower:
                    monster_type = MonsterType.FUSION
                elif 'ritual' in type_lower:
                    monster_type = MonsterType.RITUAL
                elif 'synchro' in type_lower:
                    monster_type = MonsterType.SYNCHRO
                elif 'xyz' in type_lower:
                    monster_type = MonsterType.XYZ
                elif 'link' in type_lower:
                    monster_type = MonsterType.LINK
                else:
                    monster_type = MonsterType.EFFECT
                    
                # Determine attribute if available
                if 'attribute' in card_data:
                    attr = card_data['attribute'].upper()
                    try:
                        attribute = CardAttribute[attr]
                    except KeyError:
                        # Default to DARK if attribute can't be mapped
                        attribute = CardAttribute.DARK
                        
            elif 'spell' in type_lower:
                card_type = CardType.SPELL
            elif 'trap' in type_lower:
                card_type = CardType.TRAP
        
        # Create card object
        new_card = Card(
            external_id=card_data['id'],
            name=card_data['name'],
            description=card_data.get('desc', ''),
            card_type=card_type,
            monster_type=monster_type,
            attribute=attribute,
            level=card_data.get('level', None),
            attack=card_data.get('atk', None),
            defense=card_data.get('def', None),
            
            # Spell/Trap properties
            is_continuous='Continuous' in card_data.get('race', ''),
            is_counter='Counter' in card_data.get('race', ''),
            is_equip='Equip' in card_data.get('race', ''),
            is_field='Field' in card_data.get('race', ''),
            is_quick_play='Quick-Play' in card_data.get('race', ''),
            
            # Set image path
            image_path=f"{card_data['id']}.jpg"
        )
        
        db.add(new_card)
        imported_count += 1
        
        # Commit in batches to avoid memory issues
        if imported_count % 100 == 0:
            db.commit()
    
    # Final commit
    db.commit()
    return imported_count