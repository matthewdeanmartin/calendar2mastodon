# calendar2mastodon — Specification

## Overview

`calendar2mastodon` fetches an iCalendar feed and posts upcoming event reminders
as Mastodon DMs (direct messages) to the authenticated account owner.
It is designed to run as a GitHub Actions scheduled workflow and must minimise
startup overhead to reduce billed GHA minutes.

---

## Goals

- Parse an iCal feed (URL or local file) for upcoming events.
- Post one or two timed reminders per event as Mastodon DMs.
- Reminder messages can be static ("hey, check your calendar") or include event
  details (summary, start time, location/description).
- Configuration lives in `pyproject.toml` under `[tool.calendar2mastodon]`
  (overridable by env vars and CLI flags).
- CLI uses `argparse`; entry point is `calendar2mastodon.cli:main`.
- Ships a ready-to-use GitHub Actions workflow for scheduling.
- Secure by default: no secrets in config files, no logging of credentials.

---

## Functional Requirements

### Reminder model

Each run acts as a **morning digest**: at the scheduled run time (default 6:30am
EST) the tool posts DMs for every event starting on that calendar day.

Optionally a second reminder can be configured for each event (e.g. a same-day
closer reminder). Up to **two** reminders per event are supported:

| Reminder | Config key | Default behaviour |
|----------|-----------|-------------------|
| Reminder 1 | `reminder1_offset` | `"0m"` — fires at run time for events today |
| Reminder 2 | `reminder2_offset` | `null` — disabled by default |

An offset of `null` / absent disables that reminder entirely.
Offsets are expressed as a string: `"<N><unit>"` where unit is
`m` (minutes), `h` (hours), `d` (days). `"0m"` means "fire immediately on this
run for matching events".

**Digest mode** (reminder1_offset = `"0m"`): the tool scans for events whose
`start` date equals today in the configured timezone, and posts one DM per event
at run time. This is the default and primary use case.

### Message modes

Controlled by `message_mode` (config / CLI):

| Mode | Content |
|------|---------|
| `static` | A fixed string (e.g. "Hey, check your calendar!") |
| `event` | Event summary + start time (+ optional location/description) |

`static_message` config key holds the text used in `static` mode.

### Timezone handling

- `timezone` config key: either `"UTC"` or any IANA tz name (e.g. `"America/New_York"`).
- Default: `"America/New_York"` (EST/EDT, matching the 6:30am run).
- "Today" for digest purposes is determined in the configured timezone.
- All times in `event` mode messages are rendered in the configured timezone.
- Internal scheduling is always computed in UTC; timezone only affects display
  and the definition of "today".
- Runtime dependency: `tzdata` package (required on Windows and some Linux
  containers where system tz data may be absent).

---

## Configuration

### `pyproject.toml` section

```toml
[tool.calendar2mastodon]
ical_url            = ""                        # overridden by ICAL_URL env var
mastodon_base_url   = "https://mastodon.social"
mastodon_username   = "mistersql"               # used for self-DM targeting
reminder1_offset    = "0m"                      # digest at run time
reminder2_offset    = null                      # disabled
message_mode        = "event"                   # "static" or "event"
static_message      = "Hey, check your calendar!"
timezone            = "America/New_York"
lookahead_window    = "1d"                      # scan today's events only
```

### Environment variables (secrets — never in config files)

| Variable | Purpose |
|----------|---------|
| `ICAL_URL` | iCal feed URL (contains secret token — must not appear in toml or logs) |
| `MASTODON_BASE_URL` | Base URL of Mastodon instance (may also be in toml) |
| `MASTODON_ACCESS_TOKEN` | OAuth access token for posting |

### Precedence (lowest → highest)

1. `pyproject.toml` `[tool.calendar2mastodon]`
2. Environment variables
3. CLI flags

---

## CLI Interface

```
usage: calendar2mastodon [-h] [--version]
                         [--ical-url URL]
                         [--mastodon-base-url URL]
                         [--mastodon-username USER]
                         [--reminder1-offset OFFSET]
                         [--reminder2-offset OFFSET]
                         [--message-mode {static,event}]
                         [--static-message TEXT]
                         [--timezone TZ]
                         [--lookahead-window WINDOW]
                         [--dry-run]
                         [--state-file PATH]
                         [--config FILE]
```

- `--dry-run`: print what would be posted; do not call Mastodon API.
- `--config FILE`: path to a `pyproject.toml`-format file (default: auto-discover
  `pyproject.toml` from CWD upward).
- `--state-file PATH`: override default state file location.
- All other flags mirror the `[tool.calendar2mastodon]` keys.

---

## Module Structure

```
calendar2mastodon/
    __about__.py       # version
    __init__.py
    __main__.py        # python -m calendar2mastodon
    cli.py             # argparse entry point; thin — delegates to core
    config.py          # load/merge config from toml + env + cli args
    ical_fetch.py      # fetch + parse iCal; return list of Event dataclasses
    reminder.py        # compute which reminders fire for the current run
    mastodon_post.py   # post DM via Mastodon.py (lazy import)
    message.py         # build message text (static vs event mode)
```

### Key dataclasses

