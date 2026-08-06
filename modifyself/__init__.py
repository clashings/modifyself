"""
modifyself — a clean, pythonic Discord self-bot library.
"""

__version__ = "0.1.0"

from .client import Client
from .core.snowflake import Snowflake
from .core.bitfield import Bitfield, Permissions
from .core.enums import *
from .core.mixins import Hashable, EqualityById
from .errors import (
    DiscordException,
    HTTPException,
    GatewayException,
    CommandError,
    CheckFailure,
    ConversionError,
)
from .models.base import DiscordObject
from .models.user import User
from .models.guild import Guild
from .models.channel import Channel, TextChannel, DMChannel
from .models.message import Message
from .models.member import Member
from .commands.core import Command, command
from .commands.context import Context
from .commands.cog import Cog, listener

__all__ = [
    "Client",
    "Snowflake",
    "Bitfield",
    "Permissions",
    "DiscordException",
    "HTTPException",
    "GatewayException",
    "CommandError",
    "CheckFailure",
    "ConversionError",
    "DiscordObject",
    "User",
    "Guild",
    "Channel",
    "TextChannel",
    "DMChannel",
    "Message",
    "Member",
    "Command",
    "command",
    "Context",
    "Cog",
    "listener",
]