"""Tests for config loading and merging."""

from pathlib import Path

import pytest

from calendar2mastodon.config import build_config, parse_offset


def test_defaults():
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={})
    assert cfg.mastodon_base_url == "https://mastodon.social"
    assert cfg.mastodon_username == "mistersql"
    assert cfg.reminder1_offset == "0m"
    assert cfg.reminder2_offset is None
    assert cfg.timezone == "America/New_York"


def test_cli_override_wins_over_defaults():
    cfg = build_config(
        toml_path=Path("/nonexistent/pyproject.toml"),
        cli_overrides={"timezone": "UTC", "message_mode": "static"},
    )
    assert cfg.timezone == "UTC"
    assert cfg.message_mode == "static"


def test_env_var_sets_ical_url(monkeypatch):
    monkeypatch.setenv("ICAL_URL", "https://example.com/calendar.ics")
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={})
    assert cfg.ical_url == "https://example.com/calendar.ics"


def test_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("ICAL_URL", "https://example.com/calendar.ics")
    cfg = build_config(
        toml_path=Path("/nonexistent/pyproject.toml"),
        cli_overrides={"ical_url": "https://override.example.com/cal.ics"},
    )
    assert cfg.ical_url == "https://override.example.com/cal.ics"


def test_parse_offset_none():
    assert parse_offset(None) is None


def test_parse_offset_empty_string():
    assert parse_offset("") is None


def test_parse_offset_value():
    assert parse_offset("2h") == "2h"


def test_dry_run_default_false():
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={})
    assert cfg.dry_run is False


def test_dry_run_cli():
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={"dry_run": True})
    assert cfg.dry_run is True


def test_state_file_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_path = tmp_path / "my_sent.json"
    monkeypatch.setenv("CALENDAR2MASTODON_STATE_FILE", str(state_path))
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={})
    assert cfg.state_file == state_path


def test_mastodon_access_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "secret-token")
    cfg = build_config(toml_path=Path("/nonexistent/pyproject.toml"), cli_overrides={})
    assert cfg.mastodon_access_token == "secret-token"


def test_mastodon_base_url_cli_override() -> None:
    cfg = build_config(
        toml_path=Path("/nonexistent/pyproject.toml"),
        cli_overrides={"mastodon_base_url": "https://fosstodon.org"},
    )
    assert cfg.mastodon_base_url == "https://fosstodon.org"


def test_toml_config_loaded(tmp_path: Path) -> None:
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        "[tool.calendar2mastodon]\n"
        'ical_url = "https://toml.example.com/calendar.ics"\n'
        'timezone = "Europe/London"\n'
    )
    cfg = build_config(toml_path=toml_file, cli_overrides={})
    assert cfg.ical_url == "https://toml.example.com/calendar.ics"
    assert cfg.timezone == "Europe/London"


def test_cli_overrides_toml(tmp_path: Path) -> None:
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text('[tool.calendar2mastodon]\ntimezone = "Europe/London"\n')
    cfg = build_config(toml_path=toml_file, cli_overrides={"timezone": "Asia/Tokyo"})
    assert cfg.timezone == "Asia/Tokyo"
