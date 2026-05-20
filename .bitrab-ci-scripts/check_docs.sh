#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run interrogate calendar2mastodon --verbose --fail-under 70
uv run codespell --ignore-words=private_dictionary.txt calendar2mastodon tests README.md CHANGELOG.md docs || true
uv run pylint --score=n --reports=n --rcfile=.pylintrc_spell calendar2mastodon || true
