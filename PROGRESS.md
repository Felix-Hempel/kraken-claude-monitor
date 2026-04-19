# PROGRESS.md — kraken-claude-monitor

## Compact-Recovery

> Kontext verloren? Lies diese 4 Dateien:
> 1. `CLAUDE.md` — Regeln, Stack, Patterns, Architektur
> 2. **Diese Datei** — Aktueller Status, was existiert, was fehlt
> 3. `docs/VISION.md` — Was das Tool soll und warum
> 4. `docs/ROADMAP.md` — 3-Sprint-Gesamtplan

**Projekt:** kraken-claude-monitor
**Aktueller Sprint:** Sprint 3 Code-DONE, User-Gate US-018 offen (2026-04-19)
**Aktueller Status:** 16/18 Stories DONE (6 S1 + 6 S2 + 4 S3), US-016 bewusst ausgelassen (optional/fragil), US-018 wartet auf Reboot
**Test-Count:** 35 (pytest, alle grün)
**Stufe:** 3 — Autostart + Polish: Autologin-Task registriert, Graceful Shutdown mit PAUSED-Frame, Plan-Auto-Detection via ccusage

---

## Sprint 1 — Foundation + Hardware-Path (2026-04-16 → 2026-04-19)

| Story | Titel | Status |
|-------|-------|--------|
| US-001 | Python-Projekt scaffolden | DONE |
| US-002 | Treiber-Setup (ehemals Zadig, jetzt Recovery-Doku) | DONE |
| US-003 | CAM-LCD deaktivieren + cam_check | DONE |
| US-004 | Test-Image manuell aufs Display pushen | DONE (Visual-Verify 2026-04-19) |
| US-005 | KrakenDevice-Wrapper + winusbcdc-Patch | DONE |
| US-006 | Config + Logging | DONE |

### Neu entdeckte Facts während Sprint 1

1. **Interface-Layout war umgekehrt zur bisherigen Annahme** — Kraken 2023 (PID 0x300E) hat MI_00 = WinUSB (Bulk/Display) und MI_01 = HidUsb (HID-Steuerung), per USB-Descriptor verifiziert. Ältere Kraken X3/Z3 haben's umgekehrt (daher die ursprüngliche Zadig-Doku-Annahme). **Keine Zadig-Custom-Treiber nötig**; Windows bindet beide Interfaces automatisch korrekt. `docs/sprint-1/ZADIG-SETUP.md` ist entsprechend neu geschrieben, enthält jetzt Recovery-Fälle statt Install-Anleitung.

2. **winusbcdc-Library hat zwei Bugs in Kombination mit Kraken 2023** — Runtime-Monkeypatch in `kraken_monitor.kraken` fixt beides:
   - Custom-WinUSB-GUID (`300e300d-…`) aus MS-OS-Descriptor statt Standard-GUID
   - `list_usb_devices()` ohne Filter liefert leere Liste; Wrapper setzt `vid=0x1E71, pid=0x300E` als Default
   - Details: `docs/sprint-1/WINUSBCDC-PATCH.md`

3. **LCD-Framebuffer ist 240×240, Panel 640×640** — Firmware skaliert intern. Bei 640er-Frames werden Muster verzerrt, uniforme Farben gehen. `KrakenDevice.connect()` setzt `lcd_resolution = (240, 240)` explizit.

4. **Kraken 2023 FW 2.0.0 `static`-Mode** — liquidctl's `_send_2023_data_fw2` schickt das Bild doppelt (Framebuffer-Swap-Trick, kein Bucket-Setup). Der reguläre FW1-Pfad (`_send_data`) funktioniert auf FW 2.0.0 nicht (Bucket-Commands werden nicht beantwortet). Für unseren Poll-basierten Ansatz reicht der doppelte static-Push.

5. **Research-Report war bei liquidctl-Issues invertiert:**
   - **#631** (echtes Issue): `gif`-Mode auf FW 2.X.Y **nicht unterstützt** — nur `static` mit PNG/JPG geht.
   - **#757** (Non-Issue in liquidctl 1.16): `static`-Bug ist längst gefixt.
   - **Implikation:** Wir nutzen `static` mit PNG statt `gif`. `push_frame()` erkennt Dateiendung automatisch.

6. **libusb-package 1.0.26.1 cp314-wheel bundled keine DLL** — PyUSB crasht mit `NoBackendError`. Fix: `scripts/post_install.py` kopiert DLL aus `libusb`-Package rüber. Idempotent, Teil des Install-Flows.

