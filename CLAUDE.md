# CLAUDE.md — kraken-claude-monitor

## Projekt: kraken-claude-monitor

Persönliches Tool. Zeigt auf dem NZXT Kraken 2023 LCD (physisch 640×640, **Framebuffer 240×240** — Firmware skaliert intern) live den Claude-Code-Quota-Stand an. Hardware-PID: `1E71:300E`, Firmware 2.0.0.

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
| Display-Lib | liquidctl (pip) — **benötigt Runtime-Patch**, siehe `docs/sprint-1/WINUSBCDC-PATCH.md` |
| USB-Driver | MI_00 WinUSB (Bulk/Display) + MI_01 HidUsb (HID-Steuerung) — **keine Zadig-Installation nötig**, siehe `docs/sprint-1/ZADIG-SETUP.md` |
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
2. **Static-Mode, nicht GIF (auf FW 2.X.Y)** — liquidctl Issue #631: `gif`-Mode ist auf Kraken 2023 FW 2.X nicht unterstützt. Für unsere Poll-basierte Anzeige reicht `static` mit PNG pro Poll. `push_frame()` erkennt Dateiendung automatisch.
3. **Treiber-Layout für PID 0x300E (FW 2.X.Y)** — MI_00 muss WinUSB haben (Bulk/Display), MI_01 muss HidUsb haben (HID-Steuerung). Bei Kraken 2023 sind die Interface-Rollen umgekehrt zur älteren Kraken X3/Z3 (dort ist MI_01 der Bulk-Kanal). Siehe `docs/sprint-1/ZADIG-SETUP.md`.
4. **liquidctl + winusbcdc Runtime-Patch** — `winusbcdc` hat einen hardcoded WinUSB-Interface-GUID (`dee824ef-…`), die Kraken 2023 meldet aber per MS-OS-Descriptor einen Custom-GUID (`300e300d-7EE7-1125-0724-101503010819`). Ausserdem: `list_usb_devices()` ohne vid/pid-Filter liefert aktuell leere Liste, aber liquidctl ruft so auf. Zwei-Zeilen-Monkeypatch in `kraken_monitor.kraken` fixt beides. Siehe `docs/sprint-1/WINUSBCDC-PATCH.md`.
5. **LCD-Framebuffer ist 240×240, nicht 640×640** — Panel ist physisch 640, aber Firmware erwartet 240er-Frames und skaliert intern. `liquidctl` hat das in `_MATCHES` für PID 0x300E korrekt (`lcd_resolution: (240, 240)`). Bei 640er-Frames wird bei uniformen Farben korrekt angezeigt, aber Muster/Text werden verzerrt.
6. **FW2 static-Push doppelt senden** — liquidctl `_send_2023_data_fw2` schickt das Bild zweimal hintereinander. Einmal reicht nicht für den Framebuffer-Swap. Der reguläre FW1-Pfad (`_send_data` mit Bucket-Setup) funktioniert auf FW 2.0.0 nicht — Bucket-Commands werden nicht beantwortet.
7. **Post-Install-DLL-Fix nötig (Python 3.14)** — `libusb-package` 1.0.26.1 cp314-wheel hat die libusb-1.0.dll nicht gebundled. `python scripts/post_install.py` nach jedem fresh install ausführen.
8. **CAM muss LCD nicht bespielen** — User-Verantwortung, Script bricht sonst mit Error ab (kein Auto-Kill).
9. **ccusage Fallback-First** — OAuth-Endpoint nur optional hinter Config-Flag.
10. **Frames in `frames/` + gitignored** — Nur Produktions-Frame schreiben, nicht Historie sammeln.
11. **Keine Secrets im Code** — `.credentials.json` (OAuth-Token) niemals committen.

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
| 1 | Foundation + Hardware-Path | DONE (2026-04-19) |
| 2 | Daten-Pipeline + Renderer | DONE (2026-04-19) |
| 3 | Autostart + Polish | Code DONE, User-Gate US-018 offen (2026-04-19) |

## Wichtige Links

- liquidctl Kraken Guide: https://github.com/liquidctl/liquidctl/blob/main/docs/kraken-x3-z3-guide.md
- liquidctl Issue #757 (static-Bug): https://github.com/liquidctl/liquidctl/issues/757
- Zadig (libusb-Treiber): https://zadig.akeo.ie/
- ccusage: https://ccusage.com/guide/json-output
- Pillow-Docs: https://pillow.readthedocs.io/
