"""Interactively set GitHub Actions secrets for calendar2mastodon via the gh CLI."""

from __future__ import annotations

import getpass
import subprocess
import sys


SECRETS = [
    (
        "ICAL_URL",
        "iCal feed URL (contains your secret token — treated as a secret)",
        False,
    ),
    (
        "MASTODON_BASE_URL",
        "Mastodon instance base URL (e.g. https://mastodon.social)",
        False,
    ),
    (
        "MASTODON_ACCESS_TOKEN",
        "Mastodon access token (from Settings → Development → Your app)",
        True,
    ),
]


def check_gh_available() -> None:
    result = subprocess.run(["gh", "--version"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: 'gh' CLI not found. Install it from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)


def check_gh_authenticated() -> None:
    result = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: Not authenticated with gh. Run: gh auth login", file=sys.stderr)
        sys.exit(1)


def detect_repo() -> str:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: Could not detect GitHub repo. Are you inside the repo directory?", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def set_secret(repo: str, name: str, value: str) -> None:
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo],
        input=value,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR setting {name}: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def prompt_secret(label: str, description: str, hidden: bool) -> str:
    print(f"\n{label}")
    print(f"  {description}")
    while True:
        if hidden:
            value = getpass.getpass("  Value (hidden): ").strip()
        else:
            value = input("  Value: ").strip()
        if value:
            return value
        print("  Value cannot be empty. Try again.")


def main() -> None:
    check_gh_available()
    check_gh_authenticated()

    repo = detect_repo()
    print(f"Setting secrets on repo: {repo}")
    print("Press Ctrl-C to abort at any time.\n")
    print("You will be prompted for 3 secrets. Existing secrets will be overwritten.")

    collected: list[tuple[str, str]] = []
    for name, description, hidden in SECRETS:
        value = prompt_secret(name, description, hidden)
        collected.append((name, value))

    print("\nSetting secrets...")
    for name, value in collected:
        set_secret(repo, name, value)
        print(f"  ✓ {name}")

    print("\nDone. The calendar_reminder workflow is ready to run.")
    print(f"Trigger it manually: gh workflow run calendar_reminder.yml --repo {repo}")


if __name__ == "__main__":
    main()
