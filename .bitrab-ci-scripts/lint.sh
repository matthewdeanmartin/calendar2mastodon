#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run isort --check-only calendar2mastodon tests
uv run black --check calendar2mastodon tests
uv run ruff check --quiet calendar2mastodon tests
uv run pylint --score=n --reports=n --rcfile=.pylintrc calendar2mastodon
uv run pylint --score=n --reports=n --rcfile=.pylintrc_tests tests
