"""Frame-Renderer: rendert den Quota-Status als 640×640 PNG.

Layout-Spec: `Kraken Quota Display.html` (5 Mockups). Vier Anzeige-States:
  - ACTIVE: Ring + große Prozent-Zahl + Reset-Zeit (mit OVER-Variante bei >100%)
  - IDLE: Thin Track + 4 Cardinal Notches + "IDLE"-Stack
  - PAUSED: Dashed Warn-Ring + Pause-Bars + "Last update HH:MM"
  - STALE: Wie ACTIVE aber alle Farben muted + "STALE"-Badge

Layout-Konstanten in `theme.py`. Pillow-Beschränkungen:
  - Kein Letter-Spacing nativ → `_draw_spaced_text` rendert per char mit Offset
  - Kein Dashed-Stroke nativ → `_draw_dashed_arc` mehrere `arc()`-Calls
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import theme as T
from .ccusage import QuotaSnapshot
from .config import ThemeConfig

log = logging.getLogger(__name__)

_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "frames" / "live.png"


def format_time_remaining(sec: int) -> str:
    """`9480 → "2h 38m"`, `1800 → "30m"`, `40 → "<1m"`, negative → "0m"`."""
    if sec < 60:
        return "<1m" if sec > 0 else "0m"
    minutes = sec // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder}m"


# ----------------------------------------------------------------------------
# Drawing-Helper
# ----------------------------------------------------------------------------


def _ring_bbox(radius: int) -> tuple[int, int, int, int]:
    c = T.RING_CENTER
    return (c - radius, c - radius, c + radius, c + radius)


def _ring_endpoint(angle_deg: float) -> tuple[float, float]:
    """Punkt auf der Mittellinie des Rings bei gegebenem Winkel (0=3-Uhr, +CW).

    Wichtig: PIL `draw.arc(bbox, ..., width=N)` zeichnet den Strich nach
    **innen** von der bbox-Grenze. Die Mittellinie liegt also bei
    `RING_RADIUS - RING_STROKE/2`, nicht bei RING_RADIUS selbst.
    """
    midline_radius = T.RING_RADIUS - T.RING_STROKE / 2
    rad = math.radians(angle_deg)
    return (
        T.RING_CENTER + midline_radius * math.cos(rad),
        T.RING_CENTER + midline_radius * math.sin(rad),
    )


def _draw_round_cap(draw: ImageDraw.ImageDraw, angle_deg: float, color: str) -> None:
    """Vollkreis (Durchmesser = stroke) als Cap am Ende des Progress-Arcs.

    Pillow hat kein `stroke-linecap="round"`. Workaround: am Endpunkt einen
    Kreis mit dem Stroke-Durchmesser zeichnen — die Hälfte überlappt mit dem
    Arc, die andere Hälfte rundet die Kante ab.
    """
    cx, cy = _ring_endpoint(angle_deg)
    r = T.RING_STROKE / 2
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


def _draw_solid_ring(
    draw: ImageDraw.ImageDraw,
    pct: float,
    fill_color: str,
    track_color: str,
) -> None:
    """Track + farbcodierter Progress-Arc mit gerundeten Enden.

    Sweep startet bei 12 Uhr im Uhrzeigersinn. Bei pct=100% ist es ein voller
    Kreis und die Caps fallen mit dem Arc selbst zusammen — kein visueller
    Überstand.
    """
    bbox = _ring_bbox(T.RING_RADIUS)
    draw.arc(bbox, 0, 360, fill=track_color, width=T.RING_STROKE)
    if pct <= 0:
        return
    sweep = min(360.0, pct / 100.0 * 360.0)
    start_angle = -90.0
    end_angle = start_angle + sweep
    draw.arc(bbox, start_angle, end_angle, fill=fill_color, width=T.RING_STROKE)
    # Rounded caps an Anfang und Ende — bei sweep<360° sichtbar als
    # halbkreisförmige Abrundung der Stroke-Enden.
    if sweep < 360.0:
        _draw_round_cap(draw, start_angle, fill_color)
        _draw_round_cap(draw, end_angle, fill_color)


def _draw_full_ring(draw: ImageDraw.ImageDraw, color: str) -> None:
    """Komplett gefüllter Ring (für OVER-State)."""
    draw.arc(_ring_bbox(T.RING_RADIUS), 0, 360, fill=color, width=T.RING_STROKE)


def _draw_dashed_ring(
    draw: ImageDraw.ImageDraw,
    track_color: str,
    dash_color: str,
) -> None:
    """Track + dashed Overlay (für PAUSED-State)."""
    bbox = _ring_bbox(T.RING_RADIUS)
    draw.arc(bbox, 0, 360, fill=track_color, width=T.RING_STROKE)
    # Dash- und Gap-Längen aus HTML sind Pixel auf Umfang. Auf 360° umrechnen.
    circumference = 2 * 3.14159265 * T.RING_RADIUS
    dash_deg = T.PAUSED_DASH_LENGTH / circumference * 360
    gap_deg = T.PAUSED_DASH_GAP / circumference * 360
    angle = -90.0
    end_at = 270.0
    while angle < end_at:
        next_angle = min(end_at, angle + dash_deg)
        draw.arc(bbox, angle, next_angle, fill=dash_color, width=T.RING_STROKE)
        angle = next_angle + gap_deg


def _draw_thin_track(draw: ImageDraw.ImageDraw, color: str) -> None:
    """Schmaler Track (IDLE-State)."""
    draw.arc(_ring_bbox(T.RING_RADIUS), 0, 360, fill=color, width=T.RING_TRACK_THIN)


def _draw_cardinal_notches(draw: ImageDraw.ImageDraw, color: str) -> None:
    """4 kurze Striche an 12/3/6/9 Uhr — Akzent für IDLE."""
    c = T.RING_CENTER
    outer = c + T.RING_RADIUS + T.RING_STROKE // 2
    inner = outer - T.IDLE_NOTCH_LENGTH
    w = T.IDLE_NOTCH_WIDTH
    # Top (12 Uhr)
    draw.rectangle((c - w // 2, c - outer, c + w // 2, c - inner), fill=color)
    # Bottom (6 Uhr)
    draw.rectangle((c - w // 2, c + inner, c + w // 2, c + outer), fill=color)
    # Left (9 Uhr)
    draw.rectangle((c - outer, c - w // 2, c - inner, c + w // 2), fill=color)
    # Right (3 Uhr)
    draw.rectangle((c + inner, c - w // 2, c + outer, c + w // 2), fill=color)


def _measure_spaced_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, spacing_em: float
) -> float:
    spacing_px = font.size * spacing_em
    widths = [draw.textlength(c, font=font) for c in text]
    return sum(widths) + spacing_px * max(0, len(text) - 1)


def _draw_spaced_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: str,
    spacing_em: float,
) -> None:
    """Text mit letter-spacing, horizontal an center_x zentriert.

    Pillow hat kein natives letter-spacing. `anchor="mm"` referenziert den
    vertikalen Mittelpunkt des Glyphs.
    """
    spacing_px = font.size * spacing_em
    total = _measure_spaced_text(draw, text, font, spacing_em)
    cur_x = center_x - total / 2
    for ch in text:
        w = draw.textlength(ch, font=font)
        draw.text((cur_x + w / 2, y), ch, fill=color, font=font, anchor="mm")
        cur_x += w + spacing_px


def _draw_text_center(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: str,
) -> None:
    draw.text((T.RING_CENTER, y), text, fill=color, anchor="mm", font=font)


def _draw_big_number(
    draw: ImageDraw.ImageDraw,
    y: int,
    value: str,
    suffix: str,
    value_color: str,
    suffix_color: str,
) -> None:
    """Grosse Prozentzahl mit kleinerem Suffix (z.B. "67" + "%")."""
    val_font = T.load_font(T.FONT_SIZE_BIG_NUM, "black")
    suf_font = T.load_font(T.FONT_SIZE_BIG_PCT, "black")
    val_w = draw.textlength(value, font=val_font)
    suf_w = draw.textlength(suffix, font=suf_font)
    spacer = 6  # px Lücke zwischen Zahl und %
    total = val_w + spacer + suf_w
    start_x = T.RING_CENTER - total / 2
    draw.text((start_x, y), value, fill=value_color, font=val_font, anchor="lm")
    # Suffix-Baseline so platzieren, dass Zahl-Top und Suffix-Top etwa gleich
    # liegen (im HTML: `vertical-align: 18px` = Suffix sitzt höher).
    suf_y = y - (T.FONT_SIZE_BIG_NUM - T.FONT_SIZE_BIG_PCT) // 2 + 18
    draw.text(
        (start_x + val_w + spacer, suf_y), suffix, fill=suffix_color, font=suf_font, anchor="lm"
    )


# ----------------------------------------------------------------------------
# State-Renderer
# ----------------------------------------------------------------------------


def _render_active(
    img: Image.Image,
    snapshot: QuotaSnapshot,
    plan_limit: int,
    theme: ThemeConfig,
    *,
    stale: bool,
) -> None:
    draw = ImageDraw.Draw(img)
    raw_pct = snapshot.total_tokens / plan_limit * 100 if plan_limit > 0 else 0.0
    is_over = raw_pct >= 100.0
    pct = min(100.0, max(0.0, raw_pct))

    if is_over:
        _render_over(img, raw_pct, snapshot, theme)
        return

    ring_fill = T.color_for_pct(pct, theme)
    label_color = theme.muted_color
    val_color = theme.text_color
    suffix_color = theme.muted_color
    time_color = theme.text_color

    if stale:
        ring_fill = theme.muted_color
        label_color = "#4a4843"
        val_color = theme.muted_color
        suffix_color = "#5a5852"
        time_color = theme.muted_color

    _draw_solid_ring(draw, pct, ring_fill, theme.track_color)
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        T.LABEL_TOP_Y,
        "CLAUDE",
        T.load_font(T.FONT_SIZE_LABEL, "bold"),
        label_color,
        T.LETTER_SPACING_LABEL,
    )
    _draw_big_number(
        draw,
        T.BIG_NUM_Y,
        f"{pct:.0f}",
        "%",
        val_color,
        suffix_color,
    )

    sub_y = T.STALE_SUB_Y if stale else T.SUB_Y
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        sub_y + T.SUB_HINT_OFFSET,
        "RESETS IN",
        T.load_font(T.FONT_SIZE_SUB_HINT, "bold"),
        theme.muted_color if not stale else "#5a5852",
        T.LETTER_SPACING_HINT,
    )
    _draw_text_center(
        draw,
        sub_y,
        format_time_remaining(snapshot.time_remaining_sec),
        T.load_font(T.FONT_SIZE_SUB_TIME, "black"),
        time_color,
    )

    if stale:
        _draw_stale_badge(draw, theme)


def _render_over(
    img: Image.Image,
    raw_pct: float,
    snapshot: QuotaSnapshot,
    theme: ThemeConfig,
) -> None:
    draw = ImageDraw.Draw(img)
    _draw_full_ring(draw, theme.danger_color)
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        T.LABEL_TOP_Y,
        "OVER",
        T.load_font(T.FONT_SIZE_OVER_TAG, "black"),
        theme.danger_color,
        T.LETTER_SPACING_OVER,
    )
    # Bei sehr großen Prozentwerten (>999) deckeln, sonst sprengt's das Layout.
    display_pct = min(999, int(raw_pct))
    _draw_big_number(
        draw,
        T.BIG_NUM_Y,
        f"{display_pct}",
        "%",
        theme.danger_color,
        theme.danger_color,
    )
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        T.SUB_Y + T.SUB_HINT_OFFSET,
        "RESETS IN",
        T.load_font(T.FONT_SIZE_SUB_HINT, "bold"),
        theme.muted_color,
        T.LETTER_SPACING_HINT,
    )
    _draw_text_center(
        draw,
        T.SUB_Y,
        format_time_remaining(snapshot.time_remaining_sec),
        T.load_font(T.FONT_SIZE_SUB_TIME, "black"),
        theme.text_color,
    )


def _render_idle(img: Image.Image, theme: ThemeConfig) -> None:
    draw = ImageDraw.Draw(img)
    _draw_thin_track(draw, "#1F1E1B")
    _draw_cardinal_notches(draw, "#3a3833")
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        T.LABEL_TOP_Y,
        "CLAUDE",
        T.load_font(T.FONT_SIZE_LABEL, "bold"),
        "#4a4843",
        T.LETTER_SPACING_LABEL,
    )
    # Idle-Stack: dot + IDLE + hint, vertikal zentriert
    stack_center = T.RING_CENTER
    dot_y = stack_center - 80
    title_y = stack_center
    hint_y = stack_center + 78
    draw.ellipse(
        (
            T.RING_CENTER - T.IDLE_DOT_RADIUS,
            dot_y - T.IDLE_DOT_RADIUS,
            T.RING_CENTER + T.IDLE_DOT_RADIUS,
            dot_y + T.IDLE_DOT_RADIUS,
        ),
        fill=theme.muted_color,
    )
    _draw_text_center(
        draw,
        title_y,
        "IDLE",
        T.load_font(T.FONT_SIZE_IDLE_TITLE, "black"),
        theme.text_color,
    )
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        hint_y,
        "NO ACTIVE SESSION",
        T.load_font(T.FONT_SIZE_IDLE_HINT, "bold"),
        theme.muted_color,
        T.LETTER_SPACING_HINT,
    )


def _render_paused(img: Image.Image, last_update: datetime | None, theme: ThemeConfig) -> None:
    draw = ImageDraw.Draw(img)
    _draw_dashed_ring(draw, theme.track_color, theme.warning_color)
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        T.LABEL_TOP_Y,
        "PAUSED",
        T.load_font(T.FONT_SIZE_LABEL, "bold"),
        theme.warning_color,
        T.LETTER_SPACING_LABEL,
    )
    # Pause-Bars (zwei Vertikal-Balken) + "Monitor off" darunter, zentriert.
    bars_top = T.RING_CENTER - 90
    bars_bottom = bars_top + T.PAUSE_BAR_HEIGHT
    bar_total_w = 2 * T.PAUSE_BAR_WIDTH + T.PAUSE_BAR_GAP
    bars_left = T.RING_CENTER - bar_total_w // 2
    draw.rectangle(
        (bars_left, bars_top, bars_left + T.PAUSE_BAR_WIDTH, bars_bottom),
        fill=theme.warning_color,
    )
    bar2_left = bars_left + T.PAUSE_BAR_WIDTH + T.PAUSE_BAR_GAP
    draw.rectangle(
        (bar2_left, bars_top, bar2_left + T.PAUSE_BAR_WIDTH, bars_bottom),
        fill=theme.warning_color,
    )
    _draw_text_center(
        draw,
        bars_bottom + 60,
        "Monitor off",
        T.load_font(T.FONT_SIZE_PAUSED_TITLE, "black"),
        theme.text_color,
    )
    # Last-Update-Stempel ganz unten.
    stamp_y = T.SUB_Y
    _draw_spaced_text(
        draw,
        T.RING_CENTER,
        stamp_y + T.SUB_HINT_OFFSET,
        "LAST UPDATE",
        T.load_font(T.FONT_SIZE_SUB_HINT, "bold"),
        theme.muted_color,
        T.LETTER_SPACING_HINT,
    )
    if last_update is not None:
        local = last_update.astimezone()
        stamp = local.strftime("%H:%M")
    else:
        stamp = "--:--"
    _draw_text_center(
        draw,
        stamp_y,
        stamp,
        T.load_font(T.FONT_SIZE_PAUSED_TIME, "black"),
        theme.text_color,
    )


def _draw_stale_badge(draw: ImageDraw.ImageDraw, theme: ThemeConfig) -> None:
    """Border-Box "STALE" mit Square-Indikator unten zentriert."""
    text = "STALE"
    font = T.load_font(T.FONT_SIZE_BADGE, "black")
    text_w = _measure_spaced_text(draw, text, font, T.LETTER_SPACING_BADGE)
    sq = T.STALE_BADGE_SQUARE
    inner_gap = 12
    inner_w = sq + inner_gap + text_w
    box_w = inner_w + 2 * T.STALE_BADGE_PADDING_X
    box_h = T.FONT_SIZE_BADGE + 2 * T.STALE_BADGE_PADDING_Y
    box_x0 = T.RING_CENTER - box_w / 2
    box_y0 = T.STALE_BADGE_Y - box_h / 2
    box_x1 = box_x0 + box_w
    box_y1 = box_y0 + box_h
    # Border (Pillow's outline-Width geht erst ab Pillow 9, ist hier sicher).
    draw.rectangle(
        (box_x0, box_y0, box_x1, box_y1),
        outline=theme.warning_color,
        width=T.STALE_BADGE_BORDER,
    )
    # Square-Indikator links
    sq_x = box_x0 + T.STALE_BADGE_PADDING_X
    sq_y = T.STALE_BADGE_Y - sq // 2
    draw.rectangle((sq_x, sq_y, sq_x + sq, sq_y + sq), fill=theme.warning_color)
    # Text rechts vom Square, mit Spacing
    text_start_x = sq_x + sq + inner_gap + text_w / 2
    _draw_spaced_text(
        draw,
        int(text_start_x),
        T.STALE_BADGE_Y,
        text,
        font,
        theme.warning_color,
        T.LETTER_SPACING_BADGE,
    )


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def render_frame(
    snapshot: QuotaSnapshot | None,
    plan_limit: int,
    theme: ThemeConfig,
    *,
    stale: bool = False,
    output_path: Path | None = None,
) -> Path:
    """Rendert einen Live-Frame und speichert als PNG.

    Args:
        snapshot: None oder is_active=False → IDLE-Frame.
        plan_limit: Session-Token-Limit (aus config oder ccusage detected_limit).
        theme: Farb-Palette.
        stale: True → muted Farben + "STALE"-Badge.
        output_path: Override für Tests.
    """
    out = output_path or _OUTPUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (T.LCD_SIZE, T.LCD_SIZE), theme.bg_color)
    is_idle = snapshot is None or not snapshot.is_active

    if is_idle:
        _render_idle(img, theme)
    else:
        assert snapshot is not None
        _render_active(img, snapshot, plan_limit, theme, stale=stale)

    img.save(out, format="PNG", optimize=True)
    log.debug("Frame gerendert: %s (stale=%s, idle=%s)", out.name, stale, is_idle)
    return out


def render_paused_frame(
    last_update: datetime | None,
    theme: ThemeConfig,
    *,
    output_path: Path | None = None,
) -> Path:
    """Rendert einen "PAUSED"-Frame für Graceful-Shutdown."""
    out = output_path or _OUTPUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (T.LCD_SIZE, T.LCD_SIZE), theme.bg_color)
    _render_paused(img, last_update, theme)
    img.save(out, format="PNG", optimize=True)
    log.debug("PAUSED-Frame gerendert: %s", out.name)
    return out
