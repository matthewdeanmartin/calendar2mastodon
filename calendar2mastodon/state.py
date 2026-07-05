"""Track which reminders have already been sent to avoid duplicates."""

from __future__ import annotations

import json
from pathlib import Path

SentKey = tuple[str, int, str]  # (event_uid, reminder_number, date_str)


def load_sent(path: Path) -> set[SentKey]:
    """Load the set of already-sent reminder keys from the state file."""
    if not path.is_file():
        return set()
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {(item[0], int(item[1]), item[2]) for item in raw}


def save_sent(path: Path, sent: set[SentKey]) -> None:
    """Persist the sent-reminder keys to the state file (creates parent dirs if needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([[uid, num, date_str] for uid, num, date_str in sorted(sent)], fh, indent=2)


def make_key(uid: str, reminder_number: int, date_str: str) -> SentKey:
    """Build a deduplification key from event UID, reminder number, and date."""
    return (uid, reminder_number, date_str)
