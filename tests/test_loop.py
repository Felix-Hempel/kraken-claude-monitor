"""Unit-Tests für Loop-interne Helper (Plan-Limit-Resolution)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from kraken_monitor.ccusage import QuotaSnapshot
from kraken_monitor.config import AppConfig, PlanConfig
from kraken_monitor.loop import _resolve_plan_limit


@pytest.fixture
def snapshot():
    return QuotaSnapshot(
        total_tokens=10_000,
        burn_rate_tpm=1200.0,
        block_start=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        block_end=datetime(2026, 4, 19, 20, 0, tzinfo=UTC),
        time_remaining_sec=8100,
        is_active=True,
        fetched_at=datetime(2026, 4, 19, 17, 45, tzinfo=UTC),
        detected_limit=5_000_000,
    )


def test_plan_auto_uses_detected_limit(snapshot):
    config = AppConfig(plan=PlanConfig(type="auto", session_token_limit=19000))
    assert _resolve_plan_limit(config, snapshot) == 5_000_000


def test_plan_non_auto_ignores_detected_limit(snapshot):
    config = AppConfig(plan=PlanConfig(type="pro", session_token_limit=19000))
    assert _resolve_plan_limit(config, snapshot) == 19000


def test_plan_auto_fallback_when_detected_missing(snapshot):
    snap_no_detect = replace(snapshot, detected_limit=None)
    config = AppConfig(plan=PlanConfig(type="auto", session_token_limit=19000))
    assert _resolve_plan_limit(config, snap_no_detect) == 19000


def test_plan_auto_fallback_when_snapshot_none():
    config = AppConfig(plan=PlanConfig(type="auto", session_token_limit=19000))
    assert _resolve_plan_limit(config, None) == 19000
