"""Config-Loading: TOML-Defaults + optionale lokale Overrides."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MonitorConfig:
    poll_interval_sec: int = 10
    brightness_pct: int = 80
    log_level: str = "INFO"


@dataclass(frozen=True)
class PlanConfig:
    type: str = "pro"
    session_token_limit: int = 19000


@dataclass(frozen=True)
class ThemeConfig:
    """Claude-Brand-Palette (siehe `Kraken Quota Display.html`)."""

    bg_color: str = "#141413"  # Anthropic dark
    primary_color: str = "#CC785C"  # Claude Orange
    text_color: str = "#F0EEE6"  # Off-White
    muted_color: str = "#8B8680"
    warning_color: str = "#E8A87C"  # heller Orange-Ton
    danger_color: str = "#C44536"  # tiefes Rot, warm
    ok_color: str = "#5C9D4F"  # olive-grün
    track_color: str = "#26241F"  # Ring-Background (ungefüllter Teil)


@dataclass(frozen=True)
class OAuthConfig:
    enabled: bool = False


@dataclass(frozen=True)
class AppConfig:
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    plan: PlanConfig = field(default_factory=PlanConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    oauth: OAuthConfig = field(default_factory=OAuthConfig)


class ConfigError(Exception):
    pass


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Ungueltige TOML-Datei {path}: {e}") from e


def _validate_log_level(level: str) -> str:
    valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    upper = level.upper()
    if upper not in valid:
        raise ConfigError(f"log_level muss einer von {valid} sein, ist '{level}'")
    return upper


def _validate_plan_type(plan_type: str) -> str:
    valid = {"pro", "max5", "max20", "auto"}
    if plan_type not in valid:
        raise ConfigError(f"plan.type muss einer von {valid} sein, ist '{plan_type}'")
    return plan_type


def load_config(
    default_path: Path | None = None,
    local_path: Path | None = None,
) -> AppConfig:
    """Lädt config.default.toml, mergt config.local.toml darüber (wenn vorhanden)."""
    project_root = Path(__file__).resolve().parents[2]
    default_path = default_path or project_root / "config.default.toml"
    local_path = local_path or project_root / "config.local.toml"

    defaults = _load_toml(default_path)
    overrides = _load_toml(local_path)
    merged = _deep_merge(defaults, overrides)

    monitor_raw = merged.get("monitor", {})
    plan_raw = merged.get("plan", {})
    theme_raw = merged.get("theme", {})
    oauth_raw = merged.get("oauth", {})

    log_level = _validate_log_level(monitor_raw.get("log_level", "INFO"))
    plan_type = _validate_plan_type(plan_raw.get("type", "pro"))

    brightness = int(monitor_raw.get("brightness_pct", 80))
    if not 0 <= brightness <= 100:
        raise ConfigError(f"brightness_pct muss 0-100 sein, ist {brightness}")

    poll = int(monitor_raw.get("poll_interval_sec", 10))
    if poll < 1:
        raise ConfigError(f"poll_interval_sec muss >= 1 sein, ist {poll}")

    return AppConfig(
        monitor=MonitorConfig(
            poll_interval_sec=poll,
            brightness_pct=brightness,
            log_level=log_level,
        ),
        plan=PlanConfig(
            type=plan_type,
            session_token_limit=int(plan_raw.get("session_token_limit", 19000)),
        ),
        theme=ThemeConfig(**theme_raw) if theme_raw else ThemeConfig(),
        oauth=OAuthConfig(enabled=bool(oauth_raw.get("enabled", False))),
    )
