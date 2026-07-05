"""Tests for message building."""

from datetime import datetime
from zoneinfo import ZoneInfo

from calendar2mastodon.ical_fetch import CalendarEvent
from calendar2mastodon.message import build_message, format_event_message

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


def test_event_mode_includes_description():
    event = make_event("Track", 8, description="Bring your spikes")
    msg = build_message(event, 1, "event", "", NY)
    assert "Bring your spikes" in msg


def test_event_mode_no_description_when_empty():
    event = make_event("Track", 8)
    msg = build_message(event, 1, "event", "", NY)
    # message should only have the one-line header
    assert msg.count("\n") == 0


def test_event_mode_truncates_long_description():
    long_desc = "x" * 300
    event = make_event("Ultra", 6, description=long_desc)
    msg = build_message(event, 1, "event", "", NY)
    assert "x" * 201 not in msg  # at most 200 x's appear
    assert "x" * 200 in msg


def test_format_event_message_midnight_no_leading_zero():
    event = make_event("Dawn event", 0, 0)
    msg = format_event_message(event, 1, NY)
    # strftime gives "12:00 AM"; lstrip("0") should not corrupt it
    assert "12:00" in msg


def test_format_event_message_noon():
    event = make_event("Lunch", 12, 0)
    msg = format_event_message(event, 1, NY)
    assert "12:00" in msg
    assert "PM" in msg
