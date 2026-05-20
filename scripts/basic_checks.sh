#!/usr/bin/env bash
# Smoke test: exercises the CLI arg parser and verifies basic invocations exit cleanly.
# Counts successes and failures; exits non-zero if any check failed.
# Source an already-active venv before running, or call via `uv run bash scripts/basic_checks.sh`.

set -ou pipefail

PASS=0
FAIL=0
CLI_PYTHON="${PYTHON:-python}"

run_cli() {
    "$CLI_PYTHON" -m calendar2mastodon "$@"
}

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  PASS: $desc"
        ((PASS++))
    else
        echo "  FAIL: $desc  (cmd: $*)"
        ((FAIL++))
    fi
}

check_fails() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  FAIL: $desc  (expected non-zero exit, got 0)"
        ((FAIL++))
    else
        echo "  PASS: $desc"
        ((PASS++))
    fi
}

echo "=== calendar2mastodon basic_checks ==="
echo ""
echo "using: ${CLI_PYTHON} -m calendar2mastodon"
echo ""

echo "--- global flags ---"
check "calendar2mastodon --help"    run_cli --help
check "calendar2mastodon --version" run_cli --version

# TODO: add subcommand smoke checks here, e.g.:
# check "calendar2mastodon <subcommand> --help"  run_cli <subcommand> --help

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
