#!/usr/bin/env python3
"""
Script to set up the directory structure for card images.

This script creates the necessary directories to store card images
and adds a placeholder card back image.
"""
import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont

def create_directory_structure():
    """Create the directory structure for card images"""
    # Create the main images directory
    images_dir = os.path.join("static", "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        print(f"Created directory: {images_dir}")
    
    # Create the cards directory
    cards_dir = os.path.join(images_dir, "cards")
    if not os.path.exists(cards_dir):
        os.makedirs(cards_dir)
        print(f"Created directory: {cards_dir}")
    
    # Create a default card back image
    card_back_path = os.path.join(images_dir, "card_back.jpg")
    if not os.path.exists(card_back_path):
        create_card_back_image(card_back_path)
        print(f"Created default card back image: {card_back_path}")
    
    print("Directory structure setup complete.")

def create_card_back_image(path):
    """Create a simple card back image as a placeholder"""
    # Create a dark blue background with logo
    width, height = 420, 614  # Standard card dimensions
    image = Image.new('RGB', (width, height), (14, 41, 65))  # Dark blue
    
    # Add a pattern
    draw = ImageDraw.Draw(image)
    
    # Draw a border
    border_width = 20
    draw.rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        outline=(30, 100, 150),
        width=5
    )
    
    # Draw diagonal stripes
    for i in range(-width, height, 20):
        # Draw diagonal lines
        draw.line([(0, i), (i, 0)], fill=(10, 30, 50), width=3)
    
    # Add text
    try:
        # Try to load a font (this may fail on some systems)
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        # Fall back to default font
        font = ImageFont.load_default()
    
    # Draw the app name
    draw.text((width//2, height//2), "DuelGeist", fill=(100, 200, 255), font=font, anchor="mm")
    
    # Save the image
    image.save(path, "JPEG", quality=95)

def check_data_directory():
    """Check if the data directory exists and contains a cards.json file"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")
        print("Note: You'll need to place your cards.json file in the data directory.")
    else:
        cards_file = os.path.join(data_dir, "cards.json")
        if os.path.exists(cards_file):
            print(f"Found existing cards.json file.")
        else:
            print(f"Warning: No cards.json file found in {data_dir}.")
            print("You'll need to place your cards.json file in the data directory.")

if __name__ == "__main__":
    print("Setting up directory structure for DuelGeist...")
    create_directory_structure()
    check_data_directory()
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Place your cards.json file in the data directory")
    print("2. Place card images in static/images/cards/ with filenames matching the card IDs (e.g., 34541863.jpg)")
    print("3. Run the application with: uvicorn main:app --reload")