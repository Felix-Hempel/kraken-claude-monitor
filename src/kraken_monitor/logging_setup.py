"""Logging-Setup.

Schreibt Logs nach stdout (sichtbar bei `python -m ...` im Terminal) UND in
eine Rotating-Logdatei in `%USERPROFILE%\\kraken-claude-monitor.log`. Die
Datei ist wichtig für den Task-Scheduler-Fall, wo pythonw.exe keine
Konsole hat und stdout ins Nichts geht.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FILE = Path.home() / "kraken-claude-monitor.log"
_LOG_MAX_BYTES = 1_000_000  # 1 MB → reicht für ~2 Wochen INFO-Logs
_LOG_BACKUP_COUNT = 3


def setup_logging(level: str = "INFO") -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Vorhandene Handler entfernen (sonst duplizierte Logs in Test-Runs)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    try:
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as e:
        # Falls Home-Verzeichnis nicht schreibbar: nur stdout — kein Crash.
        root.warning("Log-Datei %s nicht erreichbar: %s — nur stdout", _LOG_FILE, e)

    return logging.getLogger("kraken_monitor")
