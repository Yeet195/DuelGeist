from fastapi import WebSocket
from typing import Dict, List, Any
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map game_id to list of connected WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Map WebSocket to player info
        self.socket_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, game_id: int, player_info: Dict[str, Any] = None):
        """Connect a WebSocket to a specific game"""
        await websocket.accept()
        
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        
        self.active_connections[game_id].append(websocket)
        
        if player_info:
            self.socket_info[websocket] = {
                "game_id": game_id,
                "player_info": player_info
            }
        else:
            self.socket_info[websocket] = {
                "game_id": game_id
            }
        
        logger.info(f"Client connected to game {game_id}. Total connections: {len(self.active_connections[game_id])}")
        
        # Notify about new connection
        await self.broadcast(
            game_id, 
            {
                "type": "connection_update", 
                "connected_players": len(self.active_connections[game_id])
            }
        )
    
    def disconnect(self, websocket: WebSocket, game_id: int):
        """Disconnect a WebSocket from a game"""
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
                
                # Clean up empty games
                if not self.active_connections[game_id]:
                    del self.active_connections[game_id]
        
        if websocket in self.socket_info:
            del self.socket_info[websocket]
            
        logger.info(f"Client disconnected from game {game_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        await websocket.send_json(message)
    
    async def broadcast(self, game_id: int, message: dict):
        """Broadcast a message to all connected WebSockets in a game"""
        if game_id not in self.active_connections:
            return
            
        disconnected = []
        
        for connection in self.active_connections[game_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(connection)
        
        # Clean up any connections that failed
        for conn in disconnected:
            self.disconnect(conn, game_id)
    
    async def broadcast_to_others(self, game_id: int, message: dict, current_websocket: WebSocket):
        """Broadcast a message to all connected WebSockets in a game except the sender"""
        if game_id not in self.active_connections:
            return
            
        for connection in self.active_connections[game_id]:
            if connection != current_websocket:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    self.disconnect(connection, game_id)