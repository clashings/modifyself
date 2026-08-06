"""
Discord Message model.
"""

from typing import TYPE_CHECKING

from .base import DiscordObject
from .user import User
from ..core.snowflake import Snowflake
from ..utils import parse_time

if TYPE_CHECKING:
    from ..state import ConnectionState
    from .member import Member
    from .channel import Channel
    from .guild import Guild


class Message(DiscordObject):
    """Represents a message in Discord."""

    __slots__ = (
        "channel_id",
        "author",
        "content",
        "timestamp",
        "edited_at",
        "tts",
        "mention_everyone",
        "mentions",
        "mention_roles",
        "attachments",
        "embeds",
        "reactions",
        "pinned",
        "type",
        "guild_id",
        "member",
        "referenced_message",
        "_cs_channel",
        "_cs_guild",
    )

    def __init__(self, *, state: "ConnectionState", data: dict):
        super().__init__(state=state, data=data)
        self._cs_channel = None
        self._cs_guild = None
        self._update(data)

    def _update(self, data: dict):
        self.channel_id = Snowflake(data.get("channel_id", 0))
        author_data = data.get("author", {})
        self.author = User(state=self._state, data=author_data)
        self.content = data.get("content", "")
        self.timestamp = parse_time(data["timestamp"]) if "timestamp" in data else None
        self.edited_at = (
            parse_time(data["edited_timestamp"]) if data.get("edited_timestamp") else None
        )
        self.tts = data.get("tts", False)
        self.mention_everyone = data.get("mention_everyone", False)
        self.mentions = [
            User(state=self._state, data=u) for u in data.get("mentions", [])
        ]
        self.mention_roles = [int(r) for r in data.get("mention_roles", [])]
        self.attachments = data.get("attachments", [])
        self.embeds = data.get("embeds", [])
        self.reactions = data.get("reactions", [])
        self.pinned = data.get("pinned", False)
        self.type = data.get("type", 0)
        self.guild_id = (
            Snowflake(data["guild_id"]) if data.get("guild_id") else None
        )

        # Member info if present
        member_data = data.get("member")
        if member_data and self.guild_id:
            from .member import Member
            self.member = Member(
                state=self._state, data={**member_data, "user": author_data},
                guild_id=self.guild_id
            )
        else:
            self.member = None

        # Referenced message
        ref_data = data.get("referenced_message")
        if ref_data:
            self.referenced_message = Message(state=self._state, data=ref_data)
        else:
            self.referenced_message = None

    def __repr__(self) -> str:
        return f"<Message id={self.id} author={self.author!r} channel={self.channel_id}>"

    def __str__(self) -> str:
        return self.content

    @property
    def channel(self) -> "Channel | None":
        if self._cs_channel is None:
            self._cs_channel = self._state._channels.get(self.channel_id)
        return self._cs_channel

    @property
    def guild(self) -> "Guild | None":
        if self.guild_id is None:
            return None
        if self._cs_guild is None:
            self._cs_guild = self._state._guilds.get(self.guild_id)
        return self._cs_guild

    @property
    def jump_url(self) -> str:
        guild_id = self.guild_id or "@me"
        return f"https://discord.com/channels/{guild_id}/{self.channel_id}/{self.id}"

    @property
    def created_at(self):
        return self.id.created_at

    @property
    def edited_timestamp(self):
        return self.edited_at

    @property
    def clean_content(self) -> str:
        """The message content with mentions replaced with names."""
        content = self.content
        for user in self.mentions:
            content = content.replace(f"<@{user.id}>", f"@{user.display_name}")
            content = content.replace(f"<@!{user.id}>", f"@{user.display_name}")
        return content

    async def delete(self, *, delay: float | None = None):
        """Delete this message."""
        if delay:
            import asyncio
            await asyncio.sleep(delay)
        await self._state.http.delete_message(self.channel_id, self.id)

    async def edit(self, content: str | None = None, **kwargs):
        """Edit this message."""
        data = await self._state.http.edit_message(
            self.channel_id, self.id, content, **kwargs
        )
        self._update(data)
        return self

    async def reply(self, content: str | None = None, **kwargs):
        """Reply to this message."""
        ref = {
            "type": 0,
            "message_id": str(self.id),
            "channel_id": str(self.channel_id),
        }
        if self.guild_id:
            ref["guild_id"] = str(self.guild_id)
        kwargs["message_reference"] = ref
        data = await self._state.http.send_message(self.channel_id, content, **kwargs)
        return self._state._store_message(data)

    async def add_reaction(self, emoji: str):
        """Add a reaction to this message."""
        await self._state.http.add_reaction(self.channel_id, self.id, emoji)

    async def remove_reaction(self, emoji: str):
        """Remove a reaction from this message."""
        await self._state.http.remove_reaction(self.channel_id, self.id, emoji)

    async def clear_reactions(self):
        """Clear all reactions from this message."""
        await self._state.http.clear_reactions(self.channel_id, self.id)

    async def pin(self):
        """Pin this message."""
        await self._state.http.pin_message(self.channel_id, self.id)

    async def unpin(self):
        """Unpin this message."""
        await self._state.http.unpin_message(self.channel_id, self.id)