"""Theme-Konstanten + Font-Loader.

Layout-Spec stammt aus `Kraken Quota Display.html` (5 Mockups, Design v2 mit
Claude-Orange-Branding). Alle visuellen Magic-Numbers an einer Stelle, damit
der Renderer frei von Layout-Konstanten bleibt.
"""

from __future__ import annotations

from PIL import ImageFont

# Canvas — wir rendern in 640×640 und lassen liquidctl auf das Device-
# Framebuffer (240×240) skalieren. Grösseres Canvas gibt schärferen Text
# nach Downsampling + einfacheres Layout-Denken.
LCD_SIZE = 640
RING_CENTER = LCD_SIZE // 2

# Ring-Geometrie. HTML-Mockup hatte stroke=32, im Live-Test zu dünn auf
# dem 240×240-Framebuffer — auf 64 erhöht für deutliche Präsenz.
# RING_RADIUS = Mittellinie. Außenkante = RADIUS + STROKE/2.
RING_RADIUS = 282  # Außenkante bei 282+32 = 314 (6px Abstand zum LCD-Rand)
RING_STROKE = 64
RING_TRACK_THIN = 14  # IDLE-Variante (siehe HTML-Mockup 03)

# Y-Positionen (siehe Mockups, top=0 ist obere Kante)
LABEL_TOP_Y = 132 + 12  # Label-Anchor "mm" sitzt auf Mitte → +font/2 Korrektur
BIG_NUM_Y = LCD_SIZE // 2 - 28  # transform: translate(-50%, -62%) ≈ -28px Vertikal
SUB_Y = LCD_SIZE - 168  # höher gerückt: weniger Konflikt mit unterem Ring-Cap
SUB_HINT_OFFSET = -34  # "Resets in" über der Time
STALE_SUB_Y = LCD_SIZE - 180  # höher gerückt um Platz für Badge unten
STALE_BADGE_Y = LCD_SIZE - 80

# Font-Größen (siehe HTML-CSS)
FONT_SIZE_LABEL = 24
FONT_SIZE_BIG_NUM = 228
FONT_SIZE_BIG_PCT = 74
FONT_SIZE_SUB_HINT = 20
FONT_SIZE_SUB_TIME = 46
FONT_SIZE_IDLE_TITLE = 92
FONT_SIZE_IDLE_HINT = 22
FONT_SIZE_PAUSED_TITLE = 62
FONT_SIZE_PAUSED_TIME = 38
FONT_SIZE_BADGE = 18
FONT_SIZE_OVER_TAG = 28

# Letter-Spacing (em-Faktoren aus HTML-CSS, für Pillow per char gerendert).
LETTER_SPACING_LABEL = 0.44  # "CLAUDE", "OVER"
LETTER_SPACING_HINT = 0.30  # "RESETS IN", "LAST UPDATE", "NO ACTIVE SESSION"
LETTER_SPACING_BADGE = 0.32  # "STALE · 4m ago"
LETTER_SPACING_OVER = 0.50  # "OVER"
LETTER_SPACING_IDLE_TITLE = 0.02  # subtle für große Wörter
LETTER_SPACING_PAUSED_TITLE = 0.02

# Pause-Bars (zwei vertikale Balken, siehe HTML-Mockup 04)
PAUSE_BAR_WIDTH = 42
PAUSE_BAR_HEIGHT = 124
PAUSE_BAR_GAP = 28

# Idle-Dot
IDLE_DOT_RADIUS = 14

# Idle-Notches (4 Cardinal Lines am Außenrand)
IDLE_NOTCH_LENGTH = 24
IDLE_NOTCH_WIDTH = 4

# Stale-Badge
STALE_BADGE_BORDER = 3
STALE_BADGE_PADDING_X = 22
STALE_BADGE_PADDING_Y = 10
STALE_BADGE_SQUARE = 12

# Dashed Arc (PAUSED Ring)
PAUSED_DASH_LENGTH = 44
PAUSED_DASH_GAP = 26

# Schwellen für color_for_pct: Claude Orange ist die Standard-Anzeige.
# danger nur bei OVER (≥100%) — wird im Renderer separat als OVER-Branch behandelt.
PCT_DANGER_AT = 100.0


# Font-Fallback-Chains nach Weight (Windows-Defaults zuerst).
_FONT_CHAINS = {
    "black": [
        "seguibl.ttf",  # Segoe UI Black
        "segoeuib.ttf",  # Segoe UI Bold
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "bold": [
        "segoeuib.ttf",  # Segoe UI Bold
        "seguisb.ttf",  # Segoe UI Semibold
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "semibold": [
        "seguisb.ttf",  # Segoe UI Semibold
        "segoeuib.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "segoeui.ttf",
        "arial.ttf",
        "DejaVuSans.ttf",
    ],
}


class FontNotFoundError(RuntimeError):
    """Keine Schriftart aus der Fallback-Kette gefunden."""


def load_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    """Lädt Schrift in gewünschtem Gewicht. Fallback-Chain garantiert
    funktionierende Schrift auf allen Zielsystemen."""
    chain = _FONT_CHAINS.get(weight, _FONT_CHAINS["regular"])
    for name in chain:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise FontNotFoundError(f"Keine Schrift für weight={weight!r} gefunden. Probiert: {chain}")


def color_for_pct(pct: float, theme) -> str:  # noqa: ANN001 — theme ist ThemeConfig
    """Standard-Ringfarbe ist Claude Orange. Danger erst bei ≥100% (OVER)."""
    if pct >= PCT_DANGER_AT:
        return theme.danger_color
    return theme.primary_color
