"""Generiert ein Test-GIF (640x640, 1 Frame) fuer den ersten Kraken-LCD-Push.

Usage:
    python scripts/make_test_gif.py
    → schreibt frames/test.gif
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 640  # liquidctl skaliert auf Device-Framebuffer (Kraken 2023: 240×240) per Pillow.resize
OUT_PATH = Path(__file__).resolve().parents[1] / "frames" / "test.png"

BG = "#0D0A1E"
PRIMARY = "#8B5CF6"
TEXT = "#FFFFFF"
MUTED = "#AAAAAA"

# Font-Fallback-Chain. Windows-Standard-Fonts zuerst.
FONT_CANDIDATES = [
    "seguisb.ttf",  # Segoe UI Semibold
    "segoeui.ttf",
    "arial.ttf",
    "DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    # Fallback: PIL-Default (bitmap, klein, aber crasht nicht)
    return ImageFont.load_default()


def make_test_image() -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    # Aeusserer Akzent-Ring
    ring_width = 12
    draw.arc(
        [(30, 30), (SIZE - 30, SIZE - 30)],
        start=0,
        end=360,
        fill=PRIMARY,
        width=ring_width,
    )

    # Grosse Headline
    font_big = load_font(96)
    draw.text((SIZE / 2, SIZE / 2 - 40), "KRAKEN", fill=TEXT, anchor="mm", font=font_big)

    font_sub = load_font(48)
    draw.text((SIZE / 2, SIZE / 2 + 40), "TEST", fill=PRIMARY, anchor="mm", font=font_sub)

    font_small = load_font(28)
    draw.text(
        (SIZE / 2, SIZE / 2 + 120),
        "claude-monitor v0.1",
        fill=MUTED,
        anchor="mm",
        font=font_small,
    )

    return img


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img = make_test_image()
    # Als PNG speichern (static-Mode; gif-Mode auf FW 2.X.Y nicht supported,
    # liquidctl Issue #631).
    img.save(OUT_PATH, format="PNG", optimize=True)
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"[OK] {OUT_PATH} ({SIZE}x{SIZE}, {size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
