# ROADMAP.md — kraken-claude-monitor

3 Sprints, Ziel: **first-try-funktionaler Autostart-Monitor** auf dem Kraken-LCD.

## Sprint-Übersicht

| Sprint | Name | Ziel | Stories | Effort |
|--------|------|------|---------|--------|
| 1 | Foundation + Hardware-Path | Test-GIF erscheint auf LCD, Python-Gerüst steht | US-001 – US-006 | ~4h |
| 2 | Daten-Pipeline + Renderer | Live-Quota wird gerendert und gepusht (manuell gestartet) | US-007 – US-012 | ~5h |
| 3 | Autostart + Polish + OAuth | Läuft seit Login stabil, OAuth als Bonus | US-013 – US-018 | ~4h |
| **Total** | | | **18 Stories** | **~13h** |

## Abhängigkeitsgraph

```
Sprint 1 (Foundation):
  US-001 ──┬─▶ US-005 ──┬─▶ US-006
           │            │
  US-002 ──┤            │
           │            │
  US-003 ──┤            │
           │            │
  US-004 ──┘            │

Sprint 2 (Pipeline): [blocked by Sprint 1]
  US-007 ──┬─▶ US-010 ──┬─▶ US-011 ──▶ US-012
           │            │
  US-009 ──┼─▶ US-008 ──┘
           │
  US-006 ──┘ [aus Sprint 1]

Sprint 3 (Polish): [blocked by Sprint 2]
  US-013 ──┬─▶ US-018
           │
  US-014 ──┤
           │
  US-015 ──┤
           │
  US-016 ──┼─▶ US-017
           │
  US-010 ──┘ [aus Sprint 2]
```

---

## Sprint 1 — Foundation + Hardware-Path (DETAIL)

**Was dieser Sprint liefert:** Ein Python-Gerüst steht, der Kraken ist via `liquidctl` ansprechbar, und ein Test-GIF erscheint auf dem LCD. Kein Claude-Bezug noch — reines "Hardware-Path freimachen".

| Story | Titel | Effort | Blocked-by |
|-------|-------|--------|------------|
| US-001 | Python-Projekt scaffolden (pyproject, venv, src/) | S | — |
| US-002 | libusb-Treiber via Zadig + liquidctl-Install verifizieren | M | US-001 |
| US-003 | CAM-LCD-Screen deaktivieren (Doku + Check-Skript) | S | US-002 |
| US-004 | Test-GIF manuell aufs Display pushen | S | US-002, US-003 |
| US-005 | Kraken-Device-Wrapper (`kraken.py`) | M | US-004 |
| US-006 | Config-System (TOML) + Logging | S | US-001 |

**Detail-Docs:** `docs/sprint-1/USER-STORIES.md`, `docs/sprint-1/FEATURE-ARCH.md`, `docs/sprint-1/EXECUTE.md`

**Done wenn:** `python -m kraken_monitor.kraken test-push frames/test.gif` lädt ein Test-Bild aufs LCD.

---

## Sprint 2 — Daten-Pipeline + Renderer (ROADMAP)

**Was dieser Sprint liefert:** Wenn du das Script manuell startest, zeigt das LCD deinen aktuellen Claude-Quota als Prozentring mit Reset-Zeit. Alle 10s aktualisiert. Bei ccusage-Fehlern zeigt es einen Stale-Indikator statt zu crashen.

| Story | Titel | Effort | Blocked-by |
|-------|-------|--------|------------|
| US-007 | ccusage-Wrapper (subprocess + JSON-Parse) | M | US-006 |
| US-008 | Frame-Renderer (Pillow, 640×640 Dark-Purple-Theme) | L | US-009 |
| US-009 | Theme-Konstanten (Farben, Fonts, Layout) | S | US-001 |
| US-010 | Main-Loop mit graceful error handling | M | US-005, US-007, US-008 |
| US-011 | Stale-Data-Indicator + Retry-Backoff | S | US-010 |
| US-012 | Unit-Tests für Renderer + Parser | M | US-007, US-008 |

**Detail-Docs:** Wird vor Sprint-Start erstellt (`/sprint-plan` erneut mit Sprint=2).

**Done wenn:** `python -m kraken_monitor` läuft in der Konsole, LCD zeigt Live-Prozent, Strg+C stoppt sauber.

---

## Sprint 3 — Autostart + Polish + OAuth (ROADMAP)

**Was dieser Sprint liefert:** Nach Login läuft der Monitor automatisch, überlebt Reboots, und optional (Config-Flag) nutzt er den präziseren OAuth-Endpoint mit Weekly-Cap statt nur 5h-Block. README erklärt Install + Fehlersuche.

| Story | Titel | Effort | Blocked-by |
|-------|-------|--------|------------|
| US-013 | Windows Task Scheduler XML + Install-Skript | M | US-010 |
| US-014 | Graceful Shutdown (SIGINT → "paused"-Frame) | S | US-010 |
| US-015 | Plan-Detection aus ccusage (Pro/Max5/Max20) | S | US-007 |
| US-016 | Optional: OAuth-Endpoint-Integration hinter Flag | M | US-007 |
| US-017 | README + Troubleshooting-Guide | S | US-013 |
| US-018 | End-to-End Smoke-Test nach Reboot | S | US-013, US-014 |

**Detail-Docs:** Wird vor Sprint-Start erstellt.

**Done wenn:** Rechner-Neustart → 60s später zeigt LCD aktuellen Quota-Stand, ohne dass du eine Konsole öffnen musstest.

---

## Bewusst NICHT in den 3 Sprints

| Thema | Warum nicht jetzt |
|-------|-------------------|
| GUI / System-Tray | CLI + Task Scheduler reicht, GUI wäre 2× Aufwand |
| Cross-AIO-Support (Corsair, Asus) | Kein Bedarf, eigene Hardware |
| Anthropic-API-direkt (API-Key-Nutzer) | User nutzt Claude Code Plan, nicht direct-API |
| Animierte Frames | Upload-Rate 1-2s macht Animation unbrauchbar |
| Weekly-Cap-Graph / Historie | Scope-Creep, LCD hat keinen Platz |
| Notifications (Push/Sound) | Vision: nur visuell |
| Plugin-System für andere Themes | Solo-Tool, nicht generisch |
| Web-Config-UI | TOML reicht, 1 Person nutzt es |

## Aktuelle Projekt-Metriken

| Metrik | Wert |
|--------|------|
| Sprints done | 0 / 3 |
| Stories done | 0 / 18 |
| Tests | 0 |
| LOC | 0 |
| Erwartete End-LOC | ~400 |

## Vision-Abdeckung

| Vision-Stufe | Sprint | Status |
|--------------|--------|--------|
| Stufe 1: Hardware-Path | Sprint 1 | 📋 geplant |
| Stufe 2: Live-Rendering | Sprint 2 | 📋 geplant |
| Stufe 3: Autostart stabil | Sprint 3 | 📋 geplant |
