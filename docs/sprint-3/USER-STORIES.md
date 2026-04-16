# USER-STORIES.md — Sprint 3: Autostart + Polish + OAuth

> Ziel: Läuft seit Login stabil, überlebt Reboots. OAuth als optionaler Bonus.
> Roadmap-Level. Vor Sprint-Start verfeinern.

## Phase 1: Autostart-Infrastruktur

### US-013: Windows Task Scheduler XML + Install-Skript

**Context:** Das Script muss beim Login automatisch starten, ohne dass User manuell ne Konsole aufmacht. Windows Task Scheduler via XML definieren, PowerShell-Script zum Install.

**Input:** US-010 (Main-Loop läuft stabil)

**Task:**
1. `install/kraken-claude-monitor.task.xml` — Task-Definition: Trigger=AtLogon, Action=`pythonw.exe -m kraken_monitor` (pythonw = kein Konsolenfenster), Settings: RestartOnFailure, nicht parallel
2. `install/install.ps1`:
   - Prüft: venv existiert, pip-Install aktuell, config.default.toml vorhanden
   - `schtasks /create /xml kraken-claude-monitor.task.xml /tn "Kraken Claude Monitor"`
3. `install/uninstall.ps1` — `schtasks /delete /tn "Kraken Claude Monitor" /f`
4. Task verwendet absolute Pfade zu venv-Python, damit ohne aktiviertes venv funktioniert

**Output:** `install/kraken-claude-monitor.task.xml`, `install/install.ps1`, `install/uninstall.ps1`

**Verify:**
```powershell
./install/install.ps1
schtasks /query /tn "Kraken Claude Monitor" /v
# Erwartet: Task listed, State: Ready, NextRunTime: On Logon
# Manuell triggern:
schtasks /run /tn "Kraken Claude Monitor"
# Erwartet: LCD zeigt Live-Frame innerhalb 30s
```

**Blocked-by:** US-010

---

### US-014: Graceful Shutdown (SIGINT → "paused"-Frame)

**Context:** Wenn Monitor gestoppt wird (Task beendet, Shutdown, Ctrl+C), sollte LCD nicht auf altem Frame stehen bleiben — sondern auf ein neutrales "paused"-Frame, damit klar ist dass Monitor nicht mehr live ist.

**Input:** US-010

**Task:**
1. `loop.run_loop` mit `atexit.register` + `signal.signal(SIGINT, handler)`
2. Bei Shutdown: Render Frame "PAUSED" (graues Theme, Uhrzeit des letzten Updates), push, dann exit
3. Alternative: LCD wieder auf "blank" oder CAM-Default (config-option)

**Output:** `src/kraken_monitor/loop.py` erweitert, neues Template in renderer.py

**Verify:**
```powershell
python -m kraken_monitor
# In anderem Terminal:
taskkill /im pythonw.exe  # bzw Strg+C wenn fg
# Erwartet: LCD zeigt "PAUSED"-Frame statt altem Live-Wert
```

**Blocked-by:** US-010

---

## Phase 2: Polish

### US-015: Plan-Detection aus ccusage

**Context:** Statt Plan-Typ + Token-Limit hardcoded zu config: ccusage liefert es. Script soll ableiten ob Pro / Max5 / Max20 und Limit entsprechend setzen.

**Input:** US-007 (ccusage wrapper)

**Task:**
1. `ccusage.py`: ccusage hat separates Command `npx ccusage limits --json` oder Field im blocks-Output — prüfen welches
2. `detect_plan() -> PlanType` Funktion, mit Fallback auf Config-Default
3. Bei Config-Wert `plan.type = "auto"` → Detection nutzen
4. Sicheres Fallback: unknown → größtes Limit annehmen (Max20, damit nicht fälschlich auf "100%" geflaggt)

**Output:** `ccusage.py` erweitert, `config.py` mit `plan.type="auto"` Unterstützung

**Verify:**
```powershell
python -c "from kraken_monitor.ccusage import detect_plan; print(detect_plan())"
# Erwartet: "pro" / "max5" / "max20" je nach Account
```

**Blocked-by:** US-007

---

### US-016: Optional — OAuth-Endpoint-Integration hinter Flag

