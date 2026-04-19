"""CAM-Prozess-Check: warnt wenn NZXT CAM läuft (potentielle LCD-Kollision)."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)

CAM_PROCESS_NAMES = {"CAM.exe", "NZXT CAM.exe"}


def is_cam_running() -> bool:
    """Prüft via `tasklist` ob NZXT CAM läuft.

    Gibt False bei subprocess-Fehler (Logging als Warning) — wir blockieren
    das Tool nicht deswegen.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        log.warning("tasklist-Aufruf fehlgeschlagen: %s", e)
        return False

    for line in result.stdout.splitlines():
        # CSV-Format: "CAM.exe","1234","Console","1","25.000 K"
        first_field = line.split(",", 1)[0].strip('"') if line else ""
        if first_field in CAM_PROCESS_NAMES:
            return True
    return False


def warn_if_cam_running() -> None:
    """Log-Warning wenn CAM läuft. Kein Abbruch — Verantwortung beim User."""
    if is_cam_running():
        log.warning(
            "NZXT CAM laeuft. Stelle sicher, dass in CAM der Kraken-LCD-Screen "
            "auf 'Off' gestellt ist, sonst ueberschreibt CAM unsere Frames. "
            "Siehe docs/sprint-1/CAM-COEXISTENCE.md"
        )
