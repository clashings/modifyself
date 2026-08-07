"""
Relationship models (friends, blocks, etc.)
"""

from typing import Optional, Dict, Any
from .base import DiscordObject

class Relationship(DiscordObject):
    """Represents a relationship (friend, block, etc.)."""
    
    __slots__ = (
        "user_id",
        "type",
        "nickname",
        "since",
        "user",
    )
    
    def __init__(self, *, state, data: dict):
        super().__init__(state=state, data=data)
        self._update(data)
    
    def _update(self, data: dict):
        self.user_id = int(data.get("user_id", 0))
        self.type = data.get("type", 0)  # 1=friends, 2=blocked, 3=incoming, 4=outgoing
        self.nickname = data.get("nickname")
        self.since = data.get("since")
        self.user = data.get("user")
    
    @property
    def is_friend(self) -> bool:
        return self.type == 1
    
    @property
    def is_blocked(self) -> bool:
        return self.type == 2
    
    @property
    def is_incoming_request(self) -> bool:
        return self.type == 3
    
    @property
    def is_outgoing_request(self) -> bool:
        return self.type == 4
    
    def __repr__(self) -> str:
        return f"<Relationship id={self.id} type={self.type}>"