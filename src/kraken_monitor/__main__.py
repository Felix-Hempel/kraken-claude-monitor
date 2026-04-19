"""CLI-Entry: `python -m kraken_monitor [status|test-push PATH|run]`.

Sprint 1: nur `status`, `test-push`, `version`. `run` kommt in Sprint 2.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .cam_check import warn_if_cam_running
from .config import ConfigError, load_config
from .kraken import KrakenDevice, KrakenError, KrakenNotFoundError
from .logging_setup import setup_logging
from .loop import run_loop

log = logging.getLogger(__name__)


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"kraken-claude-monitor v{__version__}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    """Zeigt: Config OK?, CAM laeuft?, Kraken gefunden?."""
    print(f"kraken-claude-monitor v{__version__}\n")

    # Config
    try:
        config = load_config()
        print("[OK]   Config geladen")
        print(
            f"       poll={config.monitor.poll_interval_sec}s, "
            f"plan={config.plan.type}, brightness={config.monitor.brightness_pct}%"
        )
    except ConfigError as e:
        print(f"[FAIL] Config: {e}")
        return 1

    # CAM
    warn_if_cam_running()
    from .cam_check import is_cam_running

    print(f"[INFO] CAM laeuft: {is_cam_running()}")

    # Kraken
    try:
        with KrakenDevice() as kraken:
            print(f"[OK]   Kraken gefunden: {kraken.description}")
            status = kraken.get_status()
            if status:
                print("       Status:")
                for key, value, unit in status[:5]:  # nur Top 5 zur Uebersicht
                    print(f"         {key}: {value} {unit}".rstrip())
    except KrakenNotFoundError as e:
        print(f"[FAIL] Kraken: {e}")
        return 2
    except KrakenError as e:
        print(f"[FAIL] Kraken: {e}")
        return 2

    return 0


def cmd_test_push(args: argparse.Namespace) -> int:
    path = Path(args.frame_path)
    try:
        config = load_config()
        with KrakenDevice() as kraken:
            kraken.set_brightness(config.monitor.brightness_pct)
            kraken.push_frame(path)
            log.info("Testbild gepusht: %s", path)
    except (ConfigError, KrakenError, FileNotFoundError, ValueError) as e:
        log.error("Fehler: %s", e)
        return 1
    return 0


def cmd_run(_args: argparse.Namespace) -> int:
    try:
        config = load_config()
    except ConfigError as e:
        log.error("Config: %s", e)
        return 1
    return run_loop(config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kraken-claude-monitor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Zeigt Config, CAM- und Kraken-Status")

    p_push = sub.add_parser("test-push", help="Pusht ein Bild aufs LCD (PNG/JPG/BMP)")
    p_push.add_argument(
        "frame_path",
        help="Pfad zum Bild. Wird von liquidctl auf 240x240 (Framebuffer-Auflösung) skaliert.",
    )

    sub.add_parser("run", help="Startet den Main-Loop (Sprint 2+)")

    sub.add_parser("version", help="Zeigt Version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Logging so frueh wie moeglich — aber vor Config-Load mit Default-Level
    try:
        config = load_config()
        setup_logging(config.monitor.log_level)
    except ConfigError:
        setup_logging("INFO")

    handlers = {
        "status": cmd_status,
        "test-push": cmd_test_push,
        "run": cmd_run,
        "version": cmd_version,
    }
    # Kein Subcommand → Main-Loop starten (häufigster Use-Case).
    command = args.command or "run"
    handler = handlers.get(command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
