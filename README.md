# kraken-claude-monitor

[![CI](https://github.com/Felix-Hempel/kraken-claude-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Felix-Hempel/kraken-claude-monitor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](https://www.microsoft.com/windows/)
[![Tests](https://img.shields.io/badge/tests-35%20passing-brightgreen)](tests/)

> Live Claude Code quota readout on the NZXT Kraken AIO LCD.

Polls `ccusage` every 10 seconds, renders a 240×240 frame with the current 5-hour-block consumption, sends it to the Kraken pump LCD via `liquidctl`. Runs as a Windows autostart task in the background. Distinct visual states for active, over-quota, idle, paused, and stale data.

🇩🇪 [Deutsche Version](README.de.md)

![Active state — 26% of session, 2h 38m to reset](docs/screenshots/01-active.png)

## States

| Active | Over | Idle | Paused | Stale |
|--------|------|------|--------|-------|
| ![](docs/screenshots/01-active.png) | ![](docs/screenshots/02-over.png) | ![](docs/screenshots/03-idle.png) | ![](docs/screenshots/04-paused.png) | ![](docs/screenshots/05-stale.png) |
| Live consumption in 5h block | Over plan limit (≥100%) | No active session | Monitor stopped, with last update timestamp | ccusage failed 3+ times, data marked as old |

## Requirements

- **Hardware:** NZXT Kraken 2023 (USB ID `1E71:300E`) or compatible. Other Kraken models likely need adjustment of `lcd_resolution` and the WinUSB device-interface GUID — see `docs/sprint-1/WINUSBCDC-PATCH.md`.
- **OS:** Windows 11 (Windows 10 should work, untested).
- **Python:** 3.11+
- **Node.js:** 20+ (for `ccusage`)
- **Claude Code:** Pro/Max plan with active session history (otherwise nothing to display).

## Quick Start

```powershell
# 1. Clone
git clone https://github.com/Felix-Hempel/kraken-claude-monitor.git
cd kraken-claude-monitor

# 2. Virtual environment + dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

# 3. libusb DLL fix (workaround for libusb-package 1.0.26.1 on Python 3.14)
python scripts/post_install.py

# 4. Verify driver layout (typically no Zadig needed)
liquidctl list
# Expected: "Device #N: NZXT Kraken 2023"
# If empty: walk through docs/sprint-1/ZADIG-SETUP.md

# 5. Disable the Kraken LCD screen in NZXT CAM (otherwise frame conflicts)
# See docs/sprint-1/CAM-COEXISTENCE.md

# 6. Smoke test
python -m kraken_monitor status
# [OK] Config / [OK] Kraken found / Liquid temperature: ... °C

python scripts/make_test_gif.py
python -m kraken_monitor test-push frames/test.png
# Test image should appear on the LCD

# 7. Start live loop (stays in terminal until Ctrl+C)
python -m kraken_monitor

# 8. Set up autostart at login (optional)
.\install\install.ps1
```

## Configuration

`config.default.toml` ships with the repo. For personal overrides create `config.local.toml` next to it (gitignored):

```toml
[monitor]
poll_interval_sec = 10
brightness_pct = 100  # 0-100, 100 for max readability behind glass

[plan]
# "auto" uses ccusage --token-limit max (historical maximum as proxy).
# "pro" / "max5" / "max20" use a fixed session_token_limit.
type = "auto"

# Fallback when ccusage doesn't return a limit OR plan.type != "auto".
# Realistic for Pro with Opus 1M context: ~800-900 M (incl. cache reads).
session_token_limit = 850000000

[theme]
# Claude brand palette. Tweak for your own setup.
bg_color      = "#141413"
primary_color = "#CC785C"
text_color    = "#F0EEE6"
muted_color   = "#8B8680"
warning_color = "#E8A87C"
danger_color  = "#C44536"
ok_color      = "#5C9D4F"
track_color   = "#26241F"
```

## When the displayed % doesn't match your real %

ccusage's `--token-limit max` only returns your **historical maximum**, not the real plan limit. If you've never hit your cap, the monitor will read too high.

Workaround: derive your real limit from a known reading. Example: Claude Code statusline shows 26% at 220 M tokens → real limit ≈ 220M / 0.26 ≈ 845M. Put it in `config.local.toml` and set `plan.type = "pro"`.

## CLI

```
python -m kraken_monitor              # = run (default)
python -m kraken_monitor run          # main loop, 10s poll, Ctrl+C to stop
python -m kraken_monitor status       # check config + CAM + Kraken status
python -m kraken_monitor test-push P  # push a single image to the LCD (PNG/JPG/BMP)
python -m kraken_monitor version
```

## Autostart

```powershell
# One-time:
.\install\install.ps1
# Registers "Kraken Claude Monitor" in Task Scheduler (user task, no admin needed).

# Manage:
Start-ScheduledTask  -TaskName "Kraken Claude Monitor"
Stop-ScheduledTask   -TaskName "Kraken Claude Monitor"
Get-ScheduledTaskInfo -TaskName "Kraken Claude Monitor"

# Remove:
.\install\uninstall.ps1
```

Logs go to `%USERPROFILE%\kraken-claude-monitor.log` (rotating, 1 MB × 3 backups). On loop shutdown (Ctrl+C, Stop-ScheduledTask), a **PAUSED** frame with the last update timestamp is pushed to the LCD — so it's visible the monitor is no longer live.

## Architecture

```
ccusage (JSON)  →  QuotaSnapshot  →  Pillow PNG  →  liquidctl  →  Kraken LCD
   10s poll                          640×640 frame   USB (MI_00 WinUSB + MI_01 HidUsb)
```

- `src/kraken_monitor/ccusage.py` — subprocess wrapper, JSON parser, `QuotaSnapshot` dataclass
- `src/kraken_monitor/renderer.py` — Pillow render, 4 state renderers, ring + cap geometry
- `src/kraken_monitor/theme.py` — layout constants + multi-weight font loader + `color_for_pct`
- `src/kraken_monitor/kraken.py` — `liquidctl` wrapper + custom WinUSB-GUID monkey patch
- `src/kraken_monitor/loop.py` — main loop, stale backoff, reconnect, graceful shutdown
- `src/kraken_monitor/config.py` — TOML loader, dataclass validation
- `install/` — PowerShell scripts for Task Scheduler

35 tests via `pytest`.

## Tests

```powershell
pytest -q
# 35 passed
```

Tests run without hardware — `ccusage` is mocked, renderer writes to tmp paths.

## Lint & format

```powershell
ruff check  src/ tests/ scripts/
ruff format src/ tests/ scripts/
```

## Troubleshooting

See **`docs/TROUBLESHOOTING.md`** for the 9 most common cases:
- `liquidctl list` doesn't show the Kraken
- `AccessDeniedError` (CAM is blocking the HID handle)
- `AttributeError: NoneType has no write` (winusbcdc patch needed)
- Garbled "purple noise" on display (wrong `lcd_resolution`)
- LCD permanently shows 100% (plan-limit override missing)
- Task Scheduler doesn't run after login
- ...and more

## Known limitations

- **Windows-only.** liquidctl + winusbcdc + the driver-recovery docs are Windows-specific. A Linux port is possible but not planned.
- **Targets Kraken 2023 (PID `0x300E`).** Other Kraken models (X3, Z3, Elite, 2024 Plus) need `_LCD_RESOLUTION` adjustment and possibly the winusbcdc patch — see `docs/sprint-1/WINUSBCDC-PATCH.md`.
- **Plan auto-detection is an estimate.** ccusage's `tokenLimitStatus.limit` is just the historical max. For accurate readings: set `session_token_limit` in `config.local.toml`.
- **No OAuth endpoint.** Deliberately omitted (see `docs/sprint-3/USER-STORIES.md`, US-016) — fragile beta endpoint, the ccusage path is sufficient.

## Project structure

```
.
├── README.md                         ← You are here
├── README.de.md                      ← German version
├── CONTRIBUTING.md
├── LICENSE                           ← MIT
├── CLAUDE.md                         ← Project rules, stack, architecture gotchas
├── PROGRESS.md                       ← Sprint status, what's verified
├── pyproject.toml                    ← Dependencies, build config
├── config.default.toml               ← Default config
├── docs/
│   ├── VISION.md                     ← Why this tool exists
│   ├── ROADMAP.md                    ← 3-sprint plan
│   ├── TROUBLESHOOTING.md            ← 9 common errors
│   ├── design/mockups.html           ← Original design mockups
│   ├── screenshots/                  ← Demo frames for README
│   ├── sprint-1/                     ← Hardware path, drivers, patches
│   ├── sprint-2/                     ← Data pipeline, renderer
│   ├── sprint-3/                     ← Autostart, polish
│   └── progress/                     ← Debug-session notes
├── src/kraken_monitor/               ← Python package
├── tests/                            ← Pytest suite
├── scripts/                          ← post_install.py, make_test_gif.py, make_screenshots.py
├── install/                          ← PowerShell setup scripts
└── frames/                           ← Runtime output (gitignored, .gitkeep retained)
```

## Contributing

See `CONTRIBUTING.md`. Bug reports, hardware ports, and small fixes are welcome.

## License

MIT — see `LICENSE`.

## Credits

- [liquidctl](https://github.com/liquidctl/liquidctl) — open-source USB driver that talks to Kraken & friends.
- [ccusage](https://github.com/ryoppippi/ccusage) — Claude Code usage CLI.
- Anthropic — for Claude Code and the brand palette.
- NZXT — for the Kraken hardware (even if reverse-engineering the driver layer was a journey).
