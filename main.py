from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from typing import Optional, List, Dict, Any

from app.api import users, decks, cards, auth
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
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Home page route
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.on_event("startup")
async def startup_card_loader():
    """Load cards on application startup"""
    success = card_loader.load_cards("data/cards.json")
    if not success:
        logging.error("Failed to load card data. Check if cards.json exists.")

@app.get("/cards")
async def card_database(
    request: Request,
    search: str = "",
    card_type: str = "",
    monster_type: str = "",
    attribute: str = "", 
    level: Optional[str] = None,  # Changed from Optional[int] to Optional[str]
    page: int = 1,
    items_per_page: Optional[int] = None  # Add optional parameter for controlling items per page
):
    try:
        # Sanitize inputs to prevent errors
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
            
        # Set default items per page to 60 (or use the provided value if valid)
        try:
            if items_per_page is not None:
                items_per_page = int(items_per_page)
                # Limit to a reasonable range
                items_per_page = max(10, min(200, items_per_page))
            else:
                items_per_page = 60  # Default to 60 cards per page
        except (ValueError, TypeError):
            items_per_page = 60
            
        # Handle level parameter properly
        parsed_level = None
        if level is not None and level.strip():
            try:
                parsed_level = int(level.strip())
            except (ValueError, TypeError):
                parsed_level = None
            
        # Set up pagination
        skip = (page - 1) * items_per_page
        
        # Add debugging to see what's being passed
        logger.info(f"Search params - search: '{search}', card_type: '{card_type}', monster_type: '{monster_type}', attribute: '{attribute}', level: {level}, parsed_level: {parsed_level}, page: {page}, items_per_page: {items_per_page}")
        
        # Rest of your code remains the same, just replace the old items_per_page with the new variable
        # ...

        # Get cards using the JSON loader
        cards = card_loader.search_cards(
            name=search,
            card_type=card_type,
            monster_type=monster_type,
            attribute=attribute,
            level=parsed_level,  # Use the safely parsed level
            skip=skip,
            limit=items_per_page  # Use the dynamic items_per_page
        )
        
        # Get total count for pagination
        total_count = card_loader.count_cards(
            name=search,
            card_type=card_type,
            monster_type=monster_type,
            attribute=attribute,
            level=parsed_level  # Use the safely parsed level
        )
        
        # Always ensure we have at least some cards to display
        if len(cards) == 0:
            logger.info("No cards found with search parameters, trying fallback methods")
            
            # Fallback 1: Try with just the name parameter if provided
            if search:
                cards = card_loader.search_cards(
                    name=search,
                    skip=skip,
                    limit=items_per_page  # Use the dynamic items_per_page
                )
                total_count = card_loader.count_cards(name=search)
                
            # Fallback 2: If still empty, get a subset of all cards
            if len(cards) == 0:
                logger.info("Still no cards found, showing sample of all cards")
                cards = card_loader.get_all_cards()[skip:skip+items_per_page]
                total_count = len(card_loader.get_all_cards())
        
        # Calculate pages, handle edge cases
        if total_count <= 0:
            total_count = len(card_loader.get_all_cards())
            
        total_pages = (total_count + items_per_page - 1) // items_per_page
        total_pages = max(1, total_pages)  # Ensure at least 1 page
        
        if page > total_pages:
            page = 1
            skip = 0
            cards = card_loader.search_cards(
                name=search,
                card_type=card_type,
                monster_type=monster_type,
                attribute=attribute,
                level=parsed_level,
                skip=skip,
                limit=items_per_page  # Use the dynamic items_per_page
            )
        
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
                "level": level,  # Return the original level string for form value
                "page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "items_per_page": items_per_page  # Pass the items_per_page to the template
            }
        )
    # Rest of the error handling remains the same
    except Exception as e:
        # Log the error
        logger.error(f"Error in card_database route: {str(e)}")
        
        # Attempt to show some cards anyway
        try:
            if card_loader.is_loaded:
                fallback_cards = card_loader.get_all_cards()[:items_per_page]
            else:
                fallback_cards = []
        except:
            fallback_cards = []
        
        # Return a basic response with error information
        return templates.TemplateResponse(
            "card_database.html",
            {
                "request": request,
                "cards": fallback_cards,
                "search": search,
                "card_type": card_type,
                "monster_type": monster_type,
                "attribute": attribute,
                "level": level,
                "page": 1,
                "total_pages": 1,
                "total_count": len(fallback_cards),
                "items_per_page": items_per_page,  # Pass the items_per_page to the template
                "error": f"An error occurred: {str(e)}"
            }
        )
    
@app.get("/cards/{card_id}")
async def card_details(request: Request, card_id: str):
    try:
        # Ensure card loader is loaded
        if not card_loader.is_loaded:
            success = False
            for path in ["data/cards.json", "static/data/cards.json", "static/cards.json"]:
                success = card_loader.load_cards(path)
                if success:
                    break
        
        # Get card from JSON loader
        card = card_loader.get_card(card_id)
        
        if not card:
            logger.warning(f"Card not found: {card_id}")
            # Try as integer if it's numeric
            if card_id.isdigit():
                card = card_loader.get_card(str(int(card_id)))
                
            # If still not found, try searching by name
            if not card:
                # Find cards with similar names
                search_term = card_id.replace('-', ' ').replace('_', ' ')
                logger.info(f"Trying to find card by name: {search_term}")
                cards = card_loader.search_cards(name=search_term, limit=10)
                
                if cards:
                    # If we found multiple cards, take the closest match
                    if len(cards) > 1:
                        # Try to find an exact match first
                        exact_matches = [c for c in cards if c['name'].lower() == search_term.lower()]
                        if exact_matches:
                            card = exact_matches[0]
                        else:
                            # Otherwise take the first match
                            card = cards[0]
                    else:
                        card = cards[0]
                        
                    # If we found a card by name, redirect to its proper ID
                    if card:
                        return RedirectResponse(url=f"/cards/{card['id']}")
        
        # If still no card found, try a more aggressive fuzzy search
        if not card and len(card_id) > 2:
            # Find cards that contain any part of the search
            all_cards = card_loader.get_all_cards()
            potential_matches = []
            search_parts = card_id.lower().replace('-', ' ').replace('_', ' ').split()
            
            for c in all_cards:
                name = c.get('name', '').lower()
                # Count how many search parts match the name
                matches = sum(1 for part in search_parts if part in name)
                if matches > 0:
                    potential_matches.append((c, matches))
            
            # Sort by number of matches (highest first)
            potential_matches.sort(key=lambda x: x[1], reverse=True)
            
            if potential_matches:
                card = potential_matches[0][0]
                # Redirect to the correct ID
                return RedirectResponse(url=f"/cards/{card['id']}")
        
        return templates.TemplateResponse(
            "card_details.html",
            {
                "request": request,
                "card": card
            }
        )
    except Exception as e:
        logger.error(f"Error in card_details route: {str(e)}")
        return templates.TemplateResponse(
            "card_details.html",
            {
                "request": request,
                "card": None,
                "error": str(e)
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