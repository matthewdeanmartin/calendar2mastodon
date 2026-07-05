"""Smoke tests for the CLI entry point."""

from pathlib import Path

import pytest

from calendar2mastodon.cli import run
from calendar2mastodon.config import AppConfig


def test_import() -> None:
    """Package can be imported."""
    import calendar2mastodon  # noqa: F401


def test_version() -> None:
    """Package exposes a version string."""
    from calendar2mastodon.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_run_cleans_up_even_when_no_new_reminders(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    import calendar2mastodon.cli as cli
    import calendar2mastodon.mastodon_post as mastodon_post

    monkeypatch.setattr(cli, "load_events", lambda _url, _tz: [])
    monkeypatch.setattr(mastodon_post, "cleanup_old_posts", lambda _base_url, _token, now=None: 2)

    config = AppConfig(
        ical_url="https://example.com/calendar.ics",
        mastodon_access_token="token",
        state_file=tmp_path / "sent.json",
    )

    result = run(config)

    captured = capsys.readouterr()
    assert result == 0
    assert "Deleted 2 old reminder post(s)." in captured.out
    assert "No reminders to send." in captured.out


def test_run_errors_without_ical_url(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    config = AppConfig(ical_url="", mastodon_access_token="token", state_file=tmp_path / "sent.json")
    result = run(config)
    assert result == 1
    assert "iCal URL" in capsys.readouterr().err


def test_run_errors_without_access_token(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    config = AppConfig(
        ical_url="https://example.com/calendar.ics",
        mastodon_access_token="",
        dry_run=False,
        state_file=tmp_path / "sent.json",
    )
    result = run(config)
    assert result == 1
    assert "MASTODON_ACCESS_TOKEN" in capsys.readouterr().err


def test_run_errors_on_invalid_timezone(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    config = AppConfig(
        ical_url="https://example.com/calendar.ics",
        mastodon_access_token="token",
        timezone="Not/A/Real/Timezone",
        state_file=tmp_path / "sent.json",
    )
    result = run(config)
    assert result == 1
    assert "timezone" in capsys.readouterr().err.lower()


def test_run_errors_on_ical_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    import calendar2mastodon.cli as cli
    import calendar2mastodon.mastodon_post as mastodon_post

    monkeypatch.setattr(cli, "load_events", lambda _url, _tz: (_ for _ in ()).throw(ValueError("bad url")))
    monkeypatch.setattr(mastodon_post, "cleanup_old_posts", lambda *_a, **_kw: 0)

    config = AppConfig(
        ical_url="https://example.com/calendar.ics",
        mastodon_access_token="token",
        state_file=tmp_path / "sent.json",
    )
    result = run(config)
    assert result == 1
    assert "bad url" in capsys.readouterr().err


def test_run_dry_run_does_not_require_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    import calendar2mastodon.cli as cli

    monkeypatch.setattr(cli, "load_events", lambda _url, _tz: [])

    config = AppConfig(
        ical_url="https://example.com/calendar.ics",
        mastodon_access_token="",
        dry_run=True,
        state_file=tmp_path / "sent.json",
    )
    result = run(config)
    assert result == 0