```python
@dataclass
class CalendarEvent:
    uid: str
    summary: str
    start: datetime          # timezone-aware
    end: datetime            # timezone-aware
    location: str
    description: str

@dataclass
class ReminderJob:
    event: CalendarEvent
    reminder_number: int     # 1 or 2
    fire_at: datetime        # UTC, when this reminder should be sent
```

---

## Libraries

| Purpose | Library |
|---------|---------|
| iCal parsing | `icalendar` (RFC 5545 compliant) |
| Timezone | `zoneinfo` (stdlib 3.9+) + `tzdata` (runtime dep, handles Windows + containers) |
| Mastodon posting | `Mastodon.py` |
| HTTP fetch | `httpx` |
| Config / toml | `tomllib` (stdlib 3.11+) + `tomli` backport for 3.9–3.10 |

`httpx` is preferred over `urllib.request` for ergonomics, SSL verification
defaults, and timeout handling. TLS certificate verification must not be
disabled.

---

## Scheduling Logic

The tool is called once daily (6:30am EST via GHA cron). On each run it:

1. Fetches the iCal feed via `httpx`.
2. Determines `today` in the configured timezone (`America/New_York` by default).
3. For every event whose `start` date == today:
   - Computes `fire_at` for reminder 1: `now` (offset `"0m"` → fire immediately).
   - Computes `fire_at` for reminder 2 if configured (e.g. `"2h"` → 2 hours
     before event start).
4. For each `ReminderJob` that should fire on this run, post the DM.

**Deduplication:** A lightweight state file (JSON) records
`(event_uid, reminder_number, date)` tuples already sent. This prevents a
re-run or cache miss from double-posting the same reminder.

State file path (precedence):
1. `--state-file` CLI flag
2. `CALENDAR2MASTODON_STATE_FILE` env var
3. `~/.cache/calendar2mastodon/sent.json`

See `spec/cache.md` for tradeoffs around persisting state in GHA.

---

## Security Requirements

- `MASTODON_ACCESS_TOKEN` and `ICAL_URL` are **only** read from environment
  variables — never written to any log or config file on disk.
- Mastodon post visibility is always `direct` (DM to self only).
- The iCal URL scheme is validated as `https` before fetching (or `file` for
  local paths in `--dry-run` / test mode).
- The generated GHA workflow stores secrets in GitHub Actions secrets only and
  never echoes them.
- `httpx` TLS certificate verification is always enabled; the code never passes
  `verify=False`.
- `bandit` is in the dev toolchain as a quality gate.

---

## Mastodon OAuth Setup

The app requires a Mastodon API access token with scope `write:statuses`.

Steps to generate:
1. Log in to your Mastodon instance (`mastodon.social`).
2. Go to **Preferences → Development → New Application**.
3. Name: `calendar2mastodon`; Scopes: tick **`write:statuses`** only (uncheck
   everything else for least privilege).
4. Click **Submit**, then copy the **Your access token** value.
5. Store it as the `MASTODON_ACCESS_TOKEN` GitHub Actions secret (never in code
   or config files).

The `mastodon_username` config value (`mistersql`) is used to address the DM
to yourself via `@mistersql@mastodon.social`.

---

## GitHub Actions Workflow

File: `.github/workflows/calendar_reminder.yml`

```yaml
name: Calendar Reminder
on:
  schedule:
    - cron: "30 11 * * *"   # 6:30am EST = 11:30 UTC (adjusts for EDT automatically
                             # via timezone config — cron always fires in UTC)
  workflow_dispatch: {}

permissions:
  contents: read

jobs:
  remind:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: hynek/setup-cached-uv@v2

      - name: Restore reminder state
        uses: actions/cache@v4
        with:
          path: ~/.cache/calendar2mastodon
          key: reminder-state-${{ runner.os }}

      - name: Install (no dev deps)
        run: uv sync --no-dev

      - name: Run reminders
        env:
          ICAL_URL: ${{ secrets.ICAL_URL }}
          MASTODON_BASE_URL: ${{ secrets.MASTODON_BASE_URL }}
          MASTODON_ACCESS_TOKEN: ${{ secrets.MASTODON_ACCESS_TOKEN }}
        run: uv run calendar2mastodon

      - name: Save reminder state
        uses: actions/cache@v4
        with:
          path: ~/.cache/calendar2mastodon
          key: reminder-state-${{ runner.os }}
```

Notes:
- Cron fires at 11:30 UTC = 6:30am EST (UTC-5). During EDT (UTC-4) the run
  lands at 7:30am — acceptable for a morning digest. If exact local time matters
  year-round, two cron entries can cover winter and summer separately.
- `uv sync --no-dev` installs only runtime deps — fast cold start.
- `actions/cache` persists the deduplication state file across runs.
- `persist-credentials: false` limits token exposure.
- No secrets are printed, echoed, or written to step logs.

---

## Performance Notes

- iCal feeds for personal calendars are typically small (<50 KB); no streaming
  needed.
- `uv` with cached packages brings cold install under ~5 seconds.
- The tool's own startup should be under 1 second: no heavy imports at module
  level; `Mastodon.py` is imported lazily inside the post function so `--dry-run`
  and config-validation paths pay zero Mastodon.py startup cost.
- `httpx` is imported at the top of `ical_fetch.py` only; other modules do not
  pay its import cost.
