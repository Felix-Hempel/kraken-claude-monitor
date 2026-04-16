# FEATURE-ARCH.md — Sprint 1: Foundation + Hardware-Path

## Scope

| Key | Wert |
|-----|------|
| **Projekt** | kraken-claude-monitor |
| **Typ** | CLI (Python) |
| **Ein-Satz** | Python-Gerüst + Hardware-Bridge zum Kraken-LCD |
| **Zielgruppe** | Felix (Solo) |
| **Kern-Constraint** | Windows 11 + libusb-win32 Treiber nötig |

### Goals

| # | Ziel | Metrik | Priorität |
|---|------|--------|-----------|
| G1 | Python-Package installierbar via `pip install -e .` | `python -m kraken_monitor` startet ohne Error | Must |
| G2 | liquidctl sieht Kraken | `liquidctl list` zeigt Device | Must |
| G3 | Test-GIF erscheint auf LCD | Visuell bestätigt | Must |
| G4 | Kraken-Wrapper kapselt Device-Handle | `KrakenDevice().push_frame()` funktioniert | Must |
| G5 | Config-System steht | `config.default.toml` wird geladen | Should |

### Non-Goals (explizit NICHT in Sprint 1)

- ccusage-Integration — Sprint 2
- Dynamisches Frame-Rendering — Sprint 2
- Autostart / Task Scheduler — Sprint 3
- OAuth-Endpoint — Sprint 3
- Tests (außer manual verify) — Sprint 2+

## Architecture Overview

```
┌──────────────────────────────────────────┐
│   kraken_monitor (Python Package)        │
│                                          │
│   ┌──────────────┐   ┌───────────────┐  │
│   │ __main__.py  │──▶│ config.py     │  │
│   │ (CLI entry)  │   │ (TOML loader) │  │
│   └──────────────┘   └───────────────┘  │
│          │                                │
│          ▼                                │
│   ┌──────────────┐   ┌───────────────┐  │
│   │ cam_check.py │   │ kraken.py     │  │
│   │ (process ck) │   │ (liquidctl    │  │
│   └──────────────┘   │  wrapper)     │  │
│                      └───────────────┘  │
└──────────────────────────────────────────┘
         │                     │
         ▼                     ▼
   ┌──────────┐         ┌─────────────┐
   │ tasklist │         │ liquidctl   │
   │ (subproc)│         │ (pip lib)   │
   └──────────┘         └─────────────┘
                              │
                              ▼ USB
                        ┌─────────────┐
                        │   Kraken    │
                        │   LCD       │
                        │  (640×640)  │
                        └─────────────┘
```

### Layers

| Layer | Verantwortung | Module |
|-------|--------------|--------|
| CLI | Entry-Point, Subcommands, Logging-Setup | `__main__.py`, `logging_setup.py` |
| Config | TOML-Loading, Defaults, Override-Merge | `config.py` |
| System | Prozess-Checks (CAM), Hardware-Status | `cam_check.py` |
| Device | liquidctl-Wrapper, Frame-Push, Brightness | `kraken.py` |

## Data Model

Nur zwei Shapes relevant in Sprint 1:

```python
# Config-Struktur (aus TOML geladen)
@dataclass
class MonitorConfig:
    poll_interval_sec: int = 10
    brightness_pct: int = 80
    log_level: str = "INFO"

@dataclass
class PlanConfig:
    type: str = "pro"              # "pro" | "max5" | "max20"
    session_token_limit: int = 19000

@dataclass
class ThemeConfig:
    bg_color: str = "#0D0A1E"
    primary_color: str = "#8B5CF6"
    text_color: str = "#FFFFFF"

@dataclass
class AppConfig:
    monitor: MonitorConfig
    plan: PlanConfig
    theme: ThemeConfig
    # oauth: OAuthConfig — ab Sprint 3
```

## CLI Design

