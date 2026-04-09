#!/usr/bin/env python3
"""
Create application icons for FileOrganizer.
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_icon():
    """Create PNG and ICO icons in the assets directory."""
    size = 256
    img = Image.new("RGB", (size, size), color="#2b2b2b")
    draw = ImageDraw.Draw(img)

    points = [
        (128, 10),
        (90, 100),
        (110, 100),
        (80, 200),
        (140, 130),
        (120, 130),
        (160, 10),
    ]
    draw.polygon(points, fill="#5B8AF5", outline="#3D6FF0")

    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"

    img.save(png_path)
    print(f"[OK] Created {png_path}")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, sizes=sizes)
    print(f"[OK] Created {ico_path}")
    print("Icon creation completed.")


if __name__ == "__main__":
    try:
        create_icon()
    except ImportError:
        print("ERROR: Pillow is not installed.")
        print("Install it with: pip install Pillow")
    except Exception as e:
        print(f"ERROR: {e}")
