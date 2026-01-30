#!/usr/bin/env python3
"""
Generate Q50_v2 images: Radii as clock hands variant.
Concept: Cut the circumference rope into radius-length pieces.
Place them inside the circle like clock hands.
How many radii fit? Answer: 2π ≈ 6.28 radii

Options:
- A: 4 radii (incorrect - too few)
- B: 8 radii (incorrect - too many)  
- C: 6 radii (incorrect - close but not exact)
- D: 6 radii + partial ≈ 2π (CORRECT)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("app/data/pruebas/alternativas/Prueba-invierno-2025/Q50/approved/Q50_v2/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RADIUS = 2.0
CIRCLE_COLOR = '#424242'
ROPE_COLOR = '#E53935'  # Red

def setup_figure(width=8, height=8):
    fig, ax = plt.subplots(1, 1, figsize=(width, height))
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    return fig, ax

def draw_circle(ax, center_x=0, center_y=0, radius=RADIUS):
    """Draw a circle outline."""
    circle = patches.Circle((center_x, center_y), radius, fill=False, 
                            edgecolor=CIRCLE_COLOR, linewidth=3)
    ax.add_patch(circle)

def draw_radii_as_hands(ax, num_full_radii, partial_fraction=0, center_x=0, center_y=0, radius=RADIUS):
    """
    Draw radii arranged like clock hands.
    
    Args:
        num_full_radii: Number of complete radius-length segments
        partial_fraction: Fraction of an additional radius (0-1)
    """
    total_radii = num_full_radii + partial_fraction
    
    # Arrange radii evenly in a fan/clock pattern
    for i in range(num_full_radii):
        # Calculate angle for this radius (starting from top, going clockwise)
        angle = np.pi/2 - (2 * np.pi * i / total_radii)
        
        end_x = center_x + radius * np.cos(angle)
        end_y = center_y + radius * np.sin(angle)
        
        ax.plot([center_x, end_x], [center_y, end_y], 
                color=ROPE_COLOR, linewidth=5, solid_capstyle='round')
        ax.plot(end_x, end_y, 'o', color=ROPE_COLOR, markersize=8)
    
    # Draw partial radius if any
    if partial_fraction > 0:
        i = num_full_radii
        angle = np.pi/2 - (2 * np.pi * i / total_radii)
        
        # Partial length
        partial_length = radius * partial_fraction
        end_x = center_x + partial_length * np.cos(angle)
        end_y = center_y + partial_length * np.sin(angle)
        
        ax.plot([center_x, end_x], [center_y, end_y], 
                color=ROPE_COLOR, linewidth=5, solid_capstyle='round')
        ax.plot(end_x, end_y, 'o', color=ROPE_COLOR, markersize=8)
    
    # Draw center point
    ax.plot(center_x, center_y, 'o', color=CIRCLE_COLOR, markersize=10)

def generate_enunciado():
    """Show circle with rope around circumference, then cut into pieces."""
    fig, ax = setup_figure(10, 8)
    
    # Draw circle
    draw_circle(ax)
    
    # Draw rope around circumference
    rope_circle = patches.Circle((0, 0), RADIUS, fill=False, 
                                  edgecolor=ROPE_COLOR, linewidth=6)
    ax.add_patch(rope_circle)
    
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    
    filepath = OUTPUT_DIR / "enunciado.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated: {filepath}")

def generate_option(num_radii, partial=0, filename="option.png"):
    """Generate an option with radii arranged as clock hands."""
    fig, ax = setup_figure(8, 8)
    
    # Draw circle
    draw_circle(ax)
    
    # Draw radii as clock hands
    draw_radii_as_hands(ax, num_radii, partial)
    
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.5, 3.5)
    
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Q50_v2 images (Radii as Clock Hands)")
    print("Correct answer: 2π ≈ 6.28 radii")
    print("=" * 60)
    
    print("\n1. Generating enunciado (circle with rope)...")
    generate_enunciado()
    
    print("\n2. Generating Option A (4 radii - incorrect)...")
    generate_option(num_radii=4, filename="altA.png")
    
    print("\n3. Generating Option B (8 radii - incorrect)...")
    generate_option(num_radii=8, filename="altB.png")
    
    print("\n4. Generating Option C (6 radii - incorrect, close but not exact)...")
    generate_option(num_radii=6, filename="altC.png")
    
    # 2π ≈ 6.283, so we need 6 full radii + 0.283 of a radius
    print("\n5. Generating Option D (6 + 0.28 ≈ 2π radii - CORRECT)...")
    generate_option(num_radii=6, partial=0.283, filename="altD.png")
    
    print("\n" + "=" * 60)
    print(f"Done! Images saved to: {OUTPUT_DIR}")