```
python -m kraken_monitor                 # Startet Main-Loop (Sprint 2 onwards — in Sprint 1: zeigt nur Status)
python -m kraken_monitor test-push PATH  # Pusht beliebiges GIF aufs LCD
python -m kraken_monitor status          # Zeigt: CAM-Status, Kraken gefunden?, Config OK?
```

## Dependencies

| Dependency | Zweck | Version | Failure Mode |
|-----------|-------|---------|-------------|
| liquidctl | Kraken-USB-Kommunikation | ≥1.14 | `No supported devices found` — Zadig-Treiber fehlt |
| Pillow (PIL) | Test-GIF generieren + später Frames | ≥10.0 | ImportError — `pip install` fehlgeschlagen |
| tomllib | Config-Parsing | stdlib (3.11+) | — |
| (Zadig) | Einmaliges libusb-Driver-Install | 2.9+ | Manuelle Aktion, kein Runtime-Dep |

### Tech-Stack-Entscheidungen

| Entscheidung | Gewählt | Alternativen | Begründung |
|-------------|---------|-------------|------------|
| Package-Manager | pip + pyproject.toml | Poetry, Hatch | Weniger Tooling, `pip install -e .` reicht |
| Config-Format | TOML (tomllib) | YAML, JSON, ENV | 3.11-stdlib, kein extra Dep, strukturiert |
| Driver-Install | Zadig manuell | libusbK auto-install | Zadig ist Standard-Weg für liquidctl-User |
| liquidctl-Usage | Python-API direkt | Subprocess-Calls | Kein 200ms-Spawn pro Call, Handle-Reuse |

## Security & Constraints

### Security

- **CAM-Credentials:** Nicht relevant — CAM läuft unabhängig
- **Secrets:** In Sprint 1 keine. OAuth-Token erst Sprint 3, dann in `%USERPROFILE%\.claude\.credentials.json` (nicht committed)
- **USB-Zugriff:** libusb-win32 auf genau dem Kraken-Interface, keine Erhöhung der Rechte nötig

### Performance

- Main-Loop-Overhead Sprint 1: nicht relevant (keine Loop)
- `KrakenDevice.__init__` einmalig ~500ms (liquidctl-Device-Scan), dann 0ms pro Call
- `push_frame` Upload: 1–2s pro 640×640 GIF (USB-Bandbreite, nicht vermeidbar)

### Constraints

- **OS:** Windows 11 only — `tasklist.exe` CAM-Check wäre auf Linux anders
- **Python:** ≥ 3.11 wegen tomllib-stdlib
- **Hardware:** NUR Kraken Elite/Z-Serie — andere Modelle haben andere Interfaces/Firmware-Quirks

## Vision-Alignment

**Adressierte Vision-Stufe:** Stufe 1 — Hardware-Path

**Kern-Loop-Schritt:** Schritt 5–6 im Kern-Loop (`Pillow-Frame → liquidctl → Kraken-LCD`). Sprint 1 baut genau den rechten Teil der Pipeline, ohne Datenquelle.

**Nächste Iteration:** Sprint 2 verbindet Datenquelle (`ccusage`) und Renderer (Pillow-Frame mit Prozent-Ring) mit der in Sprint 1 gebauten Hardware-Bridge.

## Offene Risiken für Sprint 1

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Zadig installiert falschen Treiber (Interface 0 statt 1) — zerstört CAM-Funktion | Mittel | US-002 explizit "Interface 1" dokumentiert |
| liquidctl-Version zu alt für Kraken 2024 Elite | Niedrig | `liquidctl>=1.14` in pyproject pinnen |
| CAM startet sich selbst nach Reboot und bespielt LCD | Hoch | US-003 CAM-LCD manuell auf "Off" + Check-Skript warnt |
| Pillow-GIF zu groß (>4MB) — liquidctl weigert sich | Niedrig | Test-GIF klein halten, 1 Frame, Optimize-Flag bei save() |
