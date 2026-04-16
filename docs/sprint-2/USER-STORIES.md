# USER-STORIES.md — Sprint 2: Daten-Pipeline + Renderer

> Ziel: Live-Quota wird gerendert und gepusht. Main-Loop läuft stabil solange Konsole offen.
> Roadmap-Level-Detail: Task-Schritte kompakt, volle Verify-Befehle. Vor Sprint-Start ggf. verfeinern.

## Phase 1: Datenquelle

### US-007: ccusage-Wrapper (subprocess + JSON-Parse)

**Context:** Core-Datenquelle. `npx ccusage blocks --json` liefert JSON mit aktuellen 5h-Blocks. Wir brauchen eine Python-Funktion die das aufruft, parst und in eine typisierte Dataclass packt.

**Input:** Node.js installiert, `npx ccusage@latest blocks --json` liefert im Terminal gültiges JSON.

**Task:**
1. `src/kraken_monitor/ccusage.py` anlegen
2. Dataclass `QuotaSnapshot`: `total_tokens: int`, `burn_rate: float`, `time_remaining_sec: int`, `block_start: datetime`, `block_end: datetime`, `is_active: bool`, `fetched_at: datetime`
3. Funktion `fetch_snapshot() -> QuotaSnapshot | None` — ruft `npx ccusage blocks --json` via subprocess (5s timeout), parst JSON, extrahiert aktiven Block
4. Error-Handling: kein aktiver Block → `None`, subprocess-Fail → `CCUsageError`

**Output:** `src/kraken_monitor/ccusage.py` (~60 LOC)

**Verify:**
```powershell
python -c "from kraken_monitor.ccusage import fetch_snapshot; print(fetch_snapshot())"
# Erwartet: QuotaSnapshot(total_tokens=..., ...) oder None wenn grad kein Claude-Code offen
```

**Blocked-by:** US-006

---

### US-009: Theme-Konstanten (Farben, Fonts, Layout)

**Context:** Bevor der Renderer gebaut wird, alle visuellen Konstanten an einer Stelle. Vermeidet Magic-Numbers im Draw-Code.

**Input:** US-001 (src/-Struktur), US-006 (ThemeConfig-Dataclass)

**Task:**
1. `src/kraken_monitor/theme.py` anlegen
2. Konstanten: `LCD_SIZE = 640`, `RING_WIDTH_PX = 40`, `RING_INNER_RADIUS = 220`, `RING_OUTER_RADIUS = 260`, Font-Sizes (`FONT_SIZE_BIG=160`, `FONT_SIZE_LABEL=40`, `FONT_SIZE_SUB=32`)
3. Font-Loader: Fallback-Chain von Font-Familien (Inter → Segoe UI → arial.ttf) — gibt `ImageFont` zurück, raised `FontNotFoundError` wenn keine gefunden
4. Farb-Getter: `color_for_pct(pct: float) -> str` — grün <60%, gelb <85%, rot ≥85% (als Hex)

**Output:** `src/kraken_monitor/theme.py` (~50 LOC)

**Verify:**
```powershell
python -c "from kraken_monitor.theme import color_for_pct, load_font; print(color_for_pct(95)); load_font(40)"
# Erwartet: "#EF4444" (rot) und kein Crash
```

**Blocked-by:** US-001

---

## Phase 2: Rendering

### US-008: Frame-Renderer (Pillow, 640×640 Dark-Purple-Theme)

