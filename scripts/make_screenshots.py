"""Erzeugt Demo-Frames für README + GitHub-Screenshots.

Schreibt nach `docs/screenshots/`. Re-run wenn sich Theme oder Renderer
ändern, damit das README-Bild aktuell bleibt.

Usage:
    python scripts/make_screenshots.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from kraken_monitor.ccusage import QuotaSnapshot
from kraken_monitor.config import ThemeConfig
from kraken_monitor.renderer import render_frame, render_paused_frame

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
PLAN_LIMIT = 850_000_000  # match README example


def _snap(pct: float, t_remaining_min: int, now: datetime) -> QuotaSnapshot:
    return QuotaSnapshot(
        total_tokens=int(pct * PLAN_LIMIT),
        burn_rate_tpm=2500.0,
        block_start=now - timedelta(minutes=300 - t_remaining_min),
        block_end=now + timedelta(minutes=t_remaining_min),
        time_remaining_sec=t_remaining_min * 60,
        is_active=True,
        fetched_at=now,
        detected_limit=PLAN_LIMIT,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    theme = ThemeConfig()
    now = datetime.now(UTC)

    def render(filename: str, fn) -> None:  # noqa: ANN001
        path = OUT / filename
        fn(path)
        print(f"[OK] {path.relative_to(Path.cwd())}")

    render(
        "01-active.png",
        lambda p: render_frame(_snap(0.26, 158, now), PLAN_LIMIT, theme, output_path=p),
    )
    render(
        "02-over.png",
        lambda p: render_frame(_snap(1.58, 64, now), PLAN_LIMIT, theme, output_path=p),
    )
    render("03-idle.png", lambda p: render_frame(None, PLAN_LIMIT, theme, output_path=p))
    render(
        "04-paused.png",
        lambda p: render_paused_frame(now - timedelta(minutes=12), theme, output_path=p),
    )
    render(
        "05-stale.png",
        lambda p: render_frame(_snap(0.26, 158, now), PLAN_LIMIT, theme, stale=True, output_path=p),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
