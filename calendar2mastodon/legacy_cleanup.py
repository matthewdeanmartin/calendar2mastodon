"""Preview and delete legacy calendar reminder direct messages."""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, TextIO

from calendar2mastodon.config import build_config
from calendar2mastodon.mastodon_post import DELETE_AFTER, POST_TAG, TIMELINE_PAGE_SIZE, _as_utc, _build_client

__all__ = ["CleanupCandidate", "delete_legacy_reminders", "find_legacy_reminders", "main"]

REMINDER_PATTERN = re.compile(r"(?:^|\s)Reminder [12]:\s", re.IGNORECASE)
DEFAULT_SINCE = datetime(2026, 5, 25, tzinfo=UTC)


class _TextExtractor(HTMLParser):
    """Extract readable text from Mastodon's status HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Collect text nodes."""
        self.parts.append(data)


@dataclass(frozen=True)
class CleanupCandidate:
    """A direct status positively identified as an old app reminder."""

    status: Any
    status_id: str
    created_at: datetime
    text: str


def _plain_text(content: str) -> str:
    parser = _TextExtractor()
    parser.feed(content)
    return " ".join(html.unescape("".join(parser.parts)).split())


def _is_app_reminder(text: str, username: str, static_message: str) -> bool:
    """Return whether text has a current or legacy app reminder signature."""
    folded_text = text.casefold()
    if f"#{POST_TAG}".casefold() in folded_text:
        return True
    self_mention = f"@{username.casefold()} "
    if not folded_text.startswith(self_mention):
        return False
    message = text[len(self_mention) :]
    return bool(REMINDER_PATTERN.match(message)) or bool(static_message and message.startswith(static_message))


def find_legacy_reminders(
    base_url: str,
    access_token: str,
    username: str,
    static_message: str,
    *,
    now: datetime | None = None,
    since: datetime = DEFAULT_SINCE,
    max_candidates: int | None = None,
) -> tuple[Any, list[CleanupCandidate], bool]:
    """Return the API client and old direct statuses matching this app's output."""
    client = _build_client(base_url, access_token)
    cutoff = (now if now is not None else datetime.now(tz=UTC)) - DELETE_AFTER
    account = client.me()
    page = client.account_statuses(account, limit=TIMELINE_PAGE_SIZE)
    candidates: list[CleanupCandidate] = []

    while page is not None:
        for status in page:
            created_at = _as_utc(status.created_at)
            if created_at < since:
                candidates.sort(key=lambda candidate: candidate.created_at, reverse=True)
                return client, candidates, True
            text = _plain_text(str(status.content))
            if (
                created_at > cutoff
                or status.visibility != "direct"
                or not _is_app_reminder(text, username, static_message)
            ):
                continue
            candidates.append(
                CleanupCandidate(status=status, status_id=str(status.id), created_at=created_at, text=text)
            )
            if max_candidates is not None and len(candidates) >= max_candidates:
                candidates.sort(key=lambda candidate: candidate.created_at, reverse=True)
                return client, candidates, False
        page = client.fetch_next(page)

    candidates.sort(key=lambda candidate: candidate.created_at, reverse=True)
    return client, candidates, True


def delete_legacy_reminders(
    base_url: str,
    access_token: str,
    username: str,
    static_message: str,
    *,
    now: datetime | None = None,
    since: datetime = DEFAULT_SINCE,
    output: TextIO = sys.stdout,
) -> int:
    """Delete matching reminders as they are scanned, flushing progress after each one."""
    client = _build_client(base_url, access_token)
    cutoff = (now if now is not None else datetime.now(tz=UTC)) - DELETE_AFTER
    account = client.me()
    page = client.account_statuses(account, limit=TIMELINE_PAGE_SIZE)
    scanned = 0
    deleted = 0

    while page is not None:
        for status in page:
            scanned += 1
            created_at = _as_utc(status.created_at)
            if created_at < since:
                print(
                    f"Reached lower bound {since.isoformat()}; scanned={scanned} deleted={deleted}",
                    file=output,
                    flush=True,
                )
                print(f"Deleted {deleted} old direct reminder post(s).", file=output, flush=True)
                return deleted
            text = _plain_text(str(status.content))
            if (
                created_at > cutoff
                or status.visibility != "direct"
                or not _is_app_reminder(text, username, static_message)
            ):
                continue
            status_id = str(status.id)
            print(f"Deleting id={status_id} created_at={created_at.isoformat()}", file=output, flush=True)
            try:
                client.status_delete(status)
            except Exception as exc:
                print(f"FAILED id={status_id}: {type(exc).__name__}: {exc}", file=output, flush=True)
                raise
            deleted += 1
            print(f"Deleted id={status_id}; deleted_total={deleted}", file=output, flush=True)
        print(f"Progress: scanned={scanned} deleted={deleted}", file=output, flush=True)
        page = client.fetch_next(page)

    print(f"Deleted {deleted} old direct reminder post(s).", file=output, flush=True)
    return deleted


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or delete old calendar2mastodon direct messages.")
    parser.add_argument("--delete", action="store_true", help="Delete all matches; the default is preview only")
    parser.add_argument("--limit", type=int, default=10, help="Number of matches to print (default: 10)")
    return parser


def main() -> None:
    """Run the legacy reminder cleanup command."""
    args = _parser().parse_args()
    if args.limit < 1:
        raise SystemExit("ERROR: --limit must be at least 1")

    config = build_config()
    if not config.mastodon_access_token:
        raise SystemExit("ERROR: MASTODON_ACCESS_TOKEN environment variable is required")

    if args.delete:
        delete_legacy_reminders(
            config.mastodon_base_url,
            config.mastodon_access_token,
            config.mastodon_username,
            config.static_message,
        )
        return

    _, candidates, scan_complete = find_legacy_reminders(
        config.mastodon_base_url,
        config.mastodon_access_token,
        config.mastodon_username,
        config.static_message,
        max_candidates=args.limit,
    )
    count = str(len(candidates)) if scan_complete else f"at least {len(candidates)}"
    print(f"Found {count} old direct reminder post(s). Would delete all matches.")
    print(f"Showing newest {min(args.limit, len(candidates))} match(es):")
    for candidate in candidates[: args.limit]:
        print(f"- {candidate.created_at.isoformat()} id={candidate.status_id}: {candidate.text}")
    print("Preview only; nothing was deleted. Re-run with --delete after reviewing the sample.")


if __name__ == "__main__":
    main()
