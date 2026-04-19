"""Unit-Tests für Frame-Renderer.

Rendert in tmp-Pfade — keine Seiteneffekte auf `frames/live.png`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from PIL import Image

from kraken_monitor.ccusage import QuotaSnapshot
from kraken_monitor.config import ThemeConfig
from kraken_monitor.renderer import format_time_remaining, render_frame, render_paused_frame
from kraken_monitor.theme import LCD_SIZE


@pytest.fixture
def theme():
    return ThemeConfig()


@pytest.fixture
def snapshot():
    return QuotaSnapshot(
        total_tokens=9500,
        burn_rate_tpm=1200.0,
        block_start=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        block_end=datetime(2026, 4, 19, 20, 0, tzinfo=UTC),
        time_remaining_sec=8100,
        is_active=True,
        fetched_at=datetime(2026, 4, 19, 17, 45, tzinfo=UTC),
    )


def test_render_active_snapshot_produces_640_png(tmp_path, theme, snapshot):
    out = tmp_path / "frame.png"
    result = render_frame(snapshot, plan_limit=19000, theme=theme, output_path=out)
    assert result == out
    assert out.is_file()
    with Image.open(out) as img:
        assert img.size == (LCD_SIZE, LCD_SIZE)
        assert img.mode == "RGB"


def test_render_idle_when_snapshot_none(tmp_path, theme):
    out = tmp_path / "idle.png"
    render_frame(None, plan_limit=19000, theme=theme, output_path=out)
    assert out.is_file()


def test_render_idle_when_not_active(tmp_path, theme, snapshot):
    inactive = QuotaSnapshot(
        total_tokens=snapshot.total_tokens,
        burn_rate_tpm=snapshot.burn_rate_tpm,
        block_start=snapshot.block_start,
        block_end=snapshot.block_end,
        time_remaining_sec=snapshot.time_remaining_sec,
        is_active=False,
        fetched_at=snapshot.fetched_at,
    )
    out = tmp_path / "inactive.png"
    render_frame(inactive, plan_limit=19000, theme=theme, output_path=out)
    assert out.is_file()


def test_render_stale_uses_muted_palette_not_orange(tmp_path, theme, snapshot):
    """Stale-Mode tauscht Claude-Orange-Ring gegen muted-color.

    Statt globalem Desaturate (alter Look) nutzt der neue Renderer explizite
    muted Farben für Ring + Text. Wir prüfen, dass die Primary-Farbe
    (Claude Orange) nicht im Bild auftaucht.
    """
    from PIL import ImageColor

    out = tmp_path / "stale.png"
    render_frame(snapshot, plan_limit=19000, theme=theme, stale=True, output_path=out)
    primary_rgb = ImageColor.getrgb(theme.primary_color)
    with Image.open(out) as img:
        colors = {p for p in img.getdata()}
    assert primary_rgb not in colors, "Stale-Frame darf keine Claude-Orange-Pixel enthalten"


def test_render_caps_pct_at_100(tmp_path, theme):
    """totalTokens > plan_limit → pct gecappt bei 100 (kein Ring-Overflow)."""
    over_budget = QuotaSnapshot(
        total_tokens=50_000,
        burn_rate_tpm=None,
        block_start=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        block_end=datetime(2026, 4, 19, 20, 0, tzinfo=UTC),
        time_remaining_sec=8100,
        is_active=True,
        fetched_at=datetime.now(UTC),
    )
    out = tmp_path / "over.png"
    render_frame(over_budget, plan_limit=19000, theme=theme, output_path=out)
    assert out.is_file()


def test_render_survives_zero_plan_limit(tmp_path, theme, snapshot):
    """plan_limit=0 darf nicht in ZeroDivisionError münden."""
    out = tmp_path / "zero.png"
    render_frame(snapshot, plan_limit=0, theme=theme, output_path=out)
    assert out.is_file()


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0m"),
        (30, "<1m"),
        (59, "<1m"),
        (60, "1m"),
        (180, "3m"),
        (3599, "59m"),
        (3600, "1h 0m"),
        (9480, "2h 38m"),
    ],
)
def test_format_time_remaining(seconds: int, expected: str) -> None:
    assert format_time_remaining(seconds) == expected


def test_format_time_remaining_clamps_negative() -> None:
    assert format_time_remaining(-120) == "0m"


def test_render_paused_frame_with_last_update(tmp_path, theme):
    out = tmp_path / "paused.png"
    last = datetime(2026, 4, 19, 17, 42, tzinfo=UTC)
    result = render_paused_frame(last, theme, output_path=out)
    assert result == out
    with Image.open(out) as img:
        assert img.size == (LCD_SIZE, LCD_SIZE)
        assert img.mode == "RGB"


def test_render_paused_frame_without_last_update(tmp_path, theme):
    out = tmp_path / "paused_never.png"
    render_paused_frame(None, theme, output_path=out)
    assert out.is_file()
