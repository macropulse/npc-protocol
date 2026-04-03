"""
Session store interface and built-in implementations.

Sessions are NPC-owned. The calling agent only carries the opaque session_id token.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any


class SessionStore(ABC):
    """
    Abstract interface for NPC session storage.
    Implement this to plug in Redis, a database, or any other backend.
    """

    @abstractmethod
    async def create(self, data: dict[str, Any] | None = None) -> str:
        """Create a new session and return its session_id."""
        ...

    @abstractmethod
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session data by session_id.
        Returns None if the session does not exist or has expired.
        """
        ...

    @abstractmethod
    async def update(self, session_id: str, data: dict[str, Any]) -> bool:
        """
        Update session data. Returns False if the session does not exist.
        """
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Terminate a session. Returns False if it did not exist."""
        ...

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check whether a session exists and has not expired."""
        ...

    @classmethod
    def in_memory(cls, ttl_seconds: int = 86400) -> "InMemorySessionStore":
        """Factory: create an in-memory session store (default, suitable for development)."""
        return InMemorySessionStore(ttl_seconds=ttl_seconds)


class InMemorySessionStore(SessionStore):
    """
    Simple in-memory session store. Not suitable for production multi-process deployments.
    Sessions expire after ttl_seconds of inactivity (default 24 hours).
    """

    def __init__(self, ttl_seconds: int = 86400) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _is_expired(self, session: dict[str, Any]) -> bool:
        return time.time() - session.get("_last_accessed", 0) > self._ttl

    async def create(self, data: dict[str, Any] | None = None) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        self._store[session_id] = {
            **(data or {}),
            "_created_at": time.time(),
            "_last_accessed": time.time(),
        }
        return session_id

    async def get(self, session_id: str) -> dict[str, Any] | None:
        session = self._store.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            del self._store[session_id]
            return None
        session["_last_accessed"] = time.time()
        return {k: v for k, v in session.items() if not k.startswith("_")}

    async def update(self, session_id: str, data: dict[str, Any]) -> bool:
        if session_id not in self._store or self._is_expired(self._store[session_id]):
            return False
        self._store[session_id].update(data)
        self._store[session_id]["_last_accessed"] = time.time()
        return True

    async def delete(self, session_id: str) -> bool:
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    async def exists(self, session_id: str) -> bool:
        session = self._store.get(session_id)
        if session is None:
            return False
        if self._is_expired(session):
            del self._store[session_id]
            return False
        return True
