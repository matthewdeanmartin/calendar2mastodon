"""Tests for Mastodon posting and cleanup."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import ClassVar

import pytest

from calendar2mastodon import mastodon_post


class FakeStatus:
    """Minimal fake Mastodon status."""

    def __init__(self, created_at: datetime, visibility: str) -> None:
        self.created_at = created_at
        self.visibility = visibility


class FakeMastodon:
    """Minimal fake Mastodon client."""

    pages: ClassVar[list[list[FakeStatus] | None]] = []
    last_instance: ClassVar[FakeMastodon | None] = None

    def __init__(self, *, access_token: str, api_base_url: str) -> None:
        self.access_token = access_token
        self.api_base_url = api_base_url
        self.posted: tuple[str, str] | None = None
        self.deleted: list[FakeStatus] = []
        self.account_statuses_args: tuple[object, str, int] | None = None
        self.fetch_count = 0
        FakeMastodon.last_instance = self

    def status_post(self, text: str, visibility: str) -> None:
        self.posted = (text, visibility)

    def me(self) -> str:
        return "self-account"

    def account_statuses(self, account: object, tagged: str, limit: int) -> list[FakeStatus] | None:
        self.account_statuses_args = (account, tagged, limit)
        return self.pages[0] if self.pages else None

    def fetch_next(self, _page: list[FakeStatus]) -> list[FakeStatus] | None:
        self.fetch_count += 1
        return self.pages[self.fetch_count] if self.fetch_count < len(self.pages) else None

    def status_delete(self, status: FakeStatus) -> None:
        self.deleted.append(status)


def install_fake_mastodon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "mastodon", SimpleNamespace(Mastodon=FakeMastodon))


def test_post_dm_mentions_self_and_tags_message(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mastodon(monkeypatch)

    mastodon_post.post_dm("https://mastodon.social", "token", "mistersql", "Calendar says hello")

    instance = FakeMastodon.last_instance
    assert instance is not None
    assert instance.posted == (
        "@mistersql Calendar says hello\n\n#calendar2mastodon",
        "direct",
    )


def test_cleanup_old_posts_only_deletes_direct_tagged_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mastodon(monkeypatch)
    now = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    old_direct = FakeStatus(now - timedelta(days=8), "direct")
    old_public = FakeStatus(now - timedelta(days=8), "public")
    recent_direct = FakeStatus(now - timedelta(days=2), "direct")
    FakeMastodon.pages = [[recent_direct, old_public], [old_direct]]

    deleted = mastodon_post.cleanup_old_posts("https://mastodon.social", "token", now=now)

    instance = FakeMastodon.last_instance
    assert instance is not None
    assert deleted == 1
    assert instance.account_statuses_args == ("self-account", "calendar2mastodon", 40)
    assert instance.deleted == [old_direct]


def test_cleanup_no_posts_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mastodon(monkeypatch)
    FakeMastodon.pages = [[]]
    deleted = mastodon_post.cleanup_old_posts("https://mastodon.social", "token")
    assert deleted == 0


def test_cleanup_empty_first_page(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mastodon(monkeypatch)
    FakeMastodon.pages = [None]
    deleted = mastodon_post.cleanup_old_posts("https://mastodon.social", "token")
    assert deleted == 0


def test_build_dm_text_format() -> None:
    text = mastodon_post._build_dm_text("alice", "Hello there")
    assert text == "@alice Hello there\n\n#calendar2mastodon"


def test_as_utc_naive_datetime() -> None:
    naive = datetime(2026, 5, 20, 12, 0)
    result = mastodon_post._as_utc(naive)
    assert result.tzinfo == timezone.utc
    assert result.hour == 12


def test_as_utc_aware_datetime() -> None:
    aware = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    result = mastodon_post._as_utc(aware)
    assert result == aware
