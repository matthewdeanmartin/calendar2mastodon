"""Build DM message text for a reminder."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from calendar2mastodon.ical_fetch import CalendarEvent


def format_event_message(event: CalendarEvent, reminder_number: int, tz: ZoneInfo) -> str:
    local_start = event.start.astimezone(tz)
    time_str = local_start.strftime("%I:%M %p %Z").lstrip("0")
    lines = [f"Reminder {reminder_number}: {event.summary} at {time_str}"]
    if event.location:
        lines.append(f"Where: {event.location}")
    if event.description:
        lines.append(event.description[:200])
    return "\n".join(lines)


def build_message(
    event: CalendarEvent,
    reminder_number: int,
    mode: str,
    static_message: str,
    tz: ZoneInfo,
) -> str:
    if mode == "static":
        return static_message
    return format_event_message(event, reminder_number, tz)
