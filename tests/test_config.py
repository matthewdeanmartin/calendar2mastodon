"""Tests for config loading and merging."""

import os
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
