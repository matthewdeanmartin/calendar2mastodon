"""Compute which reminder jobs should fire on the current run."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from calendar2mastodon.ical_fetch import CalendarEvent


@dataclass
class ReminderJob:
    event: CalendarEvent
    reminder_number: int
    fire_at: datetime


def parse_offset_to_timedelta(offset: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([mhd])", offset.strip())
    if not match:
        raise ValueError(f"Invalid offset format {offset!r} — expected e.g. '0m', '2h', '1d'")
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def compute_jobs(
    events: list[CalendarEvent],
    now: datetime,
    tz: ZoneInfo,
    reminder1_offset: str | None,
    reminder2_offset: str | None,
) -> list[ReminderJob]:
    """Return ReminderJobs whose fire_at falls on today (in tz) and is <= now."""
    today = now.astimezone(tz).date()
    jobs: list[ReminderJob] = []

    for event in events:
        event_date = event.start.astimezone(tz).date()
        if event_date != today:
            continue

        offsets = [
            (1, reminder1_offset),
            (2, reminder2_offset),
        ]
        for reminder_number, offset_str in offsets:
            if offset_str is None:
                continue
            delta = parse_offset_to_timedelta(offset_str)
            if delta.total_seconds() == 0:
                # Digest mode: fire immediately at run time for any matching event today.
                jobs.append(ReminderJob(event=event, reminder_number=reminder_number, fire_at=now))
            else:
                fire_at = event.start.astimezone(timezone.utc) - delta
                if fire_at <= now:
                    jobs.append(ReminderJob(event=event, reminder_number=reminder_number, fire_at=fire_at))

    return jobs
