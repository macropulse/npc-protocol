"""
NPCContext — per-request context passed to instruction handlers.

Provides helper methods to construct spec-compliant responses without
manually building response dicts.
"""

from __future__ import annotations

from typing import Any

from .response import (
    CompletedResponse,
    FailedResponse,
    GateLevel,
    InProgressResponse,
    NeedsConfirmationResponse,
    NeedsInputResponse,
    NPCResponse,
    ProtectedResource,
)
from .session import SessionStore


class NPCContext:
    """
    Context object injected into every instruction handler call.

    Provides the current session state and helper methods for building
    spec-compliant NPC Protocol responses.
    """

    def __init__(
        self,
        session_id: str,
        session_store: SessionStore,
        session_data: dict[str, Any],
    ) -> None:
        self.session_id = session_id
        self._store = session_store
        self._data = session_data

    # -- Session helpers --

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the current session data."""
        return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Persist a value to the current session."""
        self._data[key] = value
        await self._store.update(self.session_id, {key: value})

    async def clear(self) -> None:
        """Terminate the current session."""
        await self._store.delete(self.session_id)

    # -- Response builders --

    def in_progress(
        self,
        message: str,
        progress: dict[str, Any] | None = None,
    ) -> NPCResponse:
        return InProgressResponse(
            session_id=self.session_id,
            message=message,
            progress=progress,
        )

    def needs_input(
        self,
        question: str,
        options: list[str] | None = None,
        message: str | None = None,
    ) -> NPCResponse:
        return NeedsInputResponse(
            session_id=self.session_id,
            question=question,
            options=options,
            message=message,
        )

    def require_confirmation(
        self,
        gate_id: str,
        gate_level: GateLevel,
        prompt: str,
        details: dict[str, Any] | None = None,
        protected_resources: list[dict[str, str]] | None = None,
        message: str | None = None,
    ) -> NPCResponse:
        """
        Emit a confirmation gate. The calling agent must resolve this before
        the NPC can proceed.

        For gate_level=DESTRUCTIVE, protected_resources should list all
        resources that will be permanently affected.
        """
        resources = None
        if protected_resources:
            resources = [ProtectedResource(**r) for r in protected_resources]

        return NeedsConfirmationResponse(
            session_id=self.session_id,
            gate_id=gate_id,
            gate_level=gate_level,
            prompt=prompt,
            details=details,
            protected_resources=resources,
            message=message,
        )

    def complete(
        self,
        result: str,
        data: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> NPCResponse:
        return CompletedResponse(
            session_id=self.session_id,
            result=result,
            data=data,
            message=message,
        )

    def fail(
        self,
        error: str,
        recovery_hint: str,
        retryable: bool = False,
        message: str | None = None,
    ) -> NPCResponse:
        """
        Return a failure response. recovery_hint is required by the NPC Protocol spec
        and must always be a concrete, actionable instruction.
        """
        return FailedResponse(
            session_id=self.session_id,
            error=error,
            recovery_hint=recovery_hint,
            retryable=retryable,
            message=message,
        )
