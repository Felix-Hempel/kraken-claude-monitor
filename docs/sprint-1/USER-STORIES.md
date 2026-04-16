# USER-STORIES.md — Sprint 1: Foundation + Hardware-Path

> Ziel: Ein Test-GIF erscheint auf dem Kraken-LCD. Python-Gerüst + libusb-Setup + Kraken-Wrapper stehen.
> Keine Claude-Daten in diesem Sprint — nur Infrastruktur.

## Phase 1: Scaffolding

### US-001: Python-Projekt scaffolden

**Context:** Leeres Projekt-Verzeichnis. Braucht ein minimales Python-Package mit `pyproject.toml`, venv, src-Layout, damit die nächsten Stories sauber Module anlegen können. Kein `setup.py`, kein Poetry — stdlib + `pip -e .` reicht.

**Input (Vorbedingungen):**
- Python 3.11+ ist installiert (`py -V` zeigt ≥ 3.11)
- Git ist installiert
- Arbeitsverzeichnis: `C:\Users\felix\Documents\IT\kraken-claude-monitor`

**Task:**
1. `py -3.11 -m venv .venv` ausführen
2. `pyproject.toml` anlegen mit `[project]`-Sektion:
   - name = `kraken-claude-monitor`
   - version = `0.1.0`
   - requires-python = `>=3.11`
   - dependencies = `["liquidctl>=1.14", "pillow>=10.0"]`
   - optional-dependencies.dev = `["pytest>=8.0", "ruff>=0.6"]`
3. `src/kraken_monitor/__init__.py` anlegen (leer)
4. `src/kraken_monitor/__main__.py` anlegen mit `print("kraken-claude-monitor v0.1.0")`
5. `[tool.setuptools.packages.find]` in pyproject auf `where = ["src"]` setzen
6. Venv aktivieren (`.venv\Scripts\activate` in cmd)
7. `pip install -e ".[dev]"` ausführen

**Output (erzeugte/geänderte Dateien):**
- `pyproject.toml` — Projekt-Metadaten + Dependencies
- `src/kraken_monitor/__init__.py` — Leeres Package
- `src/kraken_monitor/__main__.py` — Minimaler Entry-Point

**Verify:**
```powershell
.venv\Scripts\activate
python -m kraken_monitor
# Erwartet: "kraken-claude-monitor v0.1.0"
python -c "import liquidctl, PIL; print(liquidctl.__version__, PIL.__version__)"
# Erwartet: beide Versionen gedruckt
```

**Blocked-by:** —

---

### US-002: libusb-Treiber via Zadig + liquidctl-Install verifizieren

**Context:** Ohne libusb-Treiber sieht `liquidctl` den Kraken nicht — `liquidctl list` gibt "No supported devices found". Windows verwendet sonst den NZXT-HID-Treiber, den liquidctl nicht öffnen kann. Zadig installiert libusb-win32 genau für das Kraken-Interface, ohne CAM-Funktion zu zerstören (CAM nutzt HID-Interface 0, liquidctl nutzt Interface 1).

**Input (Vorbedingungen):**
- US-001 abgeschlossen (venv + liquidctl installiert)
- Zadig heruntergeladen von https://zadig.akeo.ie/ (Stand 2026: Version 2.9+)
- NZXT CAM **beendet** (sonst blockiert es das USB-Handle)
- Admin-Rechte für Treiber-Install

**Task:**
1. CAM komplett schließen (Task-Manager → "NZXT CAM" und "CAM.exe" beenden)
2. Zadig als Admin starten
3. Options → "List All Devices" aktivieren
4. In der Dropdown "NZXT Kraken..." auswählen — das Interface mit der höheren Interface-Nummer (meist Interface 1, USB ID 1e71:3008 für Elite)
5. Ziel-Treiber "libusb-win32" wählen
6. "Replace Driver" klicken
7. Gerätemanager öffnen, bestätigen dass unter "libusb-win32 devices" ein "NZXT Kraken..." Eintrag steht
8. `liquidctl list` ausführen
9. `liquidctl --match kraken initialize` ausführen (setzt Display initial auf Default)

**Output:**
- Treiber-Zustand auf Windows (kein Code-Artefakt)
- `docs/sprint-1/ZADIG-SETUP.md` — Kurze Doku mit Screenshots (oder Text-Step-Liste) wie es gemacht wurde, für Wiederholung nach Windows-Reset

