# Contributing

This is a personal project — small contributions and bug reports are welcome, but the scope stays narrow (NZXT Kraken 2023 + Claude Code on Windows).

## Reporting bugs

Open an issue with:
- Output of `python -m kraken_monitor status`
- Last 30 lines of `%USERPROFILE%\kraken-claude-monitor.log`
- `liquidctl --verbose list` output
- `pip show liquidctl winusbcdc pyusb pillow` versions

For driver problems: also check `docs/TROUBLESHOOTING.md` first — covers the 9 most common cases.

## Hardware-specific PRs

If you have a different Kraken model (X3, Z3, Elite, 2024 Plus), most likely:
- `_LCD_RESOLUTION` in `src/kraken_monitor/kraken.py` needs adjustment
- `_KRAKEN_PID` and possibly `_KRAKEN_WINUSB_GUID` need new values

Sketch the model + USB-Descriptor (`pyusb` enumeration output) in your PR — that's enough for triage.

## Local development

```powershell
git clone https://github.com/Felix-Hempel/kraken-claude-monitor.git
cd kraken-claude-monitor
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
python scripts/post_install.py
pytest -q
```

Run lint/format before pushing:

```powershell
ruff check src/ tests/ scripts/
ruff format src/ tests/ scripts/
```

CI runs on Windows + Python 3.11/3.12/3.13.

## Code style

- Type hints everywhere, no `Any`
- Comments only when WHY is non-obvious — code should explain WHAT
- New features need tests; aim for happy-path + at least one edge case
- Configuration via `config.local.toml` (gitignored), not env vars
- See `CLAUDE.md` for project-specific patterns and anti-patterns

## Visual changes

If you change `theme.py` or `renderer.py`:
1. Re-run `python scripts/make_screenshots.py` to refresh `docs/screenshots/`
2. Include the regenerated PNGs in your PR

## License

By contributing, you agree your changes are licensed under MIT (same as the project).
