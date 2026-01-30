#!/usr/bin/env python3
"""
Generate Q50 variant images using matplotlib for precise geometric control.
Q50 tests: Circumference = π × diameter (approximately 3.14 diameters)

Options:
- A: 2 diameters (incorrect - too few)
- B: 4 diameters (incorrect - too many)  
- C: 3 diameters (incorrect - close but not exact)
- D: ~3.14 diameters (CORRECT - this is π)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("app/data/pruebas/alternativas/Prueba-invierno-2025/Q50/approved/Q50_v2/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Circle parameters
RADIUS = 1.0
DIAMETER = 2 * RADIUS
LINE_COLOR = '#E53935'  # Red
CIRCLE_COLOR = '#212121'  # Dark gray
CIRCLE_LINEWIDTH = 3
ROPE_LINEWIDTH = 6

def setup_figure(width=10, height=4):
    """Create a figure with white background."""
    fig, ax = plt.subplots(1, 1, figsize=(width, height))
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    return fig, ax

def draw_circle(ax, center_x, center_y, radius=RADIUS):
    """Draw a circle outline."""
    circle = patches.Circle(
        (center_x, center_y), 
        radius, 
        fill=False, 
        edgecolor=CIRCLE_COLOR, 
        linewidth=CIRCLE_LINEWIDTH
    )
    ax.add_patch(circle)

def draw_rope_line(ax, start_x, end_x, y=0):
    """Draw the red rope as a horizontal line."""
    ax.plot([start_x, end_x], [y, y], color=LINE_COLOR, linewidth=ROPE_LINEWIDTH, solid_capstyle='round')
    # Add end dots
    ax.plot(start_x, y, 'o', color=LINE_COLOR, markersize=12)
    ax.plot(end_x, y, 'o', color=LINE_COLOR, markersize=12)

def draw_diameter_markers(ax, centers_x, y=0):
    """Draw small tick marks at each diameter boundary."""
    for cx in centers_x:
        # Mark left edge of each circle
        ax.plot([cx - RADIUS, cx - RADIUS], [y - 0.15, y + 0.15], color='#757575', linewidth=2)
        # Mark right edge of each circle  
        ax.plot([cx + RADIUS, cx + RADIUS], [y - 0.15, y + 0.15], color='#757575', linewidth=2)

def generate_enunciado():
    """Generate the problem statement image: a circle with rope around it."""
    fig, ax = setup_figure(6, 6)
    
    # Draw circle
    draw_circle(ax, 0, 0)
    
    # Draw red rope around the circle (as a thicker circle)
    rope_circle = patches.Circle(
        (0, 0), 
        RADIUS, 
        fill=False, 
        edgecolor=LINE_COLOR, 
        linewidth=ROPE_LINEWIDTH,
        linestyle='-'
    )
    ax.add_patch(rope_circle)
    
    ax.set_xlim(-2, 2)
    ax.set_ylim(-2, 2)
    
    filepath = OUTPUT_DIR / "enunciado.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"Generated: {filepath}")

def generate_option(num_circles, rope_length_diameters, filename):
    """
    Generate an option image with circles in a row and a rope line.
    
    Args:
        num_circles: Number of circles to draw
        rope_length_diameters: Length of rope in terms of diameters
        filename: Output filename
    """
    fig_width = max(10, num_circles * 3)
    fig, ax = setup_figure(fig_width, 4)
    
    # Calculate circle centers (tangent circles)
    centers_x = [DIAMETER * i for i in range(num_circles)]
    
    # Draw circles
    for cx in centers_x:
        draw_circle(ax, cx, 0)
    
    # Calculate rope endpoints
    # Rope starts at the leftmost point of the first circle
    rope_start = -RADIUS
    # Rope length = rope_length_diameters * diameter
    rope_end = rope_start + (rope_length_diameters * DIAMETER)
    
    # Draw the rope
    draw_rope_line(ax, rope_start, rope_end, 0)
    
    # Set limits with padding
    padding = 1
    ax.set_xlim(-RADIUS - padding, centers_x[-1] + RADIUS + padding)
    ax.set_ylim(-RADIUS - padding, RADIUS + padding)
    
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Q50_v2 images with matplotlib")
    print("=" * 60)
    
    # Generate enunciado (circle with rope around it)
    print("\n1. Generating enunciado (circle with rope around circumference)...")
    generate_enunciado()
    
    # Generate options
    # Option A: 2 diameters (incorrect - too short)
    print("\n2. Generating Option A (2 diameters - incorrect)...")
    generate_option(num_circles=3, rope_length_diameters=2.0, filename="altA.png")
    
    # Option B: 4 diameters (incorrect - too long)
    print("\n3. Generating Option B (4 diameters - incorrect)...")
    generate_option(num_circles=5, rope_length_diameters=4.0, filename="altB.png")
    
    # Option C: 3 diameters (incorrect - close but not exact)
    print("\n4. Generating Option C (3 diameters - incorrect)...")
    generate_option(num_circles=4, rope_length_diameters=3.0, filename="altC.png")
    
    # Option D: π ≈ 3.14159 diameters (CORRECT!)
    print("\n5. Generating Option D (π ≈ 3.14 diameters - CORRECT)...")
    generate_option(num_circles=4, rope_length_diameters=np.pi, filename="altD.png")
    
    print("\n" + "=" * 60)
    print(f"Done! Images saved to: {OUTPUT_DIR}")
    print("=" * 60)