### Dateien erstellt in Sprint 1

```
pyproject.toml                              — Projekt-Metadaten, Dependencies
config.default.toml                         — Default-Config
README.md                                   — Install + Quick-Start
src/kraken_monitor/
  __init__.py                               — Package, Version
  __main__.py                               — CLI mit status/test-push/run/version
  config.py                                 — TOML-Loader + Dataclasses
  logging_setup.py                          — Logging-Format
  cam_check.py                              — CAM-Prozess-Warning
  kraken.py                                 — KrakenDevice Wrapper + push_frame
scripts/
  make_test_gif.py                          — Test-PNG-Generator (640x640)
  post_install.py                           — libusb-DLL-Fix (Windows, Python 3.14)
docs/sprint-1/
  ZADIG-SETUP.md                            — Treiber-Layout + Recovery-Fälle (2026-04-19 neu)
  WINUSBCDC-PATCH.md                        — Runtime-Patch-Begründung (2026-04-19 neu)
  CAM-COEXISTENCE.md                        — LCD auf Off stellen
docs/progress/
  progress-kraken-treiber-2026-04-19.md     — Debug-Session Treiber + LCD
frames/test.png                             — Generiertes Test-Bild (15 KB)
```

### Sprint-Abschluss-Verify (2026-04-19)

```
> python -m kraken_monitor test-push frames/test.png
Kraken verbunden: NZXT Kraken 2023 @ 240x240
Test-GIF gepusht: .../frames/test.png
```
→ LCD zeigt `test.png` (weißer "KRAKEN TEST"-Text auf dunklem Grund mit violettem Kreis).

```
> python -m kraken_monitor status
[OK] Config geladen
[INFO] CAM laeuft: False
[OK] Kraken gefunden: NZXT Kraken 2023
     Liquid temperature: 33.5 °C / Pump speed: 1374 rpm / …
```
→ Alle Checks grün, Status-Read + LCD-Write verifiziert.

---

## Sprint 2 — Daten-Pipeline + Renderer (2026-04-19)

| Story | Titel | Status |
|-------|-------|--------|
| US-007 | ccusage-Wrapper (subprocess + JSON-Parse) | DONE |
| US-008 | Frame-Renderer (Pillow, PNG, 640×640) | DONE |
| US-009 | Theme-Konstanten (Farben, Fonts, Layout) | DONE |
| US-010 | Main-Loop mit graceful error handling | DONE |
| US-011 | Stale-Data-Indicator + Retry-Backoff | DONE |
| US-012 | Unit-Tests für Renderer + Parser | DONE |

### Neu entdeckte Facts während Sprint 2

1. **Clear enqueued reports vor jedem `set_screen`** — ohne das hängt der 2. und jeder weitere Push auf `_read_until({0x31,0x01})`, weil nach dem FW2-static-Push-Pfad die HID-Response-Queue in einem Zustand bleibt, in dem der erneute `[0x30,0x01]`-Request keine Antwort produziert. Fix: `KrakenDevice.push_frame` ruft vor `set_screen` `self._device.device.clear_enqueued_reports()` auf.

2. **ccusage `burnRate.tokensPerMinuteForIndicator` > `tokensPerMinute`** — die Raw-tokensPerMinute explodiert durch Cache-Reads (bei Opus-1M-Context bis ~1,6 M Tokens/Min). `ForIndicator` zählt nur input+output und ist die sinnvolle Anzeige-Metrik.

3. **Frame-Format ist PNG (static), nicht GIF** — liquidctl Issue #631. Renderer schreibt PNG mit `optimize=True`, `push_frame` wählt `static`-Mode per Dateiendung.

4. **Canvas 640×640 statt direkt 240×240** — liquidctl skaliert intern via `Image.resize(lcd_resolution)`. Größeres Canvas gibt schärferen Text nach Downsampling (Pillow default LANCZOS) und einfachere Layout-Konstanten.

5. **`session_token_limit = 19000` passt nicht zur Realität** — mein aktiver Block zeigt 80+ Millionen `totalTokens` (inkl. Cache-Reads). Renderer cappt bei 100%, aber der "Pro"-Default-Limit ist zu klein. User sollte in `config.local.toml` selbst kalibrieren. Nicht Code-Problem.

### Dateien erstellt/geändert in Sprint 2

