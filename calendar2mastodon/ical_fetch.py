"""Fetch and parse an iCalendar feed into CalendarEvent dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from icalendar import Calendar, vDatetime  # type: ignore[import-untyped]


@dataclass
class CalendarEvent:
    uid: str
    summary: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""
    all_day: bool = False


def fetch_ical(url: str, timeout: int = 15) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(parsed.path).read_bytes()
    if parsed.scheme != "https":
        raise ValueError(f"iCal URL must use https (got {parsed.scheme!r})")
    with httpx.Client(verify=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def as_aware_datetime(value: object, tz: ZoneInfo) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tz)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=tz)
    raise TypeError(f"Cannot convert {type(value)} to datetime")


def parse_ical(raw: bytes, tz: ZoneInfo) -> list[CalendarEvent]:
    cal = Calendar.from_ical(raw)
    events: list[CalendarEvent] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        uid = str(component.get("UID", ""))
        summary = str(component.get("SUMMARY", ""))
        location = str(component.get("LOCATION", ""))
        description = str(component.get("DESCRIPTION", ""))

        dt_start = component.get("DTSTART")
        dt_end = component.get("DTEND")
        if dt_start is None:
            continue

        raw_start = dt_start.dt if isinstance(dt_start, vDatetime) else dt_start.dt
        raw_end = dt_end.dt if dt_end is not None and isinstance(dt_end, vDatetime) else (dt_end.dt if dt_end else raw_start)

        all_day = isinstance(raw_start, date) and not isinstance(raw_start, datetime)
        start = as_aware_datetime(raw_start, tz)
        end = as_aware_datetime(raw_end, tz)

        events.append(
            CalendarEvent(
                uid=uid,
                summary=summary,
                start=start,
                end=end,
                location=location,
                description=description,
                all_day=all_day,
            )
        )
    return events


def load_events(url: str, tz: ZoneInfo) -> list[CalendarEvent]:
    raw = fetch_ical(url)
    return parse_ical(raw, tz)
