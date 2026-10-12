"""Post and clean up direct Mastodon reminders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

POST_TAG = "calendar2mastodon"
POST_TAG_TEXT = f"#{POST_TAG}"
DELETE_AFTER = timedelta(days=7)
CLEANUP_WINDOW = timedelta(hours=48)
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
    """Delete tagged direct reminders newly expired within the 48-hour cleanup window."""
    current_time = _as_utc(now) if now is not None else datetime.now(tz=timezone.utc)
    cutoff = current_time - DELETE_AFTER
    window_start = cutoff - CLEANUP_WINDOW
    deleted = 0
    scanned = 0

    logger.info(
        "Starting reminder cleanup: tag=%s eligible_from=%s eligible_through=%s",
        POST_TAG,
        window_start.isoformat(),
        cutoff.isoformat(),
    )
    try:
        client = _build_client(base_url, access_token)
        account = client.me()
        page = client.account_statuses(account, tagged=POST_TAG, limit=TIMELINE_PAGE_SIZE)
    except Exception:
        logger.exception("Failed to initialize reminder cleanup or fetch its first page")
        raise

    page_number = 0
    while page is not None:
        page_number += 1
        logger.info("Checking cleanup page %d containing %d tagged status(es)", page_number, len(page))
        for status in page:
            scanned += 1
            created_at = _as_utc(status.created_at)
            # Account timelines are newest-first. Once a tagged status predates
            # this run's retry window, all following statuses will too.
            if created_at < window_start:
                logger.info(
                    "Cleanup reached its 48-hour boundary after scanning %d tagged status(es); deleted=%d",
                    scanned,
                    deleted,
                )
                return deleted
            if created_at > cutoff or status.visibility != "direct":
                continue
            status_id = str(getattr(status, "id", "unknown"))
            try:
                client.status_delete(status)
            except Exception:
                logger.exception(
                    "Failed to delete reminder status id=%s created_at=%s", status_id, created_at.isoformat()
                )
                raise
            deleted += 1
            logger.info("Deleted reminder status id=%s created_at=%s", status_id, created_at.isoformat())
        try:
            page = client.fetch_next(page)
        except Exception:
            logger.exception("Failed to fetch cleanup page after page_number=%d scanned=%d", page_number, scanned)
            raise

    logger.info("Reminder cleanup completed after scanning %d tagged status(es); deleted=%d", scanned, deleted)
    return deleted