```
src/kraken_monitor/
  theme.py                                  — Layout-Konstanten + Font-Loader + color_for_pct
  ccusage.py                                — Subprocess + JSON-Parse + QuotaSnapshot
  renderer.py                               — Pillow 640×640 PNG: Ring + Text + Idle/Stale
  loop.py                                   — Main-Loop mit Stale-Backoff + Reconnect
  kraken.py                                 — push_frame: clear_enqueued_reports vor set_screen
  __main__.py                               — cmd_run implementiert, default-Command = run
tests/
  test_ccusage.py                           — 7 Tests (Parser, Gap-Handling, Fehler-Propagation)
  test_renderer.py                          — 14 Tests (Dimensionen, Idle, Stale, format_time)
  test_theme.py                             — 6 Tests (color_for_pct, Font-Loader)
  fixtures/
    ccusage_active.json                     — Fixture mit aktivem Block
    ccusage_empty.json                      — Fixture ohne aktiven Block
```

### Sprint-Abschluss-Verify (2026-04-19)

```
> python -m kraken_monitor run
Kraken verbunden: NZXT Kraken 2023 @ 240x240
Loop gestartet — poll=10s, plan=pro, limit=19000 tokens
Frame gepusht — 87100674 tokens, 14849s bis Reset
Frame gepusht — 88836847 tokens, 14834s bis Reset
Frame gepusht — 89312908 tokens, 14820s bis Reset
```
→ LCD aktualisiert sich alle 10s, Prozent + Reset-Time sichtbar.

```
> pytest -q
27 passed, 1 warning in 0.20s
```

---

## Sprint 3 — Autostart + Polish (2026-04-19)

| Story | Titel | Status |
|-------|-------|--------|
| US-013 | Windows Task Scheduler Install-Scripts | DONE |
| US-014 | Graceful Shutdown (PAUSED-Frame) | DONE |
| US-015 | Plan-Detection aus ccusage | DONE |
| US-016 | OAuth-Endpoint (optional, fragil) | SKIPPED — bewusst ausgelassen |
| US-017 | README + TROUBLESHOOTING | DONE |
| US-018 | E2E-Smoke-Test nach Reboot | User-Gate — offen bis Reboot |

### Neu entdeckte Facts während Sprint 3

1. **ccusage `--token-limit max` liefert `tokenLimitStatus.limit`** — historisches 5h-Block-Maximum aus der Usage-Historie. Deutlich präziser als die hardcoded Pro/Max5/Max20-Schätzungen in der Config. `plan.type = "auto"` nutzt den Wert, Fallback auf `session_token_limit` wenn's fehlt (z.B. bei frischer Historie). Default in `config.default.toml` auf "auto" gestellt.

2. **SIGBREAK-Handler nötig für Task-Scheduler** — `schtasks /end` schickt `CTRL_BREAK_EVENT` (Windows). Ohne Handler terminiert Python ohne `finally`-Block → kein PAUSED-Frame. `_install_break_handler()` in `loop.py` konvertiert SIGBREAK in KeyboardInterrupt.

3. **pythonw.exe braucht File-Logging** — im Autostart-Task hat pythonw keine Konsole, stdout geht ins Nichts. `logging_setup.py` schreibt jetzt zusätzlich nach `%USERPROFILE%\kraken-claude-monitor.log` (RotatingFileHandler, 1 MB × 3 Backups).

4. **PowerShell-5.1 stolpert über em-dashes (`—`) in Strings** — `.ps1`-Dateien ohne BOM werden teils als ANSI gelesen, Unicode-Zeichen brechen Parser. `install/uninstall.ps1` nutzt ASCII-Bindestriche, install.ps1 kommt ohne Umlaute aus.

### Bewusst ausgelassen

**US-016 OAuth-Endpoint:** Im Sprint-Plan als „Optional" markiert. Der Endpoint (`api.anthropic.com/api/oauth/usage` mit `anthropic-beta: oauth-2025-04-20`) ist undokumentiert und fragil. Session-Daten aus ccusage reichen für die Visualisierung — Weekly-Cap als zweiter Ring wäre nice-to-have, aber der Aufwand (OAuth-Token-Lifecycle, Beta-Header-Stabilität, Fallback-Pfad) ist disproportional. In `docs/VISION.md` als `📋`-Backlog-Eintrag erhalten.

### Dateien erstellt/geändert in Sprint 3

