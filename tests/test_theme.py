"""Unit-Tests für Theme-Helper."""

from __future__ import annotations

import pytest

from kraken_monitor.config import ThemeConfig
from kraken_monitor.theme import FontNotFoundError, color_for_pct, load_font


@pytest.fixture
def theme():
    return ThemeConfig()


def test_color_for_pct_orange_below_100(theme):
    """Standard-Anzeige ist Claude Orange auf der ganzen 0-99% Range."""
    for pct in (0, 25, 50, 67, 85, 99.9):
        assert color_for_pct(pct, theme) == theme.primary_color


def test_color_for_pct_danger_at_100_and_above(theme):
    """Erst bei ≥100% (OVER) wechselt's auf danger."""
    assert color_for_pct(100, theme) == theme.danger_color
    assert color_for_pct(150, theme) == theme.danger_color


def test_load_font_returns_usable_font():
    font = load_font(24)
    # Darf nicht crashen + size sollte mindestens gesetzt sein.
    assert font is not None
    # PIL-Fonts haben `.size` als Attribute.
    assert getattr(font, "size", None) == 24


def test_load_font_supports_multiple_weights():
    """Black/Bold/Semibold/Regular sollen alle ohne Crash laden."""
    for weight in ("black", "bold", "semibold", "regular"):
        font = load_font(20, weight=weight)
        assert font is not None


def test_load_font_raises_when_no_font_available(monkeypatch):
    """Wenn die Fallback-Chain leer ist → FontNotFoundError."""
    import kraken_monitor.theme as theme_module

    monkeypatch.setattr(
        theme_module,
        "_FONT_CHAINS",
        {
            "bold": ["nonexistent-font-xyz.ttf"],
            "regular": ["nonexistent-font-xyz.ttf"],
        },
    )
    with pytest.raises(FontNotFoundError):
        load_font(12, weight="bold")