**Verify:**
```powershell
liquidctl list
# Erwartet: Zeile wie "Device #0: NZXT Kraken Elite (2024)" oder ähnlich
liquidctl --match kraken status
# Erwartet: Temp, Pump-Speed etc. ohne Error
```

**Blocked-by:** US-001

---

### US-003: CAM-LCD-Screen deaktivieren (Doku + Check-Skript)

**Context:** CAM kann das LCD parallel bespielen und überschreibt unsere Frames. Lösung: In CAM unter "LCD" den Screen-Mode auf "None"/deaktiviert stellen. Kein Code kann das zuverlässig automatisieren (CAM hat keine CLI). Daher: Eine Dokumentations-Story + ein Python-Helper der beim Start warnt wenn CAM läuft.

**Input:**
- US-002 abgeschlossen
- CAM neu gestartet nach Treiber-Wechsel (sollte weiterhin Pumpen-Daten lesen, nur nicht mehr das LCD bespielen)

**Task:**
1. CAM öffnen → Kraken-Kachel → LCD-Einstellungen
2. Display-Mode auf "Off" / "Blank" setzen (nicht "GIF", nicht "CPU Temp")
3. Änderung speichern, CAM minimieren
4. `src/kraken_monitor/cam_check.py` anlegen mit Funktion `is_cam_running() -> bool` die via `subprocess` + `tasklist` nach "CAM.exe" schaut
5. Main-Entry (`__main__.py`) updaten: wenn CAM läuft → Warning loggen "CAM is running — stelle sicher dass LCD-Screen in CAM auf 'Off' steht"
6. `docs/sprint-1/CAM-COEXISTENCE.md` schreiben — 5-Zeilen-Doku was der User machen muss

**Output:**
- `src/kraken_monitor/cam_check.py` — Process-Check Helper
- `src/kraken_monitor/__main__.py` — um CAM-Warnung erweitert
- `docs/sprint-1/CAM-COEXISTENCE.md` — User-Doku

**Verify:**
```powershell
# CAM läuft
python -m kraken_monitor
# Erwartet: Warning-Log "CAM is running — ..."
# CAM beenden, erneut:
python -m kraken_monitor
# Erwartet: Keine Warning
```

**Blocked-by:** US-002

---

## Phase 2: Hardware-Bridge

### US-004: Test-GIF manuell aufs Display pushen

**Context:** Bevor wir Code schreiben der komplexe Frames rendert, erst beweisen dass der liquidctl-Push-Path funktioniert. Wenn das nicht geht, ist Sprint 2 blockiert. 1-Frame-GIF 640×640 mit einem einfachen Testbild.

**Input:**
- US-002, US-003 abgeschlossen
- Pillow installiert (via US-001)

**Task:**
1. `scripts/make_test_gif.py` anlegen: erstellt 640×640 GIF mit Text "KRAKEN TEST" auf Dark-Purple-Hintergrund
2. Script ausführen → erzeugt `frames/test.gif`
3. `liquidctl --match kraken set lcd screen gif frames/test.gif` ausführen
4. Bestätigen dass Test-GIF auf dem Kraken-LCD zu sehen ist
5. Foto machen zur Doku (optional in `docs/sprint-1/evidence/first-push.jpg`)
6. `liquidctl --match kraken set lcd screen brightness 80` testen (anpassen falls 80% zu hell/dunkel)

**Output:**
- `scripts/make_test_gif.py` — Test-GIF-Generator
- `frames/test.gif` — 640×640, 1 Frame, Dark-Purple mit "KRAKEN TEST"
- `frames/.gitkeep` — damit Ordner im Git bleibt

**Verify:**
```powershell
python scripts/make_test_gif.py
ls frames/test.gif
liquidctl --match kraken set lcd screen gif frames/test.gif
# Visuell prüfen: LCD zeigt "KRAKEN TEST" auf dunkelviolettem Hintergrund
```

**Blocked-by:** US-002, US-003

---

### US-005: Kraken-Device-Wrapper (`kraken.py`)

**Context:** `liquidctl` als Subprocess aufzurufen ist lahm (~200ms Spawn-Overhead pro Call). Besser: Python-API direkt nutzen. Wrapper-Modul kapselt Device-Init, Push-Frame, Brightness — eine Klasse, ein Handle, initialize einmal beim Start.

**Input:**
- US-004 abgeschlossen (manueller Push funktioniert)
- liquidctl-Python-API dokumentiert: `liquidctl.driver.find_liquidctl_devices()`

