# CLAUDE.md — kraken-claude-monitor

## Projekt: kraken-claude-monitor

Persönliches Tool. Zeigt auf dem NZXT Kraken Elite LCD (640×640) live den Claude-Code-Quota-Stand an.

## Session-Start (PFLICHT)

1. Diese Datei lesen
2. `PROGRESS.md` lesen — aktueller Sprint-Stand
3. `docs/VISION.md` lesen — Warum das Ding existiert, was in-scope ist
4. `docs/ROADMAP.md` — 3-Sprint-Plan
5. Aktuellen Sprint-Ordner lesen (`docs/sprint-N/`)

## Tech Stack

| Key | Wert |
|-----|------|
| Language | Python 3.11+ |
| OS | Windows 11 |
| Display-Lib | liquidctl (pip) |
| USB-Driver | libusb-win32 via Zadig |
| Data Source | ccusage (npx @latest) |
| Rendering | Pillow (PIL) |
| Config | TOML (stdlib tomllib) |
| Autostart | Windows Task Scheduler |

## Befehle

| Zweck | Befehl |
|-------|--------|
| Venv erstellen | `py -3.11 -m venv .venv` |
| Venv aktivieren | `.venv\Scripts\activate` (cmd) / `.venv/Scripts/Activate.ps1` (PS) |
| Install | `pip install -e .` |
| Run (dev) | `python -m kraken_monitor` |
| Test Hardware | `liquidctl --match kraken initialize` |
| Manueller Push | `liquidctl --match kraken set lcd screen gif frames/test.gif` |
| Test | `pytest` |
| Lint | `ruff check src/ tests/` |
| Format | `ruff format src/ tests/` |

## Architektur-Regeln

1. **Keine sekündlichen Updates** — liquidctl-Upload dauert 1–2s, Default-Poll = 10s.
2. **Immer GIF, nie static** — liquidctl Issue #757: static-Modus auf 2023 FW broken.
3. **CAM muss LCD nicht bespielen** — User-Verantwortung, Script bricht sonst mit Error ab (kein Auto-Kill).
4. **ccusage Fallback-First** — OAuth-Endpoint nur optional hinter Config-Flag.
5. **Frames in `frames/` + gitignored** — Nur Produktions-Frame schreiben, nicht Historie sammeln.
6. **Keine Secrets im Code** — `.credentials.json` (OAuth-Token) niemals committen.

## Anti-Patterns

- Nicht bei jedem Frame `liquidctl list` aufrufen (100ms Overhead) — Handle cachen.
- Kein sync HTTP im Main-Loop ohne Timeout — hängt sonst beim OAuth-Endpoint.
- Kein `shell=True` mit user-input-Strings (bei uns nicht relevant, aber Grundsatz).
- Kein Retry-without-Backoff bei LCD-Write-Fail — sonst USB-Spam.

## Naming

- Modulnamen: snake_case (`kraken_monitor`, `frame_renderer`)
- Klassen: PascalCase (`KrakenDevice`, `QuotaSnapshot`)
- Konstanten: UPPER_SNAKE (`POLL_INTERVAL_SEC`, `LCD_SIZE`)

## Sprint-Abschluss

Kein AKARA-Workflow. Lokal committen, pushen wenn Remote existiert. PROGRESS.md updaten.

## Sprint-Tabelle

| Sprint | Name | Status |
|--------|------|--------|
| 1 | Foundation + Hardware-Path | TODO |
| 2 | Daten-Pipeline + Renderer | TODO |
| 3 | Autostart + Polish + OAuth | TODO |

## Wichtige Links

- liquidctl Kraken Guide: https://github.com/liquidctl/liquidctl/blob/main/docs/kraken-x3-z3-guide.md
- liquidctl Issue #757 (static-Bug): https://github.com/liquidctl/liquidctl/issues/757
- Zadig (libusb-Treiber): https://zadig.akeo.ie/
- ccusage: https://ccusage.com/guide/json-output
- Pillow-Docs: https://pillow.readthedocs.io/
