"""Tests for message building."""

from datetime import datetime
from zoneinfo import ZoneInfo

from calendar2mastodon.ical_fetch import CalendarEvent
from calendar2mastodon.message import build_message

NY = ZoneInfo("America/New_York")


def make_event(summary: str, hour: int, minute: int = 0, location: str = "", description: str = "") -> CalendarEvent:
    start = datetime(2026, 5, 20, hour, minute, tzinfo=NY)
    return CalendarEvent(uid="x", summary=summary, start=start, end=start, location=location, description=description)


def test_static_mode_returns_static_message():
    event = make_event("Swim 5K", 9)
    msg = build_message(event, 1, "static", "Hey, check your calendar!", NY)
    assert msg == "Hey, check your calendar!"


def test_event_mode_includes_summary():
    event = make_event("Swim 5K", 9)
    msg = build_message(event, 1, "event", "", NY)
    assert "Swim 5K" in msg


def test_event_mode_includes_time():
    event = make_event("Morning Run", 7, 30)
    msg = build_message(event, 1, "event", "", NY)
    assert "7:30" in msg


def test_event_mode_includes_location():
    event = make_event("Race", 8, location="Central Park")
    msg = build_message(event, 1, "event", "", NY)
    assert "Central Park" in msg


def test_event_mode_includes_reminder_number():
    event = make_event("Bike ride", 10)
    msg = build_message(event, 2, "event", "", NY)
    assert "2" in msg


def test_event_mode_no_location_when_empty():
    event = make_event("Swim", 6)
    msg = build_message(event, 1, "event", "", NY)
    assert "Where:" not in msg
