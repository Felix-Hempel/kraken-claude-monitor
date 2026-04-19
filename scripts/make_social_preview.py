"""Erzeugt das GitHub Social-Preview-Image (1280×640).

Wird in den Repo-Settings unter "Social preview" hochgeladen — sorgt fuer
ein eigenes Open-Graph-Bild beim Teilen auf Twitter/Discord/Reddit etc.
statt des generischen GitHub-Avatars.

Usage:
    python scripts/make_social_preview.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from kraken_monitor import theme as T
from kraken_monitor.ccusage import QuotaSnapshot
from kraken_monitor.config import ThemeConfig
from kraken_monitor.renderer import _draw_spaced_text, render_frame

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots" / "social-preview.png"
W, H = 1280, 640


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    theme = ThemeConfig()
    now = datetime.now(UTC)

    # Live-Frame als Hero rechts (640×640, exakt wie aufm LCD).
    frame_path = OUT.parent / "_social_active.png"
    render_frame(
        QuotaSnapshot(
            total_tokens=int(0.26 * 850_000_000),
            burn_rate_tpm=2500.0,
            block_start=now - timedelta(minutes=142),
            block_end=now + timedelta(minutes=158),
            time_remaining_sec=158 * 60,
            is_active=True,
            fetched_at=now,
            detected_limit=850_000_000,
        ),
        850_000_000,
        theme,
        output_path=frame_path,
    )
    hero = Image.open(frame_path).convert("RGB")
    frame_path.unlink()

    # Canvas
    img = Image.new("RGB", (W, H), theme.bg_color)
    # Hero rechts platzieren, vertikal zentriert
    img.paste(hero, (W - 640, 0))

    # Text-Block links
    draw = ImageDraw.Draw(img)
    left_x = 320  # zentriert in der linken 640×640-Hälfte

    title_font = T.load_font(72, "black")
    tagline_font = T.load_font(28, "bold")
    sub_font = T.load_font(22, "regular")

    # Title — auf zwei Zeilen damit's passt
    draw.text((left_x, 220), "kraken-claude", fill=theme.text_color, anchor="mm", font=title_font)
    draw.text((left_x, 300), "-monitor", fill=theme.primary_color, anchor="mm", font=title_font)

    # Tagline
    draw.text(
        (left_x, 380),
        "Live Claude Code quota",
        fill=theme.text_color,
        anchor="mm",
        font=tagline_font,
    )
    draw.text(
        (left_x, 415),
        "on the NZXT Kraken LCD",
        fill=theme.text_color,
        anchor="mm",
        font=tagline_font,
    )

    # Footer-Tags (mit letter-spacing)
    _draw_spaced_text(
        draw,
        left_x,
        500,
        "PYTHON  ·  LIQUIDCTL  ·  WINDOWS",
        sub_font,
        theme.muted_color,
        0.18,
    )

    img.save(OUT, format="PNG", optimize=True)
    print(f"[OK] {OUT.relative_to(Path.cwd())} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
