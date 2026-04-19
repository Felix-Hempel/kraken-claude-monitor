"""Main-Loop: alle `poll_interval_sec` → ccusage → render → push → sleep.

Keept running bis Ctrl+C. Bei 3+ ccusage-Fehlern in Folge: Stale-Frame + Backoff.
Bei Shutdown (KeyboardInterrupt, CTRL_BREAK von schtasks /end): PAUSED-Frame
aufs LCD pushen, damit sichtbar ist, dass Monitor gestoppt wurde.
"""

from __future__ import annotations

import logging
import signal
import time

from .cam_check import warn_if_cam_running
from .ccusage import CCUsageError, QuotaSnapshot, fetch_snapshot
from .config import AppConfig
from .kraken import KrakenDevice, KrakenError
from .renderer import render_frame, render_paused_frame

log = logging.getLogger(__name__)

_STALE_AFTER_FAILURES = 3
_STALE_BACKOFF_SEC = 30


def _install_break_handler() -> None:
    """SIGBREAK (Ctrl+Break) auf Windows in KeyboardInterrupt umwandeln.

    SIGINT (Ctrl+C) triggert KeyboardInterrupt out-of-the-box. SIGBREAK tut
    das nicht — Task-Scheduler schickt aber CTRL_BREAK_EVENT bei `schtasks /end`.
    Ohne Handler terminiert der Prozess dann ohne den finally-Block auszuführen.
    """
    if hasattr(signal, "SIGBREAK"):

        def _raise_kbinterrupt(_signum, _frame):
            raise KeyboardInterrupt("SIGBREAK")

        signal.signal(signal.SIGBREAK, _raise_kbinterrupt)


def _resolve_plan_limit(config: AppConfig, snap: QuotaSnapshot | None) -> int:
    """Wählt das effektive Plan-Limit.

    `config.plan.type == "auto"` + ccusage liefert `detected_limit` → dieses nutzen.
    Sonst: `config.plan.session_token_limit` aus Config.
    """
    if config.plan.type == "auto" and snap is not None and snap.detected_limit:
        return snap.detected_limit
    return config.plan.session_token_limit


def _try_fetch(counter: int) -> tuple[QuotaSnapshot | None, int, bool]:
    """Fetcht Snapshot + managed Fehlerzähler + Stale-Flag.

    Returns:
        (snapshot-or-None, new-failure-counter, stale)
    """
    try:
        snap = fetch_snapshot()
    except CCUsageError as e:
        counter += 1
        stale = counter >= _STALE_AFTER_FAILURES
        log.warning("ccusage fehlgeschlagen (#%d): %s", counter, e)
        return None, counter, stale
    return snap, 0, False


def run_loop(config: AppConfig) -> int:
    """Startet den Main-Loop. Returns 0 bei sauberem Shutdown, 2 bei Hard-Fail."""
    _install_break_handler()
    warn_if_cam_running()

    try:
        kraken = KrakenDevice()
        kraken.connect()
    except KrakenError as e:
        log.error("Kraken-Connect fehlgeschlagen: %s", e)
        return 2

    # Vor dem try-Block initialisieren, damit `finally` auf jeden Fall darauf
    # zugreifen kann (auch wenn `set_brightness` vor der ersten Iteration wirft).
    last_snapshot: QuotaSnapshot | None = None
    failures = 0

    try:
        kraken.set_brightness(config.monitor.brightness_pct)
        log.info(
            "Loop gestartet — poll=%ds, plan=%s, limit=%s tokens",
            config.monitor.poll_interval_sec,
            config.plan.type,
            "auto" if config.plan.type == "auto" else config.plan.session_token_limit,
        )

        while True:
            snap, failures, stale_from_fail = _try_fetch(failures)
            # Drei Zustände unterscheiden, sonst zeigt das LCD nach Block-Ende
            # weiter den alten Prozentstand statt auf IDLE zu springen:
            #   - fetch success + snap != None → aktualisieren
            #   - fetch failed (stale_from_fail) → letztes Snapshot mit Stale-Badge
            #   - fetch success + snap == None (keine active session) → IDLE
            if snap is not None:
                last_snapshot = snap
                effective = snap
            elif stale_from_fail:
                effective = last_snapshot
            else:
                effective = None

            try:
                effective_limit = _resolve_plan_limit(config, effective)
                frame_path = render_frame(
                    effective,
                    effective_limit,
                    config.theme,
                    stale=stale_from_fail,
                )
                kraken.push_frame(frame_path)
                if snap is not None:
                    log.info(
                        "Frame gepusht — %d tokens, %ds bis Reset",
                        snap.total_tokens,
                        snap.time_remaining_sec,
                    )
                else:
                    log.debug(
                        "Frame gepusht (stale=%s, idle=%s)", stale_from_fail, effective is None
                    )
            except KrakenError as e:
                log.error("LCD-Push fehlgeschlagen: %s — reconnect-Versuch", e)
                kraken.close()
                try:
                    kraken.connect()
                    kraken.set_brightness(config.monitor.brightness_pct)
                except KrakenError as reconnect_err:
                    log.error("Reconnect gescheitert: %s — Loop stoppt", reconnect_err)
                    return 2

            sleep_sec = _STALE_BACKOFF_SEC if stale_from_fail else config.monitor.poll_interval_sec
            time.sleep(sleep_sec)
    except KeyboardInterrupt:
        log.info("Shutdown-Signal erhalten — stoppe Loop")
        return 0
    finally:
        _push_paused_frame(kraken, config, last_snapshot)
        kraken.close()


def _push_paused_frame(
    kraken: KrakenDevice, config: AppConfig, last_snapshot: QuotaSnapshot | None
) -> None:
    """Rendert + pusht PAUSED-Frame. Schluckt alle Fehler — Shutdown darf nicht crashen."""
    try:
        path = render_paused_frame(
            last_snapshot.fetched_at if last_snapshot else None,
            config.theme,
        )
        kraken.push_frame(path)
        log.info("PAUSED-Frame gepusht")
    except Exception as e:  # noqa: BLE001 — best-effort Shutdown
        log.warning("PAUSED-Frame konnte nicht gepusht werden: %s", e)
