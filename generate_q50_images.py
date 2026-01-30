#!/usr/bin/env python3
"""
Generate Q50 variant images using OpenAI DALL-E API.
Q50 tests the relationship between circumference and diameter (π ≈ 3.14)
"""

import os
import requests
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = Path("app/data/pruebas/alternativas/Prueba-invierno-2025/Q50/approved/Q50_v2/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_and_save_image(prompt: str, filename: str):
    """Generate image with DALL-E and save to file."""
    print(f"Generating: {filename}")
    print(f"Prompt: {prompt[:100]}...")
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    
    image_url = response.data[0].url
    print(f"Generated URL: {image_url[:50]}...")
    
    # Download and save
    img_response = requests.get(image_url)
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'wb') as f:
        f.write(img_response.content)
    print(f"Saved to: {filepath}")
    return filepath

# Q50 concept: Circumference = π × diameter, so a rope around a circle covers ~3.14 diameters

# Image prompts for Q50 variants
prompts = {
    "enunciado.png": """
    Clean educational math diagram on pure white background.
    A single circle with thin black outline.
    A bright red string/rope placed exactly around the circle's edge, covering the entire circumference.
    The red string wraps completely around the circle like a ring.
    Simple, clean, minimal style. No text, no labels, no numbers.
    Educational diagram quality.
    """,
    
    "altA.png": """
    Clean educational math diagram on pure white background.
    Exactly 2 identical circles in a horizontal row, touching at one point (tangent circles).
    A straight red string/rope extends horizontally across the circles, covering 2 diameters.
    The rope starts at the left edge of the first circle and ends at the right edge of the second circle.
    Simple, clean, minimal style. No text, no labels.
    Educational diagram quality.
    """,
    
    "altB.png": """
    Clean educational math diagram on pure white background.
    Exactly 4 identical circles in a horizontal row, each touching the next at one point (tangent circles).
    A straight red string/rope extends horizontally, covering approximately 4 diameters.
    The rope starts at the left edge of the first circle and ends at the right edge of the fourth circle.
    Simple, clean, minimal style. No text, no labels.
    Educational diagram quality.
    """,
    
    "altC.png": """
    Clean educational math diagram on pure white background.
    Exactly 3 identical circles in a horizontal row, each touching the next at one point (tangent circles).
    A straight red string/rope extends horizontally, covering exactly 3 diameters.
    The rope starts at the left edge of the first circle and ends at the right edge of the third circle.
    Simple, clean, minimal style. No text, no labels.
    Educational diagram quality.
    """,
    
    "altD.png": """
    Clean educational math diagram on pure white background.
    Exactly 4 identical circles in a horizontal row, each touching the next at one point (tangent circles).
    A straight red string/rope extends horizontally, covering approximately 3.14 diameters (pi diameters).
    The rope starts at the left edge of the first circle and ends about 14% into the fourth circle.
    This is the CORRECT answer showing circumference = pi * diameter.
    Simple, clean, minimal style. No text, no labels.
    Educational diagram quality.
    """,
}

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Q50_v2 images with DALL-E 3")
    print("=" * 60)
    
    for filename, prompt in prompts.items():
        try:
            generate_and_save_image(prompt.strip(), filename)
            print("-" * 40)
        except Exception as e:
            print(f"ERROR generating {filename}: {e}")
            print("-" * 40)
    
    print("\nDone! Images saved to:", OUTPUT_DIR)