**Context:** Pillow rendert einen 640×640-Frame pro Snapshot: Prozent-Ring außen, Prozent-Zahl groß in der Mitte, Reset-Zeit darunter. Als 1-Frame-GIF gespeichert (wg. liquidctl Issue #757).

**Input:** US-007 (QuotaSnapshot), US-009 (Theme-Konstanten)

**Task:**
1. `src/kraken_monitor/renderer.py` anlegen
2. Funktion `render_frame(snapshot: QuotaSnapshot, plan_limit: int, theme: ThemeConfig) -> Path`:
   - Neues `Image.new("RGB", (640, 640), theme.bg_color)`
   - Prozent-Ring zeichnen mit `ImageDraw.arc()` (Basis grau, Füllung farbcodiert)
   - Prozent-Zahl zentriert (anchor="mm")
   - Sublabel "CLAUDE QUOTA" darüber, Reset-Zeit darunter
   - Als GIF speichern nach `frames/live.gif` (overwrite), `optimize=True`
   - Return Path
3. Edge-Cases:
   - `snapshot is None` → Render "IDLE" Frame (grau, "no active session")
   - `is_active=False` → Same wie None
4. Helper `format_time_remaining(sec: int) -> str` → "2h 14m" oder "38m" oder "< 1m"

**Output:** `src/kraken_monitor/renderer.py` (~100 LOC), `frames/live.gif` (runtime-generated, gitignored)

**Verify:**
```powershell
python -c "from kraken_monitor.renderer import render_frame; from kraken_monitor.ccusage import fetch_snapshot; from kraken_monitor.config import load_config; c=load_config(); render_frame(fetch_snapshot(), c.plan.session_token_limit, c.theme)"
# Erwartet: frames/live.gif existiert, 640x640, sieht gut aus wenn manuell geöffnet
liquidctl --match kraken set lcd screen gif frames/live.gif
# Erwartet: Live-Frame auf LCD (nicht Test-Bild)
```

**Blocked-by:** US-007, US-009

---

## Phase 3: Main-Loop

### US-010: Main-Loop mit graceful error handling

**Context:** Das Herzstück: alle `poll_interval_sec` → snapshot → render → push → sleep. Robust gegen einzelne Fehler in snapshot/render/push. Keepsrunning bis Ctrl+C.

**Input:** US-005 (KrakenDevice), US-007 (fetch_snapshot), US-008 (render_frame), US-006 (Config)

**Task:**
1. `src/kraken_monitor/loop.py` anlegen mit `run_loop(config: AppConfig) -> None`
2. Startup: `KrakenDevice()` init, CAM-Check warnen
3. Loop:
   ```
   while not stop_requested:
       try:
           snap = fetch_snapshot()
           frame_path = render_frame(snap, ...)
           kraken.push_frame(frame_path)
       except CCUsageError as e:
           log.warning("ccusage failed: %s", e)
           # kein Re-Render, alter Frame bleibt
       except liquidctl-Errors:
           log.error(...)
           reconnect_device()
       time.sleep(config.monitor.poll_interval_sec)
   ```
4. `__main__.py` ergänzen: default-Command = `run_loop`

**Output:** `src/kraken_monitor/loop.py` (~80 LOC), `__main__.py` aktualisiert

**Verify:**
```powershell
python -m kraken_monitor
# Erwartet: Log-Zeile alle 10s "pushed frame: 42% of session". LCD zeigt Live-Prozent.
# Strg+C stoppt ohne Traceback.
```

**Blocked-by:** US-005, US-007, US-008

---

### US-011: Stale-Data-Indicator + Retry-Backoff

**Context:** Wenn ccusage 3× hintereinander fehlschlägt oder Snapshot älter als 60s ist: Anzeige ausgrauen + "STALE" im Frame. Verhindert dass User einer alten Zahl traut.

**Input:** US-010 (Loop), US-007, US-008

**Task:**
1. `renderer.render_frame` um `stale: bool = False` Param erweitern — graue Desaturation auf allem
2. `loop.run_loop`: Counter `consecutive_failures`, bei ≥3 → nächster Render mit `stale=True`, Backoff-Sleep auf 30s (statt 10)
3. Bei Snapshot-Alter > 60s: ebenfalls stale
4. Recovery: erfolgreicher Snapshot → Counter = 0, Backoff zurück auf normal

**Output:** `src/kraken_monitor/loop.py` erweitert, `renderer.py` um stale-Mode

**Verify:**
```powershell
# ccusage umbenennen um Fails zu simulieren, dann
python -m kraken_monitor
# Erwartet nach 3 Fails: Graues Frame mit "STALE" Label, Log "backing off to 30s"
```

**Blocked-by:** US-010

---

## Phase 4: Qualität

### US-012: Unit-Tests für Renderer + Parser

**Context:** Vor Sprint 3 (Autostart) absichern dass Renderer + Parser deterministisch sind. Wenn Autostart läuft kann man nicht mehr debuggen — Tests fangen Regressionen.

**Input:** US-007, US-008 (Module existieren)

**Task:**
1. `tests/test_ccusage.py`: mockt subprocess-Output (fixture-JSON), verifiziert Snapshot-Parsing (happy, leer, corrupt)
2. `tests/test_renderer.py`: ruft `render_frame` mit fixture-Snapshot, prüft dass GIF entsteht + richtige Dimensions hat (`Image.open(path).size == (640,640)`)
3. `tests/fixtures/ccusage_active.json`, `tests/fixtures/ccusage_empty.json` als Test-Daten
4. `tests/test_theme.py`: `color_for_pct` Grenzwerte (59 → grün, 60 → gelb, 85 → rot)

**Output:** `tests/` Verzeichnis (~4 Test-Dateien, ~150 LOC insgesamt)

**Verify:**
```powershell
pytest -v
# Erwartet: Alle Tests grün, ≥10 Tests
```

**Blocked-by:** US-007, US-008

---

## Dependency Graph

```
US-006 ──▶ US-007 ──┬─▶ US-008 ──▶ US-010 ──▶ US-011
                    │                            
US-001 ──▶ US-009 ──┤                            
                    │
US-007,008 ─────────┴─▶ US-012
```

## Summary

| Phase | Stories | Effort |
|-------|---------|--------|
| 1: Datenquelle | US-007, US-009 | ~1h |
| 2: Rendering | US-008 | ~2h |
| 3: Main-Loop | US-010, US-011 | ~1.5h |
| 4: Qualität | US-012 | ~0.5h |
| **Total** | **6 Stories** | **~5h** |

**Done wenn:** Script läuft in Konsole, LCD zeigt Live-Prozent, `pytest` ist grün, Ctrl+C stoppt sauber.
