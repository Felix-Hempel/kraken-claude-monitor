"""Unit-Tests für ccusage-Parser. Subprocess wird nie wirklich aufgerufen."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from kraken_monitor.ccusage import CCUsageError, _parse_active_block, fetch_snapshot

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_parse_active_block_extracts_active_entry():
    snap = _parse_active_block(_load("ccusage_active.json"))
    assert snap is not None
    assert snap.is_active is True
    assert snap.total_tokens == 12000
    assert snap.burn_rate_tpm == pytest.approx(3700.5)
    assert snap.block_start == datetime(2026, 4, 19, 15, 0, tzinfo=UTC)
    assert snap.block_end == datetime(2026, 4, 19, 20, 0, tzinfo=UTC)


def test_parse_active_block_prefers_indicator_over_raw_burn_rate():
    """`tokensPerMinuteForIndicator` ist relevanter als `tokensPerMinute`
    (das durch Cache-Reads explodiert)."""
    snap = _parse_active_block(_load("ccusage_active.json"))
    assert snap is not None
    assert snap.burn_rate_tpm == pytest.approx(3700.5)


def test_parse_extracts_detected_limit_from_token_limit_status():
    """`--token-limit max` füllt `tokenLimitStatus.limit` — das ist der
    historische 5h-Block-Max als Plan-Proxy."""
    snap = _parse_active_block(_load("ccusage_active.json"))
    assert snap is not None
    assert snap.detected_limit == 342813511


def test_parse_detected_limit_is_none_when_tokenlimit_missing():
    """Fixture ohne tokenLimitStatus (frisches ccusage, kein --token-limit max)."""
    json_no_status = '{"blocks":[{"startTime":"2026-04-19T15:00:00.000Z","endTime":"2026-04-19T20:00:00.000Z","isActive":true,"isGap":false,"totalTokens":1000,"burnRate":null}]}'
    snap = _parse_active_block(json_no_status)
    assert snap is not None
    assert snap.detected_limit is None


def test_parse_no_active_block_returns_none():
    assert _parse_active_block(_load("ccusage_empty.json")) is None


def test_parse_ignores_gap_blocks():
    # Der einzige "is_active=True"-Block muss trotz Gap-Blöcken erkannt werden.
    snap = _parse_active_block(_load("ccusage_active.json"))
    assert snap is not None
    assert snap.is_active is True


def test_parse_raises_on_invalid_json():
    with pytest.raises(CCUsageError, match="unparsebar"):
        _parse_active_block("{ not valid json }")


def test_parse_raises_on_missing_blocks_field():
    with pytest.raises(CCUsageError, match="blocks"):
        _parse_active_block('{"foo": "bar"}')


def test_fetch_snapshot_propagates_subprocess_failure():
    """Wenn npx crasht, soll CCUsageError hochkommen — kein Silent-Return."""
    with patch("kraken_monitor.ccusage._run_ccusage") as run_mock:
        run_mock.side_effect = CCUsageError("npx nicht gefunden")
        with pytest.raises(CCUsageError):
            fetch_snapshot()
