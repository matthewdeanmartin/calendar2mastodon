"""Post a direct message to self via Mastodon.py (lazily imported)."""

from __future__ import annotations


def post_dm(base_url: str, access_token: str, username: str, text: str) -> None:
    from mastodon import Mastodon  # type: ignore[import-untyped]

    client = Mastodon(access_token=access_token, api_base_url=base_url)
    dm_text = f"@{username} {text}"
    client.status_post(dm_text, visibility="direct")
