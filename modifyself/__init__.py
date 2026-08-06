"""
modifyself — a clean, pythonic Discord self-bot library.
"""

__version__ = "0.1.2"

from .client import Client
from .commands.core import command
from .commands.cog import Cog
from .commands.context import Context

__all__ = ["Client", "command", "Cog", "Context"]
