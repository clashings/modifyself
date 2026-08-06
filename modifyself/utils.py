"""
Pure utility functions. No Discord-specific state here.
"""

import re
from datetime import datetime, timezone


MARKDOWN_ESCAPE_RE = re.compile(r"([*_{\[\]()~`>\#+\-=|.!])")


def escape_markdown(text: str) -> str:
    """Escape Discord markdown characters."""
    return MARKDOWN_ESCAPE_RE.sub(r"\\", text)


def parse_time(timestamp: str) -> datetime:
    """Parse an ISO 8601 timestamp from Discord."""
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp)


def snowflake_time(snowflake: int) -> datetime:
    """Extract the creation time from a snowflake ID."""
    from .core.snowflake import Snowflake
    return datetime.fromtimestamp(
        ((snowflake >> 22) + Snowflake.EPOCH) / 1000,
        tz=timezone.utc,
    )


def chunk_list(lst: list, size: int):
    """Yield successive chunks of a list."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def find(predicate, iterable):
    """Return the first item in iterable matching predicate."""
    for item in iterable:
        if predicate(item):
            return item
    return None


def get(iterable, **attrs):
    """Return the first item in iterable with matching attributes."""
    for item in iterable:
        if all(getattr(item, k, None) == v for k, v in attrs.items()):
            return item
    return None


def oauth_url(client_id: int, *, permissions: int = 0, guild_id: int | None = None):
    """Generate an OAuth2 authorization URL."""
    url = f"https://discord.com/oauth2/authorize?client_id={client_id}&scope=bot"
    if permissions:
        url += f"&permissions={permissions}"
    if guild_id:
        url += f"&guild_id={guild_id}"
    return url