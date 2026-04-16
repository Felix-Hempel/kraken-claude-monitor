# Sprint 1 — kraken-claude-monitor

> Übergabe-Prompt für Implementierung nach `/clear`.
> Referenzieren mit: `@docs/sprint-1/EXECUTE.md`

**Pfad:** `C:\Users\felix\Documents\IT\kraken-claude-monitor`
**Sprint:** 1 — Foundation + Hardware-Path
**Erstellt:** 2026-04-16
**Build-Check:** `python -m kraken_monitor --version`
**Branch-Konvention:** lokal auf `main` (keine Feature-Branches für Solo-Projekt nötig)

## Sprint-Docs

- Stories: `docs/sprint-1/USER-STORIES.md`
- Architektur: `docs/sprint-1/FEATURE-ARCH.md`
- Projekt-Regeln: `CLAUDE.md`
- Vision: `docs/VISION.md`

## Ziel-Definition

**Done wenn:**
1. `python -m kraken_monitor test-push frames/test.gif` zeigt Test-Bild auf LCD
2. `python -m kraken_monitor` loggt Config + CAM-Check ohne Crash
3. `liquidctl list` findet den Kraken
4. `docs/sprint-1/ZADIG-SETUP.md` + `CAM-COEXISTENCE.md` existieren als Wiederholungs-Doku

## Waves

### Wave 1 — Scaffolding (sequentiell, aber schnell)
| Story | Titel | Blocker |
|-------|-------|---------|
| US-001 | Python-Projekt scaffolden | — |

### Wave 2 — parallel möglich
| Story | Titel | Blocked-by |
|-------|-------|------------|
| US-002 | libusb-Treiber via Zadig + liquidctl | US-001 |
| US-006 | Config-System (TOML) + Logging | US-001 |

### Wave 3 — Hands-On Hardware
| Story | Titel | Blocked-by |
|-------|-------|------------|
| US-003 | CAM-LCD deaktivieren + Check-Skript | US-002 |

### Wave 4 — First Push
| Story | Titel | Blocked-by |
|-------|-------|------------|
| US-004 | Test-GIF manuell aufs Display pushen | US-002, US-003 |

### Wave 5 — Wrapper
| Story | Titel | Blocked-by |
|-------|-------|------------|
| US-005 | Kraken-Device-Wrapper (`kraken.py`) | US-004 |

## Auftrag

Die Stories in Wellen abarbeiten, nach jeder Story:
1. Verify-Befehle ausführen, nur wenn grün → weiter
2. PROGRESS.md aktualisieren: Status Story `TODO` → `DONE`
3. Commit: `feat(sprint-1): US-XXX — {titel}`

**Besonderheiten:**
- **US-002 braucht User-Interaktion** (Zadig-GUI, Admin-Rechte). Hier nicht autonom — an User übergeben und Output bestätigen lassen.
- **US-003 Screen-Mode in CAM deaktivieren** ist auch GUI-Click, nicht scriptbar. An User übergeben.
- **US-004 visuelles Ergebnis** — User muss bestätigen dass Test-GIF am LCD zu sehen ist, Screenshot optional.

## Commit-Strategie

Jede Story = ein Commit. Conventional Commits:
```
feat(sprint-1): US-001 — Python-Projekt scaffolden
feat(sprint-1): US-002 — Zadig + liquidctl verifiziert
feat(sprint-1): US-003 — CAM-LCD deaktiviert + cam_check.py
feat(sprint-1): US-004 — erstes Test-GIF auf LCD gepusht
feat(sprint-1): US-005 — KrakenDevice-Wrapper
feat(sprint-1): US-006 — Config + Logging
chore(sprint-1): PROGRESS.md DONE-Status
```

## Nach Sprint 1

- `/sprint-plan kraken-claude-monitor 1` mit Fokus "Sprint 2 Detail-Docs" aufrufen
- Dann Sprint 2 (ccusage + Renderer + Main-Loop) starten
