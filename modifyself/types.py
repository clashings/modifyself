"""
TypedDict mirrors of Discord's JSON payloads.
Update this when Discord changes their API.
"""

from typing import TypedDict, NotRequired


class UserPayload(TypedDict):
    id: str
    username: str
    discriminator: str
    avatar: str | None
    bot: NotRequired[bool]
    system: NotRequired[bool]
    public_flags: NotRequired[int]


class MemberPayload(TypedDict):
    user: NotRequired[UserPayload]
    nick: NotRequired[str | None]
    roles: list[str]
    joined_at: str
    premium_since: NotRequired[str | None]
    deaf: bool
    mute: bool
    pending: NotRequired[bool]


class ChannelPayload(TypedDict):
    id: str
    type: int
    guild_id: NotRequired[str]
    name: NotRequired[str]
    topic: NotRequired[str | None]
    nsfw: NotRequired[bool]
    last_message_id: NotRequired[str | None]
    parent_id: NotRequired[str | None]
    permission_overwrites: NotRequired[list[dict]]
    position: NotRequired[int]
    recipients: NotRequired[list[UserPayload]]


class MessagePayload(TypedDict):
    id: str
    channel_id: str
    author: UserPayload
    content: str
    timestamp: str
    edited_timestamp: str | None
    tts: bool
    mention_everyone: bool
    mentions: list[UserPayload]
    mention_roles: list[str]
    attachments: list[dict]
    embeds: list[dict]
    reactions: NotRequired[list[dict]]
    pinned: bool
    type: int
    guild_id: NotRequired[str]
    member: NotRequired[MemberPayload]
    referenced_message: NotRequired["MessagePayload" | None]


class GuildPayload(TypedDict):
    id: str
    name: str
    icon: str | None
    splash: str | None
    owner_id: str
    region: NotRequired[str]
    afk_channel_id: str | None
    afk_timeout: int
    verification_level: int
    default_message_notifications: int
    explicit_content_filter: int
    roles: list[dict]
    emojis: list[dict]
    features: list[str]
    mfa_level: int
    system_channel_id: str | None
    system_channel_flags: int
    max_presences: NotRequired[int | None]
    max_members: NotRequired[int]
    vanity_url_code: str | None
    description: str | None
    banner: str | None
    premium_tier: int
    premium_subscription_count: NotRequired[int]
    preferred_locale: str
    public_updates_channel_id: str | None
    max_video_channel_users: NotRequired[int]
    approximate_member_count: NotRequired[int]
    approximate_presence_count: NotRequired[int]
    nsfw_level: int
    members: NotRequired[list[MemberPayload]]
    channels: NotRequired[list[ChannelPayload]]


class ReadyPayload(TypedDict):
    v: int
    user: UserPayload
    guilds: list[dict]
    session_id: str
    shard: NotRequired[list[int]]
    application: NotRequired[dict]
