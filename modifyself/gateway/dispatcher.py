"""
Event dispatcher: maps gateway events to handlers.
"""

import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Pub/sub event dispatcher for gateway events.

    Parsers update state first, then listeners are notified.
    """

    def __init__(self, state):
        self._state = state
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._parsers = self._build_parsers()

    def _build_parsers(self) -> Dict[str, Callable]:
        """Map event names to state parser methods."""
        return {
            "READY": self._state.parse_ready,
            "RESUMED": self._state.parse_resumed,
            "USER_UPDATE": self._state.parse_user_update,
            "GUILD_CREATE": self._state.parse_guild_create,
            "GUILD_UPDATE": self._state.parse_guild_update,
            "GUILD_DELETE": self._state.parse_guild_delete,
            "GUILD_MEMBER_ADD": self._state.parse_guild_member_add,
            "GUILD_MEMBER_REMOVE": self._state.parse_guild_member_remove,
            "GUILD_MEMBER_UPDATE": self._state.parse_guild_member_update,
            "CHANNEL_CREATE": self._state.parse_channel_create,
            "CHANNEL_UPDATE": self._state.parse_channel_update,
            "CHANNEL_DELETE": self._state.parse_channel_delete,
            "MESSAGE_CREATE": self._state.parse_message_create,
            "MESSAGE_UPDATE": self._state.parse_message_update,
            "MESSAGE_DELETE": self._state.parse_message_delete,
            "MESSAGE_DELETE_BULK": self._state.parse_message_delete_bulk,
            "TYPING_START": self._state.parse_typing_start,
            "PRESENCE_UPDATE": self._state.parse_presence_update,
        }

    def on(self, event: str, handler: Callable):
        """Register an event handler."""
        event = event.upper()
        self._handlers[event].append(handler)
        logger.debug(f"Registered handler for event: {event}")

    def off(self, event: str, handler: Callable):
        """Unregister an event handler."""
        event = event.upper()
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)
            logger.debug(f"Removed handler for event: {event}")

    async def dispatch(self, event: str, data: dict):
        """Dispatch a gateway event."""
        event = event.upper()
        
        if event in ["GUILD_CREATE", "READY", "GUILD_UPDATE"]:
            logger.info(f"🔔 DISPATCH: {event}")
        else:
            logger.debug(f"🔄 DISPATCH: {event}")
        
        parser = self._parsers.get(event)
        result = None
        if parser:
            try:
                result = parser(data)
                logger.debug(f"Parser for {event} executed successfully")
            except Exception as e:
                logger.exception(f"Error parsing event {event}: {e}")

        handlers = self._handlers.get(event, [])
        
        if handlers:
            logger.debug(f"Event {event} has {len(handlers)} handlers to notify")
        else:
            logger.debug(f"Event {event} has no handlers registered")
        
        for handler in handlers:
            try:
                sig = inspect.signature(handler)
                params = list(sig.parameters.values())
                
                pos_count = 0
                has_var_positional = False
                for p in params:
                    if p.kind == inspect.Parameter.VAR_POSITIONAL:
                        has_var_positional = True
                        break
                    elif p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                        pos_count += 1

                if pos_count == 0 and not has_var_positional:
                    call_args = ()
                else:
                    call_args = (result or data,)

                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(*call_args))
                    logger.debug(f"Scheduled async handler for {event}")
                else:
                    handler(*call_args)
                    logger.debug(f"Executed sync handler for {event}")
                    
            except Exception as e:
                logger.exception(f"Error in event handler for {event}: {e}")