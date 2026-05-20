# State Persistence in GHA — Options and Tradeoffs

## The problem

`calendar2mastodon` writes a local JSON file recording which `(event_uid,
reminder_number, date)` tuples have already been posted. Without persistence
across GHA runs this file is lost every run and every event gets re-posted.

---

## Option 1: `actions/cache` (current spec default)

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/calendar2mastodon
    key: reminder-state-${{ runner.os }}
```

**Pros**
- Zero extra infrastructure.
- Fast restore (<1s for a tiny JSON file).
- Built into GHA.

**Cons**
- Cache can be evicted (GHA evicts LRU entries when the org/repo hits the 10 GB
  cap, or after 7 days of non-use on free plans).
- If evicted on a day when an event exists, that event's reminder fires again.
- For a personal calendar this is probably fine — a duplicate morning DM once in
  a while is a minor annoyance, not a production incident.

**Verdict**: good enough for personal use. Implement as default.

---

## Option 2: Commit state file to a dedicated branch

The workflow commits `sent.json` back to an orphan branch (e.g.
`refs/heads/state`) after each run.

**Pros**
- Durable: survives cache eviction.
- Visible: you can inspect history of what was sent.

**Cons**
- Requires `contents: write` permission (widens the workflow's blast radius).
- Adds a git commit + push step (~2–3s extra, minor).
- Orphan branch is slightly awkward to manage.
- If two runs race (unlikely for a daily cron but possible with
  `workflow_dispatch`) a push conflict occurs.

**Verdict**: viable but overkill for a personal tool. Implement as optional
`--state-backend git-branch` flag if durability ever matters.

---

## Option 3: External store (Redis, S3, DynamoDB, etc.)

Store sent state in a cloud key-value store.

**Pros**
- Fully durable and race-safe.

**Cons**
- Requires provisioning external infra and another secret.
- Way over-engineered for a personal calendar reminder.

**Verdict**: not worth it. Document as a "bring your own" extension point.

---

## Option 4: Idempotent design — skip state entirely

Design reminders so they are inherently idempotent: a digest that always posts
"here are today's events" every morning is fine to repeat. If the cache is
evicted you get the same DM twice — not a bug, just a minor duplicate.

**Pros**
- No state file needed.
- No persistence problem.
- Simpler code.

**Cons**
- If the user adds a second reminder (e.g. 2h before event), deduplication
  matters more — you don't want that firing twice on a re-run.
- Loses the ability to detect "this specific reminder was already sent today".

**Verdict**: viable for single-reminder digest mode. Keep state file for
correctness when reminder 2 is enabled, but make the consequence of losing it
clear: at worst you get one duplicate DM.

---

## EST vs EDT and the cron timing issue

The GHA cron `"30 11 * * *"` (11:30 UTC) equals:
- 6:30am EST (UTC-5, November–March)
- 7:30am EDT (UTC-4, March–November)

If exact 6:30am delivery matters year-round, two cron lines can be used:

```yaml
schedule:
  - cron: "30 11 * * *"   # 6:30am EST (Nov–Mar)
  - cron: "30 10 * * *"   # 6:30am EDT (Mar–Nov)
```

With deduplication the state file prevents the second trigger (which overlaps
with the DST transition day) from double-posting. Without it, the transition day
gets two runs but the digest content is identical so it is harmless.

The simpler single-cron approach is recommended; the 1-hour EDT drift is
acceptable for a morning digest.

---

## Recommendation

- **Default**: `actions/cache` (Option 1) for the state file.
- **Code design**: make the state backend pluggable behind a `StateStore`
  protocol so Option 2 or 4 can be swapped in without changing business logic.
- **Document** the eviction risk in README so users know what to expect.
