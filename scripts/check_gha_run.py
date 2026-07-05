"""Check the latest calendar_reminder workflow run status via gh CLI."""

from __future__ import annotations

import json
import subprocess
import sys


WORKFLOW = "calendar_reminder.yml"
REPO = "matthewdeanmartin/calendar2mastodon"


def latest_run() -> dict:
    result = subprocess.run(
        [
            "gh", "run", "list",
            "--workflow", WORKFLOW,
            "--repo", REPO,
            "--limit", "1",
            "--json", "databaseId,status,conclusion,startedAt,updatedAt,url",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    runs = json.loads(result.stdout)
    if not runs:
        print("No runs found yet.")
        sys.exit(0)
    return runs[0]


def run_logs(run_id: int) -> str:
    result = subprocess.run(
        ["gh", "run", "view", str(run_id), "--repo", REPO, "--log-failed"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or result.stderr.strip()


def main() -> None:
    run = latest_run()
    status = run["status"]
    conclusion = run.get("conclusion") or "—"
    started = run.get("startedAt", "")
    updated = run.get("updatedAt", "")
    url = run.get("url", "")
    run_id = run["databaseId"]

    print(f"Run ID    : {run_id}")
    print(f"Status    : {status}")
    print(f"Conclusion: {conclusion}")
    print(f"Started   : {started}")
    print(f"Updated   : {updated}")
    print(f"URL       : {url}")

    if status == "completed":
        if conclusion == "success":
            print("\nRun completed successfully.")
        else:
            print(f"\nRun finished with conclusion: {conclusion}")
            print("\n--- Failed step logs ---")
            print(run_logs(run_id))
            sys.exit(1)
    else:
        print(f"\nRun is still {status}. Check again later or visit the URL above.")


if __name__ == "__main__":
    main()
