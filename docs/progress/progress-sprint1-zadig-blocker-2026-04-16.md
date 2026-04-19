# Session-Fortschritt — 2026-04-16

## Thema

Sprint 1 Execution des Projekts `kraken-claude-monitor` (Claude-Quota auf Kraken-LCD). Code-Teil der ersten 6 Stories komplett implementiert. Aktuell blockiert auf Zadig-Treiber-Setup: nach libusb-win32-Install sieht weder liquidctl noch CAM den Kraken.

## Erledigt

1. **Deep Research abgeschlossen** — Pipeline ccusage + Pillow + liquidctl validiert, Report archiviert in vorheriger Konversation.
2. **3 Sprints geplant** (Commit `fd1fc75`):
   - `docs/VISION.md`, `docs/ROADMAP.md`
   - `docs/sprint-1/USER-STORIES.md` (detailliert), `FEATURE-ARCH.md`, `EXECUTE.md`
   - `docs/sprint-2/USER-STORIES.md`, `docs/sprint-3/USER-STORIES.md` (Roadmap-Level)
   - `CLAUDE.md`, `PROGRESS.md`
3. **Sprint 1 Code komplett geschrieben** (US-001, US-003-Code, US-004-Skript, US-005, US-006):
   - Python-Scaffolding: `pyproject.toml`, venv (Python 3.14.3)
   - Package `src/kraken_monitor/`: `__init__.py`, `__main__.py` (CLI: status / test-push / run / version), `config.py` (TOML-Loader + Dataclasses), `logging_setup.py`, `cam_check.py`, `kraken.py` (KrakenDevice-Wrapper)
   - `scripts/make_test_gif.py` (generiert PNG 640×640), `scripts/post_install.py` (DLL-Fix)
   - `config.default.toml`, `README.md`
   - Docs: `sprint-1/CAM-COEXISTENCE.md`, `sprint-1/ZADIG-SETUP.md`
4. **Install verifiziert:** `pip install -e ".[dev]"` erfolgreich, liquidctl 1.16.0, Pillow 12.2.0 installiert.
5. **Test-PNG generiert:** `frames/test.png` (640×640, 15 KB).
6. **Status-Read vom Kraken erfolgreich** (vor Zadig): `python -m kraken_monitor status` findet "NZXT Kraken 2023", liest Pump-Speed 3027 rpm, Temp 27.7°C — HID funktioniert out-of-the-box.

### Drei unerwartete Findings

1. **Research-Report war bei liquidctl-Issues invertiert:** Relevant ist Issue **#631** (nicht #757) — `gif`-Mode auf FW 2.X.Y nicht supported, nur `static`-Mode mit PNG. Code ist umgestellt (`push_frame()` erkennt Dateiendung automatisch, PNG → static, GIF → gif).
2. **Gerät ist "NZXT Kraken 2023" Standard**, nicht Elite — Display wahrscheinlich 240×240, nicht 640×640 wie in VISION/ROADMAP angenommen. Noch nicht visuell bestätigt.
3. **libusb-package 1.0.26.1 cp314-wheel liefert keine libusb-1.0.dll** — verursacht `NoBackendError`. Workaround in `scripts/post_install.py` (kopiert DLL aus alternativem `libusb`-Package rüber). Idempotent, Teil des Install-Flows.

## Offen / Naechste Schritte

### AKUT (User-Gate)

- **Zadig rückbauen:** User hat libusb-win32 via Zadig installiert. Zeigt sich im Gerätemanager als "libusb0" — das ist korrekt derselbe Treiber (libusb-win32 Projekt, libusb0.sys Kernel-Driver). ABER: danach sieht **weder CAM noch liquidctl** den Kraken. Wahrscheinlich Interface 0 (HID) statt Interface 1 (LCD) getroffen — oder Kraken 2023 Standard hat nur Single-Interface-Design.
- User-Aktion: Gerätemanager → `libusb-win32 devices` → NZXT Kraken → Rechtsklick Deinstallieren mit Häkchen bei "Treibersoftware entfernen" → Aktion → Nach geänderter Hardware suchen → CAM neu starten → `python -m kraken_monitor status`. **Wartet auf User-Feedback.**

### Nach Rückbau zu entscheiden

- **Recherche:** Hat Kraken 2023 Standard (≠ Elite) überhaupt ein separates LCD-Interface für Zadig? Oder ist LCD-Write bei diesem Modell generell mit CAM inkompatibel (Single-Interface)?
- **Möglicher Pivot:** WinUSB statt libusb-win32 (liquidctl-Docs empfehlen WinUSB teilweise). Oder: CAM-Web-Integration-SDK als Alternative wenn hardwareseitige Koexistenz unmöglich.
- **Sprint 1 Neuausrichtung möglich:** Wenn LCD-Write nicht ohne CAM-Aus geht, muss VISION "passiv parallel zu CAM" gekippt oder das Konzept ganz überdacht werden.

### Uncommittete Änderungen

Nichts ist seit Initial-Commit `fd1fc75` committed. Nach Zadig-Klärung: Story-für-Story committen (user-Memory: keine Auto-Commits).

## Geaenderte Dateien

| Datei | Status | Zweck |
|---|---|---|
| `CLAUDE.md` | M | Architektur-Regeln: #631 statt #757, Post-Install-DLL-Fix als Regel |
| `PROGRESS.md` | M | Sprint-1-Stand + 3 Findings dokumentiert |
| `README.md` | new | Install-Quickstart inkl. `post_install.py` |
| `pyproject.toml` | new | Dependencies, Ruff, Pytest-Config |
| `config.default.toml` | new | Monitor/Plan/Theme/OAuth Defaults |
| `src/kraken_monitor/__init__.py` | new | Package, Version |
| `src/kraken_monitor/__main__.py` | new | CLI mit Subcommands |
| `src/kraken_monitor/config.py` | new | TOML-Loader + Dataclasses + Merge + Validation |
| `src/kraken_monitor/logging_setup.py` | new | Logging-Format |
| `src/kraken_monitor/cam_check.py` | new | CAM-Prozess-Check + Warning |
| `src/kraken_monitor/kraken.py` | new | KrakenDevice Wrapper (Status, push_frame mit Auto-Format-Detection, set_brightness) |
| `scripts/make_test_gif.py` | new | 640×640 Test-PNG generator |
| `scripts/post_install.py` | new | libusb-DLL-Fix idempotent |
| `docs/sprint-1/CAM-COEXISTENCE.md` | new | User-Doku CAM LCD auf Off |
| `docs/sprint-1/ZADIG-SETUP.md` | new | User-Doku Zadig-Installation |
| `frames/test.png` | new | Generiertes 15 KB Test-Bild (gitignored) |

**Aktueller Commit-Head:** `fd1fc75` (nur Planung). Code-Stand ist uncommitted.

## Weiter machen mit

User-Feedback zu Zadig-Rückbau abwarten → dann entscheiden ob

1. Neuer Zadig-Versuch auf richtigem Interface
2. Pivot auf WinUSB
3. VISION-Rework (LCD-Write inkompatibel mit CAM)
