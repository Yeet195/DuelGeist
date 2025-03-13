from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Optional, Any, Union
import time


class CardPosition(str, Enum):
    DECK = "deck"
    HAND = "hand"
    FIELD_MONSTER = "field_monster"
    FIELD_SPELL = "field_spell"
    FIELD_TRAP = "field_trap"
    GRAVEYARD = "graveyard"
    BANISHED = "banished"


class CardOrientation(str, Enum):
    FACE_UP_ATTACK = "face_up_attack"
    FACE_UP_DEFENSE = "face_up_defense"
    FACE_DOWN_DEFENSE = "face_down_defense"
    FACE_DOWN = "face_down"


class GamePhase(str, Enum):
    DRAW_PHASE = "draw_phase"
    STANDBY_PHASE = "standby_phase"
    MAIN_PHASE_1 = "main_phase_1"
    BATTLE_PHASE = "battle_phase"
    MAIN_PHASE_2 = "main_phase_2"
    END_PHASE = "end_phase"


class PlayerState(BaseModel):
    id: int
    username: str
    life_points: int = 8000
    deck: List[int] = []  # List of card IDs
    hand: List[int] = []
    field_monsters: Dict[int, Dict[str, Any]] = {}  # Position -> Card details
    field_spells: Dict[int, Dict[str, Any]] = {}    # Position -> Card details
    field_traps: Dict[int, Dict[str, Any]] = {}     # Position -> Card details
    graveyard: List[int] = []
    banished: List[int] = []
    extra_deck: List[int] = []
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "username": "duelist123",
                "life_points": 8000,
                "hand": [1234, 5678],
                "field_monsters": {
                    "1": {
                        "id": 9012,
                        "orientation": "face_up_attack"
                    }
                }
            }
        }


class GameAction(BaseModel):
    action_type: str
    player_id: int
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any] = {}


class GameState(BaseModel):
    id: int
    status: str = "waiting"  # waiting, active, completed
    turn_player_id: Optional[int] = None
    phase: GamePhase = GamePhase.DRAW_PHASE
    players: Dict[int, PlayerState] = {}
    spectators: List[int] = []
    action_history: List[GameAction] = []
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    
    def add_player(self, player_id: int, username: str):
        """Add a player to the game"""
        if len(self.players) >= 2:
            raise ValueError("Game already has 2 players")
        
        self.players[player_id] = PlayerState(id=player_id, username=username)
        
        # If this is the first player, set them as the turn player
        if len(self.players) == 1:
            self.turn_player_id = player_id
        
        # If we now have 2 players, start the game
        if len(self.players) == 2:
            self.status = "active"
        
        self.updated_at = time.time()
    
    def remove_player(self, player_id: int):
        """Remove a player from the game"""
        if player_id in self.players:
            del self.players[player_id]
            
            # If we have only one player left, set them as the turn player
            if len(self.players) == 1:
                self.turn_player_id = list(self.players.keys())[0]
            
            # If no players left, reset the game
            if len(self.players) == 0:
                self.status = "waiting"
                self.turn_player_id = None
            
            self.updated_at = time.time()
    
    def add_action(self, action_type: str, player_id: int, data: Dict[str, Any] = {}):
        """Add an action to the game history"""
        action = GameAction(
            action_type=action_type,
            player_id=player_id,
            data=data
        )
        self.action_history.append(action)
        self.updated_at = time.time()
        
        return action
    
    def next_phase(self):
        """Advance to the next game phase"""
        phases = list(GamePhase)
        current_index = phases.index(self.phase)
        next_index = (current_index + 1) % len(phases)
        self.phase = phases[next_index]
        
        # If we've gone through all phases, change the turn player
        if next_index == 0:
            player_ids = list(self.players.keys())
            current_index = player_ids.index(self.turn_player_id)
            next_index = (current_index + 1) % len(player_ids)
            self.turn_player_id = player_ids[next_index]
        
        self.updated_at = time.time()