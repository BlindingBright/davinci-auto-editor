#!/usr/bin/env python3
"""
Generate app icons for DaVinci Auto-Editor AI.
Requires: pip install pillow
Outputs into src-tauri/icons/
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = REPO_ROOT / "src-tauri" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)


def create_icon(size: int) -> Image.Image:
    """Draw a clapperboard icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(2, size // 12)
    radius = max(4, size // 8)

    # ── Dark background ──────────────────────────────────────
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=(14, 14, 20, 255),
    )

    # ── Red top bar (clapperboard stripe) ────────────────────
    bar_h = max(6, size // 5)
    draw.rounded_rectangle(
        [pad, pad, size - pad, pad + bar_h],
        radius=radius,
        fill=(220, 38, 38, 255),
    )
    # Clip the bottom corners of the bar to stay inside the rounded bg
    draw.rectangle(
        [pad, pad + bar_h - radius, size - pad, pad + bar_h],
        fill=(220, 38, 38, 255),
    )

    # ── Diagonal white stripes on the bar ────────────────────
    stripe_w = max(4, size // 7)
    for i in range(-1, 8):
        x0 = pad + i * stripe_w
        draw.polygon(
            [
                (x0, pad),
                (x0 + stripe_w * 2 // 3, pad),
                (x0 + stripe_w * 2 // 3 - stripe_w // 3, pad + bar_h),
                (x0 - stripe_w // 3, pad + bar_h),
            ],
            fill=(255, 255, 255, 160),
        )

    # ── Play triangle ─────────────────────────────────────────
    cx = size // 2
    cy = pad + bar_h + (size - pad - bar_h - pad) // 2
    half = max(6, size // 4)
    draw.polygon(
        [
            (cx - half * 2 // 5, cy - half * 3 // 4),
            (cx - half * 2 // 5, cy + half * 3 // 4),
            (cx + half * 3 // 4, cy),
        ],
        fill=(220, 38, 38, 255),
    )

    return img


def save_all():
    specs = {
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 256,
    }

    images = {}
    for filename, sz in specs.items():
        img = create_icon(sz)
        img.save(ICONS_DIR / filename)
        images[sz] = img
        print(f"  ✓ {filename} ({sz}x{sz})")

    # ── ICO (Windows) — embed multiple sizes ─────────────────
    ico_sizes = [16, 32, 48, 64, 128, 256]
    ico_imgs = [create_icon(s) for s in ico_sizes]
    ico_imgs[0].save(
        ICONS_DIR / "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_imgs[1:],
    )
    print("  ✓ icon.ico (multi-size)")

    print(f"\nAll icons saved to: {ICONS_DIR}")


if __name__ == "__main__":
    print("Generating DaVinci Auto-Editor AI icons...")
    save_all()