**Task:**
1. `src/kraken_monitor/kraken.py` anlegen
2. Klasse `KrakenDevice` mit:
   - `__init__(self)` — findet Device via `find_liquidctl_devices(match="kraken")`, connect + initialize
   - `push_frame(self, gif_path: Path) -> None` — ruft `device.set_screen("lcd", "gif", str(gif_path))` auf
   - `set_brightness(self, pct: int) -> None` — `device.set_screen("lcd", "brightness", str(pct))`
   - `close(self) -> None` — disconnect
   - Context-Manager-Support (`__enter__`, `__exit__`)
3. CLI-Subcommand in `__main__.py`: `python -m kraken_monitor test-push <gif-path>`
4. Fehler-Handling: wenn Device nicht gefunden → `RuntimeError("No Kraken found. Check Zadig driver + CAM is not running.")`

**Output:**
- `src/kraken_monitor/kraken.py` — KrakenDevice-Wrapper (~80 LOC)
- `src/kraken_monitor/__main__.py` — um `test-push` Subcommand erweitert

**Verify:**
```powershell
python -m kraken_monitor test-push frames/test.gif
# Erwartet: Exit 0, LCD zeigt Test-GIF (genauso wie US-004, aber via Python-API)
python -c "from kraken_monitor.kraken import KrakenDevice; k=KrakenDevice(); k.set_brightness(50); k.close()"
# Erwartet: LCD dimmt sichtbar ab
```

**Blocked-by:** US-004

---

### US-006: Config-System (TOML) + Logging

**Context:** Ab Sprint 2 brauchen wir Config-Werte: Poll-Interval, Plan-Typ (Pro/Max5/Max20), Brightness, Farb-Theme. Nicht hardcoden. Python 3.11 hat `tomllib` stdlib — kein extra Dependency. Logging mit `logging.basicConfig`, Level via Config.

**Input:**
- US-001 abgeschlossen

**Task:**
1. `config.default.toml` im Projekt-Root anlegen mit Sections:
   - `[monitor]` — `poll_interval_sec = 10`, `brightness_pct = 80`, `log_level = "INFO"`
   - `[plan]` — `type = "pro"` (values: "pro" / "max5" / "max20"), `session_token_limit = 19000` (override wenn plan-detection aus)
   - `[theme]` — `bg_color = "#0D0A1E"`, `primary_color = "#8B5CF6"`, `text_color = "#FFFFFF"`
   - `[oauth]` — `enabled = false` (für Sprint 3)
2. `src/kraken_monitor/config.py` anlegen mit `load_config(path: Path | None = None) -> dict`:
   - lädt `config.default.toml`, merged mit `config.local.toml` wenn vorhanden
   - validiert Typen (primitive Checks, kein Pydantic-Overkill)
3. `src/kraken_monitor/logging_setup.py` mit `setup_logging(level: str)` — Formatter mit Zeitstempel + Modul
4. `__main__.py` ruft setup_logging + load_config beim Start

**Output:**
- `config.default.toml` — Defaults, committed
- `src/kraken_monitor/config.py` — Config-Loader (~40 LOC)
- `src/kraken_monitor/logging_setup.py` — Logging-Config (~15 LOC)

**Verify:**
```powershell
python -m kraken_monitor
# Erwartet: INFO-Log beim Start "Loaded config: poll_interval=10s, plan=pro, ..."
# Mit eigener Override:
echo '[monitor]' > config.local.toml
echo 'poll_interval_sec = 5' >> config.local.toml
python -m kraken_monitor
# Erwartet: Log zeigt poll_interval=5
```

**Blocked-by:** US-001

---

## Dependency Graph

```
US-001 ─┬─▶ US-002 ─▶ US-003 ─▶ US-004 ─▶ US-005
        │
        └─▶ US-006
```

## Summary

| Phase | Stories | Parallel möglich |
|-------|---------|------------------|
| 1: Scaffolding | US-001, US-002, US-003, US-006 | US-001 → Rest; US-002/003 sequentiell wg. CAM; US-006 parallel zu US-002–005 |
| 2: Hardware-Bridge | US-004, US-005 | Sequentiell |

**Gesamtaufwand:** ~4h (US-002 Zadig-Setup ist Hands-On-Teil)

**Done wenn:** `python -m kraken_monitor test-push frames/test.gif` zeigt das Test-GIF auf dem LCD, und `python -m kraken_monitor` loggt Config + CAM-Check ohne Crash.