**Context:** Wenn `oauth.enabled = true`, nutze den präziseren OAuth-Endpoint für Session + Weekly-Cap. Fragil (undokumentiert), daher hinter Flag. Fallback immer ccusage.

**Input:** US-007 (ccusage-Wrapper als Fallback)

**Task:**
1. `src/kraken_monitor/oauth.py` — liest Token aus `%USERPROFILE%\.claude\.credentials.json`, fetcht `api.anthropic.com/api/oauth/usage` mit Header `anthropic-beta: oauth-2025-04-20`
2. `fetch_oauth_snapshot() -> QuotaSnapshot | None` — kompatibel mit ccusage-Shape, nutzt `weekly_remaining_pct` wenn vorhanden
3. `loop.run_loop`: wenn `config.oauth.enabled` → OAuth-first mit ccusage-Fallback bei Fehler
4. `renderer.py` erweitert: 2 Ringe (Session innen, Weekly außen) wenn Weekly-Daten da

**Output:** `src/kraken_monitor/oauth.py` (~70 LOC), `loop.py` + `renderer.py` erweitert

**Verify:**
```powershell
# config.local.toml: [oauth] enabled=true
python -c "from kraken_monitor.oauth import fetch_oauth_snapshot; print(fetch_oauth_snapshot())"
# Erwartet: QuotaSnapshot mit weekly_remaining_pct != None
python -m kraken_monitor
# Erwartet: LCD zeigt 2 Ringe (Session + Weekly)
```

**Blocked-by:** US-007

---

## Phase 3: Abschluss

### US-017: README + Troubleshooting-Guide

**Context:** In 6 Monaten weiß der User nicht mehr wie Zadig geht. README als Onboarding, Troubleshooting für die 5 häufigsten Fehler.

**Input:** US-013 (Install-Script), Sprint 1–2 komplett

**Task:**
1. `README.md` im Projekt-Root:
   - Was macht das Tool (1 Absatz)
   - Screenshot des LCD (wenn möglich)
   - Install (3 Schritte: venv, Zadig, install.ps1)
   - Config (Beispiel config.local.toml)
   - Troubleshooting (5 Fälle): "No device found", "CAM überschreibt Frame", "Script crasht beim Start", "OAuth 401", "ccusage nicht gefunden"
2. `docs/TROUBLESHOOTING.md` — ausführlicher

**Output:** `README.md`, `docs/TROUBLESHOOTING.md`

**Verify:** Jemand der nicht wusste wie das geht, folgt dem README und bringt es zum Laufen. (Selbst-Check: 6 Monate später.)

**Blocked-by:** US-013

---

### US-018: End-to-End Smoke-Test nach Reboot

**Context:** Finale Validierung dass alles zusammen funktioniert: Reboot → Login → LCD zeigt Live-Stand. Ohne Konsole öffnen.

**Input:** Alle Sprint-3-Stories abgeschlossen

**Task:**
1. Rechner neu starten
2. Einloggen, 60s warten
3. LCD anschauen
4. Log-Datei checken: `%USERPROFILE%\kraken-claude-monitor.log` — sollte INFO-Zeilen seit Login zeigen
5. `schtasks /query /tn "Kraken Claude Monitor"` — State "Running"
6. Ein Claude-Code-Request machen, 20s warten, LCD-Update bestätigen
7. Bei Erfolg: `PROGRESS.md` Sprint 3 auf DONE

**Output:** Foto/Screenshot als Proof, PROGRESS.md aktualisiert

**Verify:** LCD zeigt aktuelle Zahl ohne dass User was gemacht hat.

**Blocked-by:** US-013, US-014, US-017

---

## Dependency Graph

```
US-010 ──┬─▶ US-013 ──▶ US-017 ──▶ US-018
         │
         └─▶ US-014 ──────────────▶ US-018

US-007 ──┬─▶ US-015
         │
         └─▶ US-016 (optional)
```

## Summary

| Phase | Stories | Effort |
|-------|---------|--------|
| 1: Autostart | US-013, US-014 | ~1.5h |
| 2: Polish | US-015, US-016 | ~1.5h |
| 3: Abschluss | US-017, US-018 | ~1h |
| **Total** | **6 Stories** | **~4h** |

**Done wenn:** Reboot → 60s später LCD zeigt aktuellen Quota-Stand, ohne dass User was macht. README reicht um Setup zu wiederholen.