```
install/
  install.ps1                               — Register-ScheduledTask mit AtLogOn-Trigger
  uninstall.ps1                             — Unregister + vorher Stop
src/kraken_monitor/
  loop.py                                   — _install_break_handler, _resolve_plan_limit,
                                              _push_paused_frame im finally
  renderer.py                               — render_paused_frame für Graceful-Shutdown
  ccusage.py                                — --token-limit max, detected_limit in Snapshot
  logging_setup.py                          — RotatingFileHandler nach %USERPROFILE%\...log
config.default.toml                         — plan.type = "auto" als Default
tests/
  test_loop.py                              — 4 Tests für _resolve_plan_limit
  test_renderer.py                          — +2 Tests für render_paused_frame
  test_ccusage.py                           — +2 Tests für detected_limit
  fixtures/ccusage_active.json              — um tokenLimitStatus ergänzt
README.md                                   — Sprint-3-Flow (install.ps1, Autostart-Kommandos)
docs/TROUBLESHOOTING.md                     — 9 häufige Fälle + Log-Sammel-Anleitung
```

### Sprint-Abschluss-Verify (2026-04-19)

```
> python -m kraken_monitor status
kraken-claude-monitor v0.1.0
[OK]   Config geladen
       poll=10s, plan=auto, brightness=80%
[INFO] CAM laeuft: False
[OK]   Kraken gefunden: NZXT Kraken 2023
       Liquid temperature: 34.7 °C / Pump speed: 1377 rpm / …

> python -m kraken_monitor run
Loop gestartet — poll=10s, plan=auto, limit=auto tokens
Frame gepusht — 125663727 tokens, 13920s bis Reset
Frame gepusht — 125933037 tokens, 13905s bis Reset

> pytest -q
35 passed, 1 warning in 0.30s
```

### Offen: US-018 E2E-Smoke-Test

Braucht User-Hands-on:
1. `./install/install.ps1` ausführen (Admin nicht nötig — Task läuft als User)
2. Reboot
3. Nach Login: 60s warten
4. LCD prüfen — sollte Live-Quota zeigen, kein PAUSED/IDLE
5. `Get-Content $env:USERPROFILE\kraken-claude-monitor.log -Tail 20` — INFO-Zeilen seit Login
6. `Get-ScheduledTaskInfo -TaskName "Kraken Claude Monitor"` — LastTaskResult=0 oder 267009 (läuft)
7. Dann Sprint 3 komplett DONE.

---

## Aktueller Zustand (2026-04-19)

### Projekt-Metriken

| Metrik | Wert |
|--------|------|
| Source-Dateien | 10 (kraken_monitor) + 2 (scripts) + 2 (install PS) |
| Test-Dateien | 4 + 2 Fixtures |
| Tests | 35 (alle grün) |
| LOC aktuell | ~1400 (inkl. Docs) |
| Verifiziert (Code) | Config, Logging, CLI, Status, LCD-Push, ccusage-Parse, Live-Loop, Stale-Mode, Plan-Auto-Detect, PAUSED-Frame |
| Offen (User-Gate) | US-018 Reboot-Smoke-Test |

### Bekannte Lücken / Risiken

- **liquidctl Issue #631** — umgesetzt: PNG/static statt GIF. Auto-Detection via Dateiendung.
- **libusb-package 1.0.26.1 cp314** — umgesetzt: `post_install.py` als Workaround.
- **winusbcdc-Bugs** — umgesetzt als Runtime-Patch in `kraken.py` (`_patch_winusbcdc()`). Siehe `docs/sprint-1/WINUSBCDC-PATCH.md`.
- **CAM-LCD auf Off** — User-Gate, aber `cam_check.py` warnt.
- **Display zeigt ggf. Liquid-Fallback wenn längere Zeit kein Push kommt** — in Sprint 2 Main-Loop prüfen, ob 10s-Polling den Fallback überschreibt.

### Umgebung (verifiziert)

- OS: Windows 11 Home
- Python: 3.14.3 (system), venv aktiv
- liquidctl: 1.16.0
- Pillow: 12.2.0
- Kraken: NZXT Kraken 2023 (PID 1E71:300E), FW 2.0.0, LCD 240×240 Framebuffer
- Treiber: MI_00 WinUSB (Microsoft `winusb.inf`), MI_01 HidUsb — beide automatisch
- Node.js: v22.14.0 (für ccusage in Sprint 2)
