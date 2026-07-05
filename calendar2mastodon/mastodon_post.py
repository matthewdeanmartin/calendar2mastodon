"""Post and clean up direct Mastodon reminders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

POST_TAG = "calendar2mastodon"
POST_TAG_TEXT = f"#{POST_TAG}"
DELETE_AFTER = timedelta(days=7)
TIMELINE_PAGE_SIZE = 40


def _build_client(base_url: str, access_token: str) -> Any:
    """Create and return an authenticated Mastodon API client."""
    from mastodon import Mastodon  # pylint: disable=import-outside-toplevel

    return Mastodon(access_token=access_token, api_base_url=base_url)


def _build_dm_text(username: str, text: str) -> str:
    return f"@{username} {text}\n\n{POST_TAG_TEXT}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def post_dm(base_url: str, access_token: str, username: str, text: str) -> None:
    """Post a direct-message reminder to Mastodon."""
    client = _build_client(base_url, access_token)
    client.status_post(_build_dm_text(username, text), visibility="direct")


def cleanup_old_posts(base_url: str, access_token: str, now: datetime | None = None) -> int:
    """Delete tagged direct-message reminders that are at least one week old."""
    client = _build_client(base_url, access_token)
    current_time = now if now is not None else datetime.now(tz=timezone.utc)
    cutoff = current_time - DELETE_AFTER

    account = client.me()
    page = client.account_statuses(account, tagged=POST_TAG, limit=TIMELINE_PAGE_SIZE)
    deleted = 0

    while page is not None:
        for status in page:
            created_at = _as_utc(status.created_at)
            if created_at > cutoff or status.visibility != "direct":
                continue
            client.status_delete(status)
            deleted += 1
        page = client.fetch_next(page)

    return deleted
