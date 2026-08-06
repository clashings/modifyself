"""
Main client class for modifyself.
"""

import asyncio
import inspect
import logging
import signal
import sys
from typing import Callable, Any, Optional, List, Dict, Union

from .http.client import HTTPClient
from .http.route import Route
from .gateway.websocket import GatewayWebSocket
from .gateway.dispatcher import EventDispatcher
from .state import ConnectionState
from .commands.core import Command, command
from .commands.context import Context
from .commands.cog import Cog
from .errors import CommandError, ConversionError, CommandNotFound
from .models.message import Message
from .headers import HeaderSpoofer, EMULATION
from .utils import send_notification, START_IMAGE, ERROR_IMAGE

logger = logging.getLogger(__name__)


class Client:
    """
    The main client for interacting with Discord.

    Usage:
        bot = Client(token="your_token")

        @bot.event
        async def on_ready():
            print(f"Logged in as {bot.user}")

        @bot.command()
        async def ping(ctx):
            await ctx.reply("Pong!")

        bot.run()
    """

    def __init__(
        self,
        *,
        token: str,
        command_prefix: Union[str, Callable[["Client", Message], str]] = "!",
        owner_ids: Optional[List[int]] = None,
        proxy: Optional[str] = None,
        notifications: bool = True,  # NEW: enable/disable notifications
    ):
        self.token = token
        self.command_prefix = command_prefix
        self.owner_ids = set(owner_ids) if owner_ids else set()
        self._notifications = notifications  # NEW

        # Internal components
        self._headers = HeaderSpoofer(token, EMULATION)
        self._http = HTTPClient(
            token,
            headers=self._headers,
            proxy=proxy,
        )
        self._state = ConnectionState(self._http)
        self._dispatcher = EventDispatcher(self._state)
        self._gateway = GatewayWebSocket(
            self._dispatcher,
            token,
            headers=self._headers,
        )

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._once_handlers: Dict[str, List[Callable]] = {}

        # Command registry
        self._commands: Dict[str, Command] = {}
        self._cogs: Dict[str, Cog] = {}

        # Lifecycle
        self._ready = asyncio.Event()
        self._closed = False
        self._task: Optional[asyncio.Task] = None
        self._close_task: Optional[asyncio.Task] = None
        self._error_handled = False  # NEW: prevent duplicate error notifications

        # Auto-register built-in event parsers
        self._dispatcher.on("READY", self._on_ready_internal)
        self._dispatcher.on("MESSAGE_CREATE", self._on_message_create_internal)

        # Send startup notification
        if self._notifications:
            send_notification(
                title="🚀 modifyself Initialized",
                message="Client created successfully. Starting connection...",
                image_url=START_IMAGE,
                timeout=3
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def user(self):
        """The client's user object."""
        return self._state.user

    @property
    def guilds(self):
        """A view of the guilds the client is in."""
        return list(self._state._guilds.values())

    @property
    def users(self):
        """A view of the users the client has cached."""
        return list(self._state._users.values())

    @property
    def latency(self) -> float:
        """The current gateway latency in seconds."""
        return self._gateway.latency

    @property
    def listeners(self) -> Dict[str, List]:
        """A view of registered event listeners by event name."""
        return dict(self._dispatcher._handlers)

    @property
    def commands(self) -> List[Command]:
        """Return a list of registered commands."""
        return list(self._commands.values())

    @property
    def cogs(self) -> List[Cog]:
        """Return a list of loaded cogs."""
        return list(self._cogs.values())

    # ------------------------------------------------------------------
    # Event decorators
    # ------------------------------------------------------------------
    def event(self, coro: Callable):
        """Register an event handler."""
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("Event handlers must be coroutines")
        name = coro.__name__.replace("on_", "", 1).upper()
        self._dispatcher.on(name, coro)
        self._event_handlers.setdefault(name, []).append(coro)
        logger.debug("Registered event handler for %s", name)
        return coro

    def listen(self, name: Optional[str] = None):
        """Decorator to register an event listener by explicit name."""
        def decorator(coro: Callable):
            if not asyncio.iscoroutinefunction(coro):
                raise TypeError("Listeners must be coroutines")
            event_name = (name or coro.__name__).upper()
            self._dispatcher.on(event_name, coro)
            return coro
        return decorator

    def add_listener(self, event: str, handler: Callable):
        """Add a listener for an event."""
        event = event.upper()
        self._dispatcher.on(event, handler)
        logger.info("[client] listener registered: %s -> %s", event, handler)

    def remove_listener(self, event: str, handler: Callable):
        """Remove a listener for an event."""
        self._dispatcher.off(event.upper(), handler)

    # ------------------------------------------------------------------
    # Command registration
    # ------------------------------------------------------------------
    def command(self, *, name: Optional[str] = None, aliases: Optional[List[str]] = None, **kwargs):
        """Decorator to register a command."""
        def decorator(func: Callable):
            cmd = Command(func, name=name, aliases=aliases, **kwargs)
            self.add_command(cmd)
            func._command = cmd
            return func
        return decorator

    def add_command(self, cmd: Command):
        """Register a Command instance."""
        if cmd.name in self._commands:
            raise ValueError(f"Command {cmd.name} is already registered")
        
        # Check aliases first before adding anything
        for alias in cmd.aliases:
            if alias in self._commands:
                raise ValueError(f"Alias {alias} is already registered")
        
        # Now safe to add
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd
        logger.debug("Registered command: %s", cmd.name)

    def remove_command(self, name: str):
        """Remove a command by name or alias."""
        cmd = self._commands.pop(name, None)
        if cmd and cmd.name == name:
            for alias in cmd.aliases:
                self._commands.pop(alias, None)

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name or alias."""
        return self._commands.get(name)

    # ------------------------------------------------------------------
    # Cog management
    # ------------------------------------------------------------------
    def add_cog(self, cog: Cog):
        """Add a cog to the bot."""
        if cog.name in self._cogs:
            raise ValueError(f"Cog {cog.name} is already loaded")
        cog._inject(self)
        self._cogs[cog.name] = cog
        cog.cog_load()
        logger.info("Loaded cog: %s", cog.name)

    def remove_cog(self, name: str):
        """Remove a cog from the bot."""
        cog = self._cogs.pop(name, None)
        if cog:
            cog.cog_unload()
            cog._eject(self)
            logger.info("Unloaded cog: %s", name)

    def get_cog(self, name: str) -> Optional[Cog]:
        """Get a loaded cog by name."""
        return self._cogs.get(name)

    # ------------------------------------------------------------------
    # Internal event handlers
    # ------------------------------------------------------------------
    async def _on_ready_internal(self, user):
        """Internal READY handler."""
        self._ready.set()
        logger.debug("Ready event received internally")
        
        # Send notification when bot is ready
        if self._notifications:
            username = user.name if user else "Unknown"
            send_notification(
                title="✅ Bot is Running",
                message=f"Logged in as {username}",
                image_url=START_IMAGE,
                timeout=5
            )

    async def _on_message_create_internal(self, message: Message):
        """Internal MESSAGE_CREATE handler for command processing."""
        logger.debug(f"📩 MESSAGE_CREATE: {message.content[:50] if message.content else '(empty)'}")
        await self._process_commands(message)

    async def _process_commands(self, message: Message):
        """Check if a message triggers a command and invoke it."""
        # SELF-BOT: Only respond to our own messages
        if not self.user or message.author.id != self.user.id:
            return
        
        # Don't process messages from bots
        if message.author.bot:
            logger.debug("Message from bot, ignoring")
            return

        # Resolve prefix
        if callable(self.command_prefix):
            prefix = self.command_prefix(self, message)
        else:
            prefix = self.command_prefix

        if not prefix:
            return

        content = message.content
        if not content:
            return

        logger.debug(f"Checking command: content='{content}', prefix='{prefix}'")

        # Check for prefix
        if not content.startswith(prefix):
            # Check for mention prefix (if user account)
            if self.user:
                mention = f"<@{self.user.id}>"
                mention_nick = f"<@!{self.user.id}>"
                if content.startswith(mention):
                    content = content[len(mention):].lstrip()
                    logger.debug(f"Stripped mention: '{content}'")
                elif content.startswith(mention_nick):
                    content = content[len(mention_nick):].lstrip()
                    logger.debug(f"Stripped mention_nick: '{content}'")
                else:
                    return
            else:
                return
        else:
            # Strip prefix
            content = content[len(prefix):].strip()
            logger.debug(f"Stripped prefix: '{content}'")

        if not content:
            return

        parts = content.split()
        name = parts[0]
        args = parts[1:]

        logger.info(f"Command detected: {name} with args: {args}")

        command = self._commands.get(name)
        if not command:
            logger.debug(f"Command not found: {name}")
            # Fire command not found event if registered
            for handler in self._event_handlers.get("COMMAND_NOT_FOUND", []):
                try:
                    await handler(message, name)
                except Exception:
                    logger.exception("Error in command not found handler")
            return

        ctx = Context(
            message=message,
            command=command,
            args=args,
            kwargs={},
            bot=self,
        )

        try:
            await command.invoke(ctx)
            logger.info(f"Command {name} executed successfully")
        except CommandError as exc:
            logger.warning("Command error in %s: %s", command.name, exc)
            self._handle_error(f"Command error in {command.name}: {exc}")
            for handler in self._event_handlers.get("COMMAND_ERROR", []):
                try:
                    await handler(ctx, exc)
                except Exception:
                    logger.exception("Error in command error handler")
        except Exception as exc:
            logger.exception("Unexpected error in command %s", command.name)
            self._handle_error(f"Unexpected error in {command.name}: {exc}")
            for handler in self._event_handlers.get("COMMAND_ERROR", []):
                try:
                    await handler(ctx, exc)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------
    def _handle_error(self, error_message: str):
        """Send a notification when an error occurs."""
        if self._notifications and not self._error_handled:
            self._error_handled = True
            send_notification(
                title="❌ Error Occurred",
                message=error_message[:100] + ("..." if len(error_message) > 100 else ""),
                image_url=ERROR_IMAGE,
                timeout=10
            )
            # Reset after a moment so new errors can trigger notifications
            asyncio.get_event_loop().call_later(2, lambda: setattr(self, '_error_handled', False))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self):
        """Start the client (connects to gateway)."""
        self._closed = False
        self._error_handled = False
        try:
            await self._gateway.connect()
        except Exception as exc:
            logger.exception("Gateway connection error: %s", exc)
            self._handle_error(f"Failed to connect: {exc}")
            raise

    async def close(self):
        """Close the client and cleanup."""
        if self._closed:
            return
            
        self._closed = True
        self._ready.clear()
        
        # Close gateway first
        await self._gateway.close()
        
        # Close HTTP client
        await self._http.close()
        
        logger.info("Client closed")

    def run(self):
        """Run the client with a new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Store close task reference
        self._close_task = None

        def signal_handler(sig):
            logger.info("Received signal %s, shutting down...", sig)
            if loop.is_running():
                # Schedule close in the event loop
                asyncio.run_coroutine_threadsafe(self.close(), loop)

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

        async def runner():
            try:
                await self.start()
            except Exception as exc:
                # Catch any unhandled errors in the main loop
                self._handle_error(f"Bot crashed: {exc}")
                raise
            finally:
                await self.close()

        try:
            loop.run_until_complete(runner())
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as exc:
            # Any unhandled exception at the top level
            self._handle_error(f"Bot crashed: {exc}")
            raise
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    async def wait_until_ready(self):
        """Wait until the client receives the READY event."""
        await self._ready.wait()

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------
    async def fetch_user(self, user_id: int):
        """Fetch a user from the HTTP API."""
        data = await self._http.request(Route.user(user_id))
        return self._state._add_user(data)

    async def fetch_guild(self, guild_id: int):
        """Fetch a guild from the HTTP API."""
        data = await self._http.request(Route.guild(guild_id))
        return self._state._add_guild(data)

    async def fetch_channel(self, channel_id: int):
        """Fetch a channel from the HTTP API."""
        data = await self._http.request(Route.channel(channel_id))
        return self._state._add_channel(data)

    async def fetch_message(self, channel_id: int, message_id: int):
        """Fetch a message from the HTTP API."""
        data = await self._http.request(Route.channel_message(channel_id, message_id))
        return self._state._store_message(data)

    def get_guild(self, guild_id: int):
        """Get a cached guild by ID."""
        return self._state._guilds.get(guild_id)

    def get_channel(self, channel_id: int):
        """Get a cached channel by ID."""
        return self._state._channels.get(channel_id)

    def get_user(self, user_id: int):
        """Get a cached user by ID."""
        return self._state._users.get(user_id)
