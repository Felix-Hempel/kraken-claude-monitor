"""ccusage-Wrapper: ruft `npx ccusage blocks --json` und parst den aktiven 5h-Block."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime

log = logging.getLogger(__name__)

# `--token-limit max` aktiviert `tokenLimitStatus.limit` im JSON-Output:
# ccusage berechnet daraus aus der Historie das maximal jemals erreichte
# 5h-Block-Limit — ein pragmatischer Proxy für den tatsächlichen Plan-Cap.
# Genauer als hardcoded "Pro=19k"/"Max20=220k"-Schätzungen.
_CCUSAGE_CMD = ["npx", "-y", "ccusage@latest", "blocks", "--json", "--token-limit", "max"]
# 30s toleriert den Erst-Call mit npm-Download (bis zu ~60s möglich, aber
# längere Waits würden den Loop blockieren). Spätere Calls laufen aus
# dem npm-Cache und sind < 2s.
_TIMEOUT_SEC = 30


class CCUsageError(RuntimeError):
    """Fehler beim Aufruf oder Parsen von ccusage."""


@dataclass(frozen=True)
class QuotaSnapshot:
    """Ein ccusage-Snapshot: aktueller 5h-Block + Zeitpunkt des Fetch.

    Felder mit `None`-Semantik:
      - `burn_rate_tpm` = None: noch kein Burn-Rate (frischer Block oder Idle)
      - `detected_limit` = None: ccusage konnte kein Limit aus der Historie ableiten
      - `is_active` = False: kein aktiver Block — Renderer zeigt IDLE
    """

    total_tokens: int
    burn_rate_tpm: float | None  # tokensPerMinuteForIndicator
    block_start: datetime
    block_end: datetime
    time_remaining_sec: int
    is_active: bool
    fetched_at: datetime
    # aus tokenLimitStatus.limit (ccusage --token-limit max) — default None
    # für Test-Fixtures und Backward-Compat, Parser setzt den echten Wert.
    detected_limit: int | None = None


def _run_ccusage() -> str:
    try:
        result = subprocess.run(
            _CCUSAGE_CMD,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SEC,
            check=True,
            shell=True,  # `npx` auf Windows ist eine .cmd-Datei
        )
    except subprocess.TimeoutExpired as e:
        raise CCUsageError(f"ccusage-Timeout nach {_TIMEOUT_SEC}s") from e
    except subprocess.CalledProcessError as e:
        raise CCUsageError(f"ccusage-Exit {e.returncode}: {e.stderr.strip()}") from e
    except FileNotFoundError as e:
        raise CCUsageError("npx nicht gefunden — Node.js installiert?") from e

    return result.stdout


def _parse_active_block(stdout: str) -> QuotaSnapshot | None:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CCUsageError(f"ccusage-JSON unparsebar: {e}") from e

    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        raise CCUsageError("ccusage-Output ohne 'blocks'-Array")

    now = datetime.now(UTC)
    active = [b for b in blocks if b.get("isActive") and not b.get("isGap")]
    if not active:
        return None

    block = active[0]
    try:
        block_start = datetime.fromisoformat(block["startTime"].replace("Z", "+00:00"))
        block_end = datetime.fromisoformat(block["endTime"].replace("Z", "+00:00"))
    except (KeyError, ValueError) as e:
        raise CCUsageError(f"ccusage-Block hat unbrauchbare Zeitstempel: {e}") from e

    burn = block.get("burnRate")
    burn_tpm = None
    if isinstance(burn, dict):
        # tokensPerMinuteForIndicator = nur input+output ohne Cache, relevanter als
        # die Raw-tokensPerMinute (die explodiert durch Cache-Reads).
        burn_tpm = burn.get("tokensPerMinuteForIndicator") or burn.get("tokensPerMinute")
        if burn_tpm is not None:
            burn_tpm = float(burn_tpm)

    time_remaining_sec = max(0, int((block_end - now).total_seconds()))

    detected_limit = None
    token_limit_status = block.get("tokenLimitStatus")
    if isinstance(token_limit_status, dict):
        raw_limit = token_limit_status.get("limit")
        if isinstance(raw_limit, int | float) and raw_limit > 0:
            detected_limit = int(raw_limit)

    return QuotaSnapshot(
        total_tokens=int(block.get("totalTokens", 0)),
        burn_rate_tpm=burn_tpm,
        block_start=block_start,
        block_end=block_end,
        time_remaining_sec=time_remaining_sec,
        is_active=True,
        fetched_at=now,
        detected_limit=detected_limit,
    )


def fetch_snapshot() -> QuotaSnapshot | None:
    """Holt den aktuellen aktiven 5h-Block. None wenn kein aktiver Block.

    Raises:
        CCUsageError: subprocess-Fehler, Timeout oder unparsebares JSON.
    """
    stdout = _run_ccusage()
    return _parse_active_block(stdout)
