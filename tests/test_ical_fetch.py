"""Tests for iCal fetching and parsing."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from calendar2mastodon.ical_fetch import as_aware_datetime, fetch_ical, parse_ical

NY = ZoneInfo("America/New_York")
UTC = timezone.utc

# ---------------------------------------------------------------------------
# as_aware_datetime
# ---------------------------------------------------------------------------


def test_aware_datetime_passes_through_with_utc_normalisation():
    dt = datetime(2026, 5, 20, 14, 0, tzinfo=UTC)
    result = as_aware_datetime(dt, NY)
    assert result == dt.astimezone(UTC)
    assert result.tzinfo is not None


def test_naive_datetime_gets_tz_attached():
    naive = datetime(2026, 5, 20, 9, 0)
    result = as_aware_datetime(naive, NY)
    assert result.tzinfo == NY
    assert result.year == 2026
    assert result.hour == 9


def test_date_object_becomes_midnight_in_tz():
    d = date(2026, 5, 20)
    result = as_aware_datetime(d, NY)
    assert result.tzinfo == NY
    assert result.hour == 0
    assert result.minute == 0
    assert result.date() == d


def test_unsupported_type_raises():
    with pytest.raises(TypeError):
        as_aware_datetime("2026-05-20", NY)


# ---------------------------------------------------------------------------
# fetch_ical — file:// scheme
# ---------------------------------------------------------------------------


def test_fetch_ical_reads_local_file(tmp_path: Path) -> None:
    content = b"BEGIN:VCALENDAR\nEND:VCALENDAR\n"
    ics_file = tmp_path / "test.ics"
    ics_file.write_bytes(content)
    url = ics_file.as_uri()
    result = fetch_ical(url)
    assert result == content


def test_fetch_ical_rejects_http():
    with pytest.raises(ValueError, match="https"):
        fetch_ical("http://example.com/calendar.ics")


def test_fetch_ical_rejects_ftp():
    with pytest.raises(ValueError, match="https"):
        fetch_ical("ftp://example.com/calendar.ics")


# ---------------------------------------------------------------------------
# parse_ical
# ---------------------------------------------------------------------------

_BASIC_ICAL = b"""\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-uid-1@example.com
SUMMARY:Morning Run
DTSTART;TZID=America/New_York:20260520T090000
DTEND;TZID=America/New_York:20260520T100000
LOCATION:Central Park
DESCRIPTION:5K warm-up run
END:VEVENT
END:VCALENDAR
"""

_ALL_DAY_ICAL = b"""\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:allday-uid@example.com
SUMMARY:Rest Day
DTSTART;VALUE=DATE:20260520
DTEND;VALUE=DATE:20260521
END:VEVENT
END:VCALENDAR
"""

_NO_DTEND_ICAL = b"""\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:nodtend-uid@example.com
SUMMARY:Quick Note
DTSTART;TZID=America/New_York:20260520T150000
END:VEVENT
END:VCALENDAR
"""

_NO_DTSTART_ICAL = b"""\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:nodtstart@example.com
SUMMARY:Broken Event
END:VEVENT
END:VCALENDAR
"""


def test_parse_ical_basic_event():
    events = parse_ical(_BASIC_ICAL, NY)
    assert len(events) == 1
    e = events[0]
    assert e.uid == "test-uid-1@example.com"
    assert e.summary == "Morning Run"
    assert e.location == "Central Park"
    assert e.description == "5K warm-up run"
    assert e.all_day is False
    assert e.start.tzinfo is not None


def test_parse_ical_all_day_event():
    events = parse_ical(_ALL_DAY_ICAL, NY)
    assert len(events) == 1
    e = events[0]
    assert e.all_day is True
    assert e.start.hour == 0
    assert e.start.tzinfo == NY


def test_parse_ical_no_dtend_uses_dtstart():
    events = parse_ical(_NO_DTEND_ICAL, NY)
    assert len(events) == 1
    e = events[0]
    assert e.start == e.end


def test_parse_ical_skips_event_without_dtstart():
    events = parse_ical(_NO_DTSTART_ICAL, NY)
    assert events == []


def test_parse_ical_empty_calendar():
    raw = b"BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n"
    events = parse_ical(raw, NY)
    assert events == []


def test_parse_ical_multiple_events():
    raw = b"""\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:ev-1@ex.com
SUMMARY:Event One
DTSTART;TZID=America/New_York:20260520T090000
DTEND;TZID=America/New_York:20260520T100000
END:VEVENT
BEGIN:VEVENT
UID:ev-2@ex.com
SUMMARY:Event Two
DTSTART;TZID=America/New_York:20260520T140000
DTEND;TZID=America/New_York:20260520T150000
END:VEVENT
END:VCALENDAR
"""
    events = parse_ical(raw, NY)
    assert len(events) == 2
    uids = {e.uid for e in events}
    assert uids == {"ev-1@ex.com", "ev-2@ex.com"}
