# PROGRESS.md — kraken-claude-monitor

## Compact-Recovery

> Kontext verloren? Lies diese 4 Dateien:
> 1. `CLAUDE.md` — Regeln, Stack, Patterns, Architektur
> 2. **Diese Datei** — Aktueller Status, was existiert, was fehlt
> 3. `docs/VISION.md` — Was das Tool soll und warum
> 4. `docs/ROADMAP.md` — 3-Sprint-Gesamtplan
>
> Dann: Aktuellen Sprint-Ordner öffnen, nächste offene Story identifizieren und abarbeiten.

**Projekt:** kraken-claude-monitor
**Aktueller Sprint:** Sprint 1 TODO
**Aktueller Status:** 0 Sprints done, 0/18 Stories
**Test-Count:** 0
**Stufe:** 0 — Planung abgeschlossen, Implementation steht an

---

## Sprint 1 — Foundation + Hardware-Path (2026-04-16)

| Story | Titel | Status |
|-------|-------|--------|
| US-001 | Python-Projekt scaffolden (pyproject, venv, src/) | TODO |
| US-002 | libusb-Treiber via Zadig + liquidctl-Install verifizieren | TODO |
| US-003 | CAM-LCD-Screen deaktivieren (Doku + Check-Skript) | TODO |
| US-004 | Test-GIF manuell aufs Display pushen | TODO |
| US-005 | Kraken-Device-Wrapper (`kraken.py`) | TODO |
| US-006 | Config-System (TOML) + Logging | TODO |

**Neue Dateien:** `pyproject.toml`, `src/kraken_monitor/{__init__,__main__,kraken,config}.py`, `config.default.toml`, `frames/test.gif`

---

## Sprint 2 — Daten-Pipeline + Renderer (geplant)

| Story | Titel | Status |
|-------|-------|--------|
| US-007 | ccusage-Wrapper (subprocess + JSON-Parse) | TODO |
| US-008 | Frame-Renderer (Pillow, 640×640 Dark-Purple-Theme) | TODO |
| US-009 | Theme-Konstanten (Farben, Fonts, Layout) | TODO |
| US-010 | Main-Loop mit graceful error handling | TODO |
| US-011 | Stale-Data-Indicator + Retry-Backoff | TODO |
| US-012 | Unit-Tests für Renderer + Parser | TODO |

---

## Sprint 3 — Autostart + Polish + OAuth (geplant)

| Story | Titel | Status |
|-------|-------|--------|
| US-013 | Windows Task Scheduler XML + Install-Skript | TODO |
| US-014 | Graceful Shutdown (SIGINT → "paused"-Frame) | TODO |
| US-015 | Plan-Detection aus ccusage (Pro/Max5/Max20) | TODO |
| US-016 | Optional: OAuth-Endpoint-Integration hinter Flag | TODO |
| US-017 | README + Troubleshooting-Guide | TODO |
| US-018 | End-to-End Smoke-Test nach Reboot | TODO |

---

## Aktueller Zustand (2026-04-16)

### Projekt-Metriken

| Metrik | Wert |
|--------|------|
| Source-Dateien | 0 |
| Test-Dateien | 0 |
| Tests | 0 |
| LOC (geschätzt final) | ~400 |

### Bekannte Lücken / Risiken

- **liquidctl FW-Bug #757** — auf Kraken 2023 Standard FW 2.x ist `static`-Modus kaputt. Mitigation: Immer 1-Frame-GIF pushen.
- **CAM-Coexistenz** — CAM überschreibt Frames, wenn auf demselben LCD ein Screen aktiv ist. Mitigation: User muss CAM-LCD-Screen auf "none" setzen. Wird in US-003 dokumentiert.
- **OAuth-Endpoint fragil** — `api.anthropic.com/api/oauth/usage` ist undokumentiert. Als optional behandeln (US-016), ccusage bleibt Primärquelle.
- **Upload-Rate** — ~1–2s pro Frame. Darunter ruckelt's. Default-Poll 10s.

### Umgebung

- OS: Windows 11 Home
- Kraken-Modell: NZXT Kraken Elite (640×640)
- NZXT CAM: muss installiert sein (für Pumpensteuerung), aber LCD-Screen leer
- Node.js: für `npx ccusage` benötigt
