"""Tests for reminder job computation."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from calendar2mastodon.ical_fetch import CalendarEvent
from calendar2mastodon.reminder import compute_jobs, parse_offset_to_timedelta
from datetime import timedelta


NY = ZoneInfo("America/New_York")


def make_event(uid: str, hour: int, minute: int = 0) -> CalendarEvent:
    start = datetime(2026, 5, 20, hour, minute, tzinfo=NY)
    return CalendarEvent(uid=uid, summary="Test Event", start=start, end=start, location="", description="")


def test_parse_offset_minutes():
    assert parse_offset_to_timedelta("30m") == timedelta(minutes=30)


def test_parse_offset_hours():
    assert parse_offset_to_timedelta("2h") == timedelta(hours=2)


def test_parse_offset_days():
    assert parse_offset_to_timedelta("1d") == timedelta(days=1)


def test_parse_offset_zero():
    assert parse_offset_to_timedelta("0m") == timedelta(0)


def test_parse_offset_invalid():
    with pytest.raises(ValueError):
        parse_offset_to_timedelta("bad")


def test_digest_fires_for_todays_events():
    now = datetime(2026, 5, 20, 11, 30, tzinfo=timezone.utc)  # 6:30am EST
    event = make_event("uid-1", 9, 0)  # 9am today
    jobs = compute_jobs([event], now, NY, "0m", None)
    assert len(jobs) == 1
    assert jobs[0].reminder_number == 1
    assert jobs[0].event.uid == "uid-1"


def test_no_jobs_for_future_date():
    now = datetime(2026, 5, 20, 11, 30, tzinfo=timezone.utc)
    event = make_event("uid-2", 9)
    # Change event to tomorrow
    from datetime import date
    tomorrow = datetime(2026, 5, 21, 9, 0, tzinfo=NY)
    event.start = tomorrow
    event.end = tomorrow
    jobs = compute_jobs([event], now, NY, "0m", None)
    assert jobs == []


def test_second_reminder_included():
    # Event at 2pm EDT = 18:00 UTC. Reminder2 "2h before" fires at 16:00 UTC.
    # now = 17:00 UTC, which is after 16:00, so both reminders should fire.
    now = datetime(2026, 5, 20, 17, 0, tzinfo=timezone.utc)
    event = make_event("uid-3", 14, 0)
    jobs = compute_jobs([event], now, NY, "0m", "2h")
    reminder_numbers = {j.reminder_number for j in jobs}
    assert 1 in reminder_numbers
    assert 2 in reminder_numbers


def test_second_reminder_disabled():
    now = datetime(2026, 5, 20, 11, 30, tzinfo=timezone.utc)
    event = make_event("uid-4", 14, 0)
    jobs = compute_jobs([event], now, NY, "0m", None)
    assert all(j.reminder_number == 1 for j in jobs)
