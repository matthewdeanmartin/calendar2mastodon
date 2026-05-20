"""Tests for sent-reminder state tracking."""

import json
from pathlib import Path

from calendar2mastodon.state import load_sent, make_key, save_sent


def test_load_empty_when_no_file(tmp_path):
    sent = load_sent(tmp_path / "nonexistent.json")
    assert sent == set()


def test_round_trip(tmp_path):
    path = tmp_path / "sent.json"
    keys = {make_key("uid-1", 1, "2026-05-20"), make_key("uid-2", 2, "2026-05-20")}
    save_sent(path, keys)
    loaded = load_sent(path)
    assert loaded == keys


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "sent.json"
    save_sent(path, {make_key("uid-x", 1, "2026-05-20")})
    assert path.is_file()


def test_make_key_structure():
    key = make_key("some-uid", 1, "2026-05-20")
    assert key == ("some-uid", 1, "2026-05-20")
