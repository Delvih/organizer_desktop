#!/usr/bin/env python3
"""
Create application icons for SmartFolderOrganizer.
Design: dark rounded background, open folder, neon-violet magic wand with spark.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw


# ── helpers ──────────────────────────────────────────────────────────────────

def _rr(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    """Draw a rounded rectangle, clamping radius to fit."""
    x0, y0, x1, y1 = xy
    r = max(0, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
    if r == 0:
        draw.rectangle([x0, y0, x1, y1], fill=fill)
        return
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0,       y0,       x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0,       x1,       y0 + 2*r], fill=fill)
    draw.ellipse([x0,       y1 - 2*r, x0 + 2*r, y1      ], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1,       y1      ], fill=fill)




# ── main drawing ─────────────────────────────────────────────────────────────

def create_icon_image(size: int = 256) -> Image.Image:
    s = size / 256  # uniform scale factor

    # ── canvas ───────────────────────────────────────────────────────────────
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── background: very dark navy with slight radial vignette ───────────────
    bg_color  = (18, 14, 40, 255)       # #120e28
    _rr(draw, [0, 0, size - 1, size - 1], int(44 * s), bg_color)
    # soft centre highlight
    cx, cy = size // 2, size // 2
    grad_r = int(120 * s)
    for step in range(grad_r, 0, -2):
        alpha = int(18 * (1 - step / grad_r))
        draw.ellipse(
            [cx - step, cy - step, cx + step, cy + step],
            fill=(100, 60, 220, alpha)
        )

    # ── folder body ──────────────────────────────────────────────────────────
    FOLD_BG   = (45,  35, 100, 255)    # dark indigo body
    FOLD_EDGE = (70,  55, 150, 255)    # lighter top edge
    FOLD_TAB  = (60,  45, 130, 255)    # tab

    # tab (top-left bump)
    tx0, ty0 = int(38*s), int(96*s)
    tx1, ty1 = int(110*s), int(118*s)
    draw.polygon([
        (tx0, ty1), (tx1, ty1),
        (int(tx1 - 12*s), ty0), (tx0, ty0)
    ], fill=FOLD_TAB)

    # main folder rectangle
    fx0, fy0 = int(38*s), int(112*s)
    fx1, fy1 = int(218*s), int(206*s)
    _rr(draw, [fx0, fy0, fx1, fy1], int(14*s), FOLD_BG)

    # top edge highlight strip
    draw.rectangle([fx0 + int(14*s), fy0, fx1 - int(14*s), fy0 + int(6*s)], fill=FOLD_EDGE)

    # ── magic wand ────────────────────────────────────────────────────────────
    # Wand: a thin diagonal rod from bottom-left to upper-right of folder
    WAND_COLOR  = (200, 180, 255, 245)   # pale violet
    WAND_W      = max(2, int(6 * s))

    wx0, wy0 = int(68*s),  int(188*s)   # handle base
    wx1, wy1 = int(185*s), int(80*s)    # tip

    # Shadow
    draw.line([(wx0+3, wy0+3), (wx1+3, wy1+3)], fill=(0,0,0,80), width=WAND_W + 2)
    # Wand rod
    draw.line([(wx0, wy0), (wx1, wy1)], fill=WAND_COLOR, width=WAND_W)

    # Wand star / sparkle at the tip ──────────────────────────────────────────
    STAR_COLOR  = (220, 160, 255, 255)  # neon-violet

    tip_x, tip_y = wx1, wy1

    # Glow rings (layered soft circles)
    for r_step, alpha in [(int(28*s), 40), (int(18*s), 70), (int(10*s), 120)]:
        draw.ellipse(
            [tip_x - r_step, tip_y - r_step,
             tip_x + r_step, tip_y + r_step],
            fill=(180, 80, 255, alpha)
        )

    # 8-pointed star
    STAR_R_OUTER = int(20 * s)
    STAR_R_INNER = int(8  * s)
    pts = []
    for i in range(16):
        angle = math.radians(i * 22.5 - 90)
        r = STAR_R_OUTER if i % 2 == 0 else STAR_R_INNER
        pts.append((tip_x + r * math.cos(angle),
                    tip_y + r * math.sin(angle)))
    draw.polygon(pts, fill=STAR_COLOR)

    # Bright centre dot
    dot_r = int(5 * s)
    draw.ellipse(
        [tip_x - dot_r, tip_y - dot_r,
         tip_x + dot_r, tip_y + dot_r],
        fill=(255, 240, 255, 255)
    )

    # Small scatter sparkles around the tip
    sparks = [
        (tip_x + int(28*s), tip_y - int(14*s), int(4*s)),
        (tip_x - int(20*s), tip_y - int(24*s), int(3*s)),
        (tip_x + int(36*s), tip_y + int(10*s), int(3*s)),
        (tip_x - int(32*s), tip_y + int(8*s),  int(2*s)),
    ]
    for sx, sy, sr in sparks:
        draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(220, 180, 255, 200))

    # ── subtle inner folder shine (top edge) ─────────────────────────────────
    shine_alpha = int(40)
    draw.rectangle(
        [fx0 + int(20*s), fy0 + int(8*s),
         fx1 - int(20*s), fy0 + int(22*s)],
        fill=(255, 255, 255, shine_alpha)
    )

    # ── very faint outer glow ring (icon border) ──────────────────────────────
    for border_step, b_alpha in [(3, 25), (6, 15), (10, 8)]:
        x1_bs = size - border_step - 1
        if x1_bs > border_step:   # skip if too small to draw
            _rr(draw,
                [border_step, border_step, x1_bs, x1_bs],
                int(44 * s),
                (138, 43, 226, b_alpha))

    return img


# ── entry points ─────────────────────────────────────────────────────────────

def create_icon():
    """Create PNG and ICO icons in the assets directory."""
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    img_256 = create_icon_image(256)

    png_path = assets_dir / "icon.png"
    img_256.save(png_path, format="PNG")
    print(f"[OK] Created {png_path}")

    ico_path = assets_dir / "icon.ico"
    frames = [create_icon_image(sz).convert("RGBA") for sz in (16, 32, 48, 64, 128, 256)]
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )
    print(f"[OK] Created {ico_path}")
    print("Icon creation complete.")


if __name__ == "__main__":
    try:
        create_icon()
    except ImportError:
        print("ERROR: Pillow is not installed.  pip install Pillow")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
