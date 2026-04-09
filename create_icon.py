#!/usr/bin/env python3
"""
Create a simple icon for FileOrganizer using PIL.
Run this script once to generate assets/icon.ico and assets/icon.png
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_icon():
    """Create a simple icon (⚡ lightning bolt symbol)."""
    size = 256
    img = Image.new('RGB', (size, size), color='#2b2b2b')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple lightning bolt shape
    # Lightning top point
    points = [
        (128, 10),   # top
        (90, 100),   # left upper
        (110, 100),  # indent
        (80, 200),   # left middle
        (140, 130),  # right indent
        (120, 130),  # left indent
        (160, 10),   # top right
    ]
    
    # Draw filled polygon (lightning bolt)
    draw.polygon(points, fill='#5B8AF5', outline='#3D6FF0')
    
    # Save as both ICO and PNG
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Save as PNG
    img.save(assets_dir / "icon.png")
    print(f"✓ Created {assets_dir / 'icon.png'}")
    
    # Save as ICO (multiple sizes)
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for width, height in icon_sizes:
        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save(assets_dir / "icon.ico", sizes=[(s[0], s[0]) for s in icon_sizes])
    print(f"✓ Created {assets_dir / 'icon.ico'}")
    print("\nIcon creation completed! You can now run the application.")

if __name__ == "__main__":
    try:
        create_icon()
    except ImportError:
        print("ERROR: Pillow is not installed.")
        print("Install it with: pip install Pillow")
    except Exception as e:
        print(f"ERROR: {e}")
