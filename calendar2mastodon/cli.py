"""Command-line entry point for calendar2mastodon."""

from __future__ import annotations

import argparse
import sys
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from calendar2mastodon.__about__ import __version__
from calendar2mastodon.config import AppConfig, build_config
from calendar2mastodon.ical_fetch import load_events
from calendar2mastodon.message import build_message
from calendar2mastodon.reminder import compute_jobs
from calendar2mastodon.state import load_sent, make_key, save_sent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calendar2mastodon",
        description="Post today's calendar events to Mastodon as DMs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--ical-url", metavar="URL", help="iCal feed URL (overrides config/env)")
    parser.add_argument("--mastodon-base-url", metavar="URL", help="Mastodon instance base URL")
    parser.add_argument("--mastodon-username", metavar="USER", help="Your Mastodon username (without @)")
    parser.add_argument("--reminder1-offset", metavar="OFFSET", help="Offset for reminder 1 (e.g. '0m', '1h', '1d')")
    parser.add_argument("--reminder2-offset", metavar="OFFSET", help="Offset for reminder 2 (or 'none' to disable)")
    parser.add_argument("--message-mode", choices=["static", "event"], help="Message content mode")
    parser.add_argument("--static-message", metavar="TEXT", help="Text to use in static mode")
    parser.add_argument("--timezone", metavar="TZ", help="IANA timezone name (e.g. 'America/New_York')")
    parser.add_argument("--lookahead-window", metavar="WINDOW", help="How far ahead to scan (e.g. '1d')")
    parser.add_argument("--state-file", metavar="PATH", type=Path, help="Path to sent-reminders state file")
    parser.add_argument("--config", metavar="FILE", type=Path, help="Path to pyproject.toml config file")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be posted without sending")
    return parser


def run(config: AppConfig) -> int:
    from datetime import datetime as dt

    if not config.ical_url:
        print("ERROR: iCal URL is required (set ICAL_URL env var or ical_url in pyproject.toml)", file=sys.stderr)
        return 1

    if not config.dry_run and not config.mastodon_access_token:
        print("ERROR: MASTODON_ACCESS_TOKEN environment variable is required", file=sys.stderr)
        return 1

    try:
        tz = ZoneInfo(config.timezone)
    except Exception:
        print(f"ERROR: Unknown timezone {config.timezone!r}", file=sys.stderr)
        return 1

    now = dt.now(tz=timezone.utc)

    try:
        events = load_events(config.ical_url, tz)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR fetching iCal feed: {exc}", file=sys.stderr)
        return 1

    jobs = compute_jobs(events, now, tz, config.reminder1_offset, config.reminder2_offset)

    if not jobs:
        print("No reminders to send.")
        return 0

    sent = load_sent(config.state_file)
    today_str = now.astimezone(tz).date().isoformat()
    new_sent = set(sent)

    for job in jobs:
        key = make_key(job.event.uid, job.reminder_number, today_str)
        if key in sent:
            continue

        text = build_message(
            event=job.event,
            reminder_number=job.reminder_number,
            mode=config.message_mode,
            static_message=config.static_message,
            tz=tz,
        )

        if config.dry_run:
            print(f"[DRY RUN] Would DM @{config.mastodon_username}@{config.mastodon_base_url.removeprefix('https://')}:")
            print(text)
            print()
        else:
            from calendar2mastodon.mastodon_post import post_dm
            post_dm(config.mastodon_base_url, config.mastodon_access_token, config.mastodon_username, text)
            print(f"Sent reminder {job.reminder_number} for: {job.event.summary}")

        new_sent.add(key)

    if not config.dry_run:
        save_sent(config.state_file, new_sent)

    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cli_overrides: dict[str, object] = {}
    if args.ical_url is not None:
        cli_overrides["ical_url"] = args.ical_url
    if args.mastodon_base_url is not None:
        cli_overrides["mastodon_base_url"] = args.mastodon_base_url
    if args.mastodon_username is not None:
        cli_overrides["mastodon_username"] = args.mastodon_username
    if args.reminder1_offset is not None:
        cli_overrides["reminder1_offset"] = args.reminder1_offset
    if args.reminder2_offset is not None:
        cli_overrides["reminder2_offset"] = None if args.reminder2_offset.lower() == "none" else args.reminder2_offset
    if args.message_mode is not None:
        cli_overrides["message_mode"] = args.message_mode
    if args.static_message is not None:
        cli_overrides["static_message"] = args.static_message
    if args.timezone is not None:
        cli_overrides["timezone"] = args.timezone
    if args.lookahead_window is not None:
        cli_overrides["lookahead_window"] = args.lookahead_window
    if args.state_file is not None:
        cli_overrides["state_file"] = args.state_file
    if args.dry_run:
        cli_overrides["dry_run"] = True

    config = build_config(toml_path=args.config, cli_overrides=cli_overrides)
    sys.exit(run(config))


if __name__ == "__main__":
    main()
