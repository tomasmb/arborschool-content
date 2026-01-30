#!/usr/bin/env python3
"""
Generate Q50_v1 images: Rolling wheel variant.
Concept: A wheel rolls along a line equal to its circumference.
The mark touches the ground exactly once (one full rotation = circumference distance).

Options:
- A: Mark touches 2 times (incorrect)
- B: Mark touches 4 times (incorrect)  
- C: Mark touches 3 times (incorrect)
- D: Mark touches 1 time (CORRECT - one full rotation)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("app/data/pruebas/alternativas/Prueba-invierno-2025/Q50/approved/Q50_v1/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RADIUS = 1.0
WHEEL_COLOR = '#424242'
MARK_COLOR = '#E53935'  # Red
LINE_COLOR = '#757575'
GROUND_COLOR = '#BDBDBD'

def setup_figure(width=12, height=5):
    fig, ax = plt.subplots(1, 1, figsize=(width, height))
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    return fig, ax

def draw_wheel_with_mark(ax, center_x, center_y, angle_deg=0, radius=RADIUS):
    """Draw a wheel with a red mark at a specific angle."""
    # Draw wheel outline
    wheel = patches.Circle((center_x, center_y), radius, fill=False, 
                           edgecolor=WHEEL_COLOR, linewidth=3)
    ax.add_patch(wheel)
    
    # Draw the mark (a line from center to edge at the given angle)
    angle_rad = np.radians(angle_deg)
    mark_x = center_x + radius * np.cos(angle_rad)
    mark_y = center_y + radius * np.sin(angle_rad)
    ax.plot([center_x, mark_x], [center_y, mark_y], color=MARK_COLOR, linewidth=4)
    ax.plot(mark_x, mark_y, 'o', color=MARK_COLOR, markersize=10)

def generate_enunciado():
    """Show a wheel with a mark at the bottom, ready to roll."""
    fig, ax = setup_figure(8, 6)
    
    # Draw wheel at starting position
    center_y = RADIUS + 0.5
    draw_wheel_with_mark(ax, 0, center_y, angle_deg=-90)  # Mark at bottom
    
    # Draw ground line
    ax.axhline(y=0.5, color=GROUND_COLOR, linewidth=3, linestyle='-')
    
    # Draw red mark on ground where it touches
    ax.plot(0, 0.5, 'o', color=MARK_COLOR, markersize=12)
    
    ax.set_xlim(-3, 3)
    ax.set_ylim(-0.5, 4)
    
    filepath = OUTPUT_DIR / "enunciado.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated: {filepath}")

def generate_option(num_marks, filename, is_correct=False):
    """
    Generate an option showing the wheel having rolled, with marks on ground.
    The rope (circumference) is shown as the distance traveled.
    """
    fig, ax = setup_figure(14, 5)
    
    # Total distance = circumference = 2*pi*r
    circumference = 2 * np.pi * RADIUS
    
    # Draw ground line
    ax.axhline(y=0, color=GROUND_COLOR, linewidth=3, linestyle='-')
    
    # Draw the rope/distance line (red, showing circumference)
    ax.plot([-0.5, circumference + 0.5], [-0.3, -0.3], color=MARK_COLOR, 
            linewidth=4, solid_capstyle='round')
    ax.plot(-0.5, -0.3, 'o', color=MARK_COLOR, markersize=10)
    ax.plot(circumference + 0.5, -0.3, 'o', color=MARK_COLOR, markersize=10)
    
    # Draw wheel at final position (after rolling the circumference distance)
    center_y = RADIUS + 0.1
    final_x = circumference
    
    if is_correct:
        # Correct answer: mark is exactly at bottom again (one full rotation)
        draw_wheel_with_mark(ax, final_x, center_y, angle_deg=-90)
    else:
        # Wrong answers: show intermediate position
        rotations = 1.0 / num_marks  # Wrong number of rotations
        angle = -90 + (360 * rotations)  # Partial rotation
        draw_wheel_with_mark(ax, final_x, center_y, angle_deg=angle)
    
    # Draw marks on ground
    if is_correct:
        # Only one mark at start and one at end (same position relative to wheel)
        mark_positions = [0, circumference]
        ax.plot(0, 0, 'o', color=MARK_COLOR, markersize=12)
        ax.plot(circumference, 0, 'o', color=MARK_COLOR, markersize=12)
    else:
        # Multiple marks (wrong)
        spacing = circumference / num_marks
        for i in range(num_marks + 1):
            ax.plot(i * spacing, 0, 'o', color=MARK_COLOR, markersize=12)
    
    # Draw starting wheel (ghost)
    wheel_ghost = patches.Circle((0, center_y), RADIUS, fill=False, 
                                  edgecolor='#E0E0E0', linewidth=2, linestyle='--')
    ax.add_patch(wheel_ghost)
    
    ax.set_xlim(-1.5, circumference + 2)
    ax.set_ylim(-1.5, RADIUS * 2 + 1)
    
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Q50_v1 images (Rolling Wheel)")
    print("=" * 60)
    
    print("\n1. Generating enunciado...")
    generate_enunciado()
    
    print("\n2. Generating Option A (2 marks - incorrect)...")
    generate_option(num_marks=2, filename="altA.png")
    
    print("\n3. Generating Option B (4 marks - incorrect)...")
    generate_option(num_marks=4, filename="altB.png")
    
    print("\n4. Generating Option C (3 marks - incorrect)...")
    generate_option(num_marks=3, filename="altC.png")
    
    print("\n5. Generating Option D (1 mark = 1 rotation - CORRECT)...")
    generate_option(num_marks=1, filename="altD.png", is_correct=True)
    
    print("\n" + "=" * 60)
    print(f"Done! Images saved to: {OUTPUT_DIR}")
