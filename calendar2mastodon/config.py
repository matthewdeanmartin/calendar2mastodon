"""Load and merge configuration from pyproject.toml, environment variables, and CLI args."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]


TOOL_KEY = "calendar2mastodon"

DEFAULTS: dict[str, object] = {
    "ical_url": "",
    "mastodon_base_url": "https://mastodon.social",
    "mastodon_username": "mistersql",
    "reminder1_offset": "0m",
    "reminder2_offset": None,
    "message_mode": "event",
    "static_message": "Hey, check your calendar!",
    "timezone": "America/New_York",
    "lookahead_window": "1d",
}

ENV_MAP: dict[str, str] = {
    "ical_url": "ICAL_URL",
    "mastodon_base_url": "MASTODON_BASE_URL",
    "mastodon_access_token": "MASTODON_ACCESS_TOKEN",
}


@dataclass
class AppConfig:
    ical_url: str = ""
    mastodon_base_url: str = "https://mastodon.social"
    mastodon_username: str = "mistersql"
    mastodon_access_token: str = ""
    reminder1_offset: str | None = "0m"
    reminder2_offset: str | None = None
    message_mode: str = "event"
    static_message: str = "Hey, check your calendar!"
    timezone: str = "America/New_York"
    lookahead_window: str = "1d"
    state_file: Path = field(default_factory=lambda: Path.home() / ".cache" / "calendar2mastodon" / "sent.json")
    dry_run: bool = False


def find_pyproject_toml(start: Path) -> Path | None:
    """Walk up from start looking for pyproject.toml."""
    for parent in [start, *start.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_toml_config(path: Optional[Path]) -> dict[str, object]:
    if path is None:
        path = find_pyproject_toml(Path.cwd())
    if path is None or not path.is_file():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("tool", {}).get(TOOL_KEY, {})  # type: ignore[return-value]


def parse_offset(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return None if s == "" else s


def build_config(
    toml_path: Path | None = None,
    cli_overrides: dict[str, object] | None = None,
) -> AppConfig:
    toml = load_toml_config(toml_path)

    def get(key: str) -> object:
        if cli_overrides and key in cli_overrides and cli_overrides[key] is not None:
            return cli_overrides[key]
        env_var = ENV_MAP.get(key)
        if env_var:
            env_val = os.environ.get(env_var)
            if env_val is not None:
                return env_val
        if key in toml:
            return toml[key]
        return DEFAULTS.get(key)

    state_file_raw = (
        (cli_overrides or {}).get("state_file")
        or os.environ.get("CALENDAR2MASTODON_STATE_FILE")
        or str(Path.home() / ".cache" / "calendar2mastodon" / "sent.json")
    )

    return AppConfig(
        ical_url=str(get("ical_url") or ""),
        mastodon_base_url=str(get("mastodon_base_url") or "https://mastodon.social"),
        mastodon_username=str(get("mastodon_username") or "mistersql"),
        mastodon_access_token=str(os.environ.get("MASTODON_ACCESS_TOKEN") or ""),
        reminder1_offset=parse_offset(get("reminder1_offset")),
        reminder2_offset=parse_offset(get("reminder2_offset")),
        message_mode=str(get("message_mode") or "event"),
        static_message=str(get("static_message") or "Hey, check your calendar!"),
        timezone=str(get("timezone") or "America/New_York"),
        lookahead_window=str(get("lookahead_window") or "1d"),
        state_file=Path(str(state_file_raw)),
        dry_run=bool((cli_overrides or {}).get("dry_run", False)),
    )
