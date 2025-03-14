from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any

from app.api import users, decks, cards
from app.ws.connection import ConnectionManager
from app.models.game_pydantic import GameState
from app.db.database import get_db, engine
from app.db import crud
from app.utils.card_loader import card_loader
import app.models as models

import uvicorn
import logging
from typing import Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(title="Improved Duelingbook")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, set to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Initialize WebSocket connection manager
manager = ConnectionManager()

# Active games - In a production app, this would be in a database or Redis
active_games: Dict[int, GameState] = {}

# Include API routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(decks.router, prefix="/api/decks", tags=["decks"])
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])

# Home page route
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.on_event("startup")
async def startup_card_loader():
    """Load cards on application startup"""
    success = card_loader.load_cards("data/cards.json")
    if not success:
        logging.error("Failed to load card data. Check if cards.json exists.")

# Card database page
@app.get("/cards")
async def card_database(
    request: Request,
    search: str = "",
    card_type: str = "",
    monster_type: str = "",
    attribute: str = "", 
    level: Optional[int] = None,  # Changed to accept None by default
    page: int = 1
):
    # Set up pagination
    items_per_page = 20
    skip = (page - 1) * items_per_page
    
    # Add debugging to see what's being passed
    logger.info(f"Search params - search: '{search}', card_type: '{card_type}', level: {level}, page: {page}")
    
    # Get cards using the JSON loader
    cards = card_loader.search_cards(
        name=search if search else None,
        card_type=card_type if card_type else None,
        monster_type=monster_type if monster_type else None,
        attribute=attribute if attribute else None,
        level=level,  # Level could be None
        skip=skip,
        limit=items_per_page
    )
    
    # Get total count for pagination
    total_count = card_loader.count_cards(
        name=search if search else None,
        card_type=card_type if card_type else None,
        monster_type=monster_type if monster_type else None,
        attribute=attribute if attribute else None,
        level=level
    )
    
    # Calculate pages
    total_pages = (total_count + items_per_page - 1) // items_per_page
    total_pages = max(1, total_pages)  # Ensure at least 1 page
    
    # Log results
    logger.info(f"Search results: Found {total_count} cards, showing page {page} of {total_pages}")
    
    return templates.TemplateResponse(
        "card_database.html",
        {
            "request": request,
            "cards": cards,
            "search": search,
            "card_type": card_type,
            "monster_type": monster_type,
            "attribute": attribute,
            "level": level,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count
        }
    )
    
# Card details page
@app.get("/cards/{card_id}")
async def card_details(request: Request, card_id: str):
    # Get card from JSON loader
    card = card_loader.get_card(card_id)
    
    if not card:
        return templates.TemplateResponse("404.html", {"request": request})
    
    return templates.TemplateResponse(
        "card_details.html",
        {
            "request": request,
            "card": card
        }
    )

# Game page
@app.get("/game/{game_id}")
async def game(request: Request, game_id: int):
    # If game doesn't exist, create a new one
    if game_id not in active_games:
        active_games[game_id] = GameState(id=game_id)
    
    return templates.TemplateResponse(
        "game.html", 
        {"request": request, "game_id": game_id}
    )

# HTMX endpoints for partial updates

@app.get("/partials/game/{game_id}/field")
async def game_field(request: Request, game_id: int):
    game = active_games.get(game_id)
    if not game:
        return {"error": "Game not found"}
    
    return templates.TemplateResponse(
        "partials/field.html",
        {"request": request, "game": game}
    )

@app.get("/partials/game/{game_id}/hand")
async def player_hand(request: Request, game_id: int, player_id: int):
    game = active_games.get(game_id)
    if not game:
        return {"error": "Game not found"}
    
    # In a real app, verify the player's identity
    
    return templates.TemplateResponse(
        "partials/hand.html",
        {"request": request, "game": game, "player_id": player_id}
    )

# WebSocket endpoint for game
@app.websocket("/ws/game/{game_id}")
async def websocket_game(websocket: WebSocket, game_id: int):
    await manager.connect(websocket, game_id)
    try:
        while True:
            # Receive JSON data from client
            data = await websocket.receive_json()
            
            # Process game action
            game = active_games.get(game_id)
            if not game:
                await websocket.send_json({"error": "Game not found"})
                continue
            
            # Process action based on type
            action_type = data.get("action")
            if action_type == "play_card":
                # Logic to play a card
                card_id = data.get("card_id")
                position = data.get("position")
                # Update game state...
                
            elif action_type == "attack":
                # Logic for attack
                attacker = data.get("attacker")
                target = data.get("target")
                # Update game state...
            
            # Send updated game state to all connected clients
            await manager.broadcast(game_id, {"type": "game_update", "game": game.dict()})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
        await manager.broadcast(
            game_id, 
            {"type": "player_disconnect", "message": "A player disconnected"}
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)