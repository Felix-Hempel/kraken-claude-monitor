# VISION.md — kraken-claude-monitor

## Problem

Claude Code hat harte Quota-Limits: 5-Stunden-Rolling-Session + 7-Tage-Weekly-Cap. Wer tief im Flow ist, merkt zu spät dass das Limit näher rückt. Ein Terminal-Tab mit `claude-monitor` hilft nur wenn er sichtbar ist — ein zweiter Monitor ist zu groß, das Panel-LCD auf der Pumpe wäre perfekt.

## Lösung

Auf dem NZXT Kraken Elite LCD (640×640) einen Live-Quota-Indikator rendern:
- Großer Prozentring (Session-Verbrauch)
- Zahl in der Mitte (z.B. "67%")
- Sekundär-Text (Reset-Zeit, z.B. "resets in 3h 12m")
- Dark-Purple-Theme (passt zum Case-Setup)

Pipeline:
```
ccusage (JSON) ──▶ QuotaSnapshot ──▶ Pillow-Frame (GIF) ──▶ liquidctl ──▶ Kraken-LCD
     ^10s                                                        ^USB
```

## Kern-Loop

1. Script läuft als Windows-Task-Scheduler-Job seit Login
2. Alle 10s: `npx ccusage blocks --json` lesen
3. Aktiven 5h-Block extrahieren (Tokens, Burn-Rate, Zeit bis Block-Ende)
4. Pillow rendert 640×640 Frame mit Prozent + Reset-Zeit
5. liquidctl pusht als 1-Frame-GIF aufs LCD
6. Sleep 10s, Loop

## Zielgruppe

Genau eine Person: Felix. Kein Distributions-Ziel, kein Plugin-Store. Solo-Nutzung.

## Abgrenzung (explizit NICHT in-scope)

- Kein GUI / System-Tray-App (Kommandozeile reicht)
- Kein Cross-Platform (Windows-only)
- Kein Support für andere AIOs (nur NZXT Kraken)
- Keine Anthropic-API-direkt-Nutzung (nur Claude-Code-Plan via ccusage)
- Keine historischen Graphen (nur jetziger Status)
- Keine Notifications (kein Push, kein Sound) — nur visuell auf LCD
- Keine Konfiguration per UI — TOML-Datei reicht

## Prinzipien

1. **First-try-functional** — Research ist durch (siehe Research-Report). Keine Experimente mit unbekannten Ansätzen.
2. **ccusage > OAuth** — bewährt > präzise-aber-fragil. OAuth als optionaler Bonus.
3. **10s-Polling** — kein Sub-Sekunden-Rendering, kein Animation. Statischer Frame pro Poll.
4. **Kein Goldplating** — keine Themes-Engine, keine Plugin-API, keine Web-UI.
5. **Kein Auto-Fix** — wenn CAM LCD bespielt, wirft Script Error. User behebt manuell.

## Stufen (Fertigstellung)

| Stufe | Merkmale |
|-------|----------|
| 0 | Planung (jetzt) |
| 1 (Sprint 1) | Hardware-Path validiert: liquidctl pusht Test-GIF aufs LCD |
| 2 (Sprint 2) | Live-Daten-Rendering: Script zeigt aktuellen Quota-Stand, aber manueller Start |
| 3 (Sprint 3) | Autostart + stabil: läuft seit Login, überlebt Reboots, OAuth optional |

## Empirische Basis

- Research-Report (vorhergehende Konversation) bestätigt Pipeline: ccusage + liquidctl beide aktiv gewartet (2025/2026), Pattern von [NZXT-Kraken-Linux-Infographic](https://github.com/aminedeesucre/NZXT-Kraken-Linux-Infographic) bewiesen funktional.
- liquidctl-Bug-Tracker #757 bestätigt FW-Workaround (GIF statt static).
- ccusage `blocks --json` liefert alle benötigten Felder (`totalTokens`, `timeRemaining`, `burnRate`, `isActive`).

## Backlog (bewusst NICHT in Sprint 1–3)

| Idee | Warum nicht jetzt | Status |
|------|-------------------|--------|
| Burn-Rate-Farbcode (grün/gelb/rot je nach Rate) | Nice-to-have, erst wenn Grundversion läuft | 📋 |
| Weekly-Cap als zweite Anzeige (Split-Screen) | Braucht OAuth-Endpoint zuverlässig | 📋 |
| Notification wenn >90% | User will nur visuell, kein Noise | ❌ bewusst abgelehnt |
| Cross-AIO-Support (Corsair, Asus) | Eigene Hardware, kein Bedarf | ❌ bewusst abgelehnt |
| Model-Breakdown (Opus vs Sonnet) | ccusage liefert es, aber 640px hat kaum Platz für mehr Text | 📋 |
