"""Tests for legacy reminder backfill cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO
from types import SimpleNamespace
from typing import Any

import pytest

from calendar2mastodon import legacy_cleanup


class FakeClient:
    """Minimal paginated Mastodon client."""

    def __init__(self, pages: list[list[Any]]) -> None:
        self.pages = pages
        self.page_index = 0
        self.deleted: list[str] = []

    def me(self) -> str:
        return "self"

    def account_statuses(self, account: object, limit: int) -> list[Any]:
        assert account == "self"
        assert limit == 40
        return self.pages[0]

    def fetch_next(self, _page: list[Any]) -> list[Any] | None:
        self.page_index += 1
        return self.pages[self.page_index] if self.page_index < len(self.pages) else None

    def status_delete(self, deleted_status: Any) -> None:
        self.deleted.append(deleted_status.id)


def status(status_id: str, created_at: datetime, visibility: str, content: str) -> Any:
    return SimpleNamespace(id=status_id, created_at=created_at, visibility=visibility, content=content)


def test_find_legacy_reminders_matches_only_old_direct_app_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    old = now - timedelta(days=30)
    pages = [
        [
            status("legacy", old, "direct", "<p>@mistersql Reminder 1: Dentist at 2:00 PM</p>"),
            status("unrelated", old, "direct", "<p>@mistersql lunch sometime?</p>"),
            status("public", old, "public", "<p>Reminder 1: public post</p>"),
        ],
        [
            status("tagged", old + timedelta(days=1), "direct", "<p>Hey, check your calendar! #calendar2mastodon</p>"),
            status("recent", now - timedelta(days=2), "direct", "<p>Reminder 2: recent</p>"),
        ],
    ]
    client = FakeClient(pages)
    monkeypatch.setattr(legacy_cleanup, "_build_client", lambda _url, _token: client)

    returned_client, candidates, scan_complete = legacy_cleanup.find_legacy_reminders(
        "https://mastodon.social", "token", "mistersql", "Hey, check your calendar!", now=now
    )

    assert returned_client is client
    assert scan_complete
    assert [candidate.status_id for candidate in candidates] == ["tagged", "legacy"]
    assert candidates[1].text == "@mistersql Reminder 1: Dentist at 2:00 PM"


def test_plain_text_decodes_status_html() -> None:
    assert legacy_cleanup._plain_text("<p>Hello &amp; <strong>goodbye</strong></p>") == "Hello & goodbye"


def test_find_legacy_reminders_can_stop_after_preview_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    old = now - timedelta(days=30)
    client = FakeClient(
        [
            [
                status("first", old, "direct", "<p>@mistersql Reminder 1: First</p>"),
                status("second", old - timedelta(days=1), "direct", "<p>@mistersql Reminder 1: Second</p>"),
            ]
        ]
    )
    monkeypatch.setattr(legacy_cleanup, "_build_client", lambda _url, _token: client)

    _, candidates, scan_complete = legacy_cleanup.find_legacy_reminders(
        "https://mastodon.social",
        "token",
        "mistersql",
        "Hey, check your calendar!",
        now=now,
        max_candidates=1,
    )

    assert [candidate.status_id for candidate in candidates] == ["first"]
    assert not scan_complete


def test_delete_legacy_reminders_flushes_each_deletion(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    old = now - timedelta(days=30)
    client = FakeClient(
        [
            [
                status("first", old, "direct", "<p>@mistersql Reminder 1: First</p>"),
                status("unrelated", old, "direct", "<p>@mistersql hello</p>"),
            ]
        ]
    )
    monkeypatch.setattr(legacy_cleanup, "_build_client", lambda _url, _token: client)
    output = StringIO()

    deleted = legacy_cleanup.delete_legacy_reminders(
        "https://mastodon.social",
        "token",
        "mistersql",
        "Hey, check your calendar!",
        now=now,
        output=output,
    )

    assert deleted == 1
    assert client.deleted == ["first"]
    assert "Deleting id=first" in output.getvalue()
    assert "Deleted id=first; deleted_total=1" in output.getvalue()
    assert "Progress: scanned=2 deleted=1" in output.getvalue()


def test_delete_stops_when_timeline_crosses_may_25_lower_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    client = FakeClient(
        [
            [
                status(
                    "in-window",
                    datetime(2026, 5, 25, tzinfo=UTC),
                    "direct",
                    "<p>@mistersql Reminder 1: Keep</p>",
                ),
                status(
                    "too-old",
                    datetime(2026, 5, 24, tzinfo=UTC),
                    "direct",
                    "<p>@mistersql Reminder 1: Stop</p>",
                ),
            ],
            [
                status(
                    "never-read",
                    datetime(2026, 5, 23, tzinfo=UTC),
                    "direct",
                    "<p>@mistersql Reminder 1: Stop</p>",
                )
            ],
        ]
    )
    monkeypatch.setattr(legacy_cleanup, "_build_client", lambda _url, _token: client)
    output = StringIO()

    deleted = legacy_cleanup.delete_legacy_reminders(
        "https://mastodon.social",
        "token",
        "mistersql",
        "Hey, check your calendar!",
        now=now,
        output=output,
    )

    assert deleted == 1
    assert client.deleted == ["in-window"]
    assert client.page_index == 0
    assert "Reached lower bound 2026-05-25T00:00:00+00:00" in output.getvalue()
