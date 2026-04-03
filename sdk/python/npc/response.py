"""
Standard response types for NPC Protocol.

All execute() calls return one of these response envelopes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    IN_PROGRESS = "in_progress"
    NEEDS_INPUT = "needs_input"
    NEEDS_CONFIRMATION = "needs_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"


class GateLevel(str, Enum):
    ADVISORY = "advisory"
    REQUIRED = "required"
    DESTRUCTIVE = "destructive"


class ProtectedResource(BaseModel):
    type: str = Field(..., description="Resource type identifier (e.g. 'aws_rds_instance')")
    name: str = Field(..., description="Resource name or identifier")
    risk: str = Field(..., description="Human-readable description of what will be permanently lost")


class NPCResponse(BaseModel):
    type: ResponseType
    session_id: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class InProgressResponse(NPCResponse):
    type: ResponseType = ResponseType.IN_PROGRESS
    progress: dict[str, Any] | None = None


class NeedsInputResponse(NPCResponse):
    type: ResponseType = ResponseType.NEEDS_INPUT
    question: str
    options: list[str] | None = None


class NeedsConfirmationResponse(NPCResponse):
    type: ResponseType = ResponseType.NEEDS_CONFIRMATION
    gate_id: str
    gate_level: GateLevel
    prompt: str
    details: dict[str, Any] | None = None
    protected_resources: list[ProtectedResource] | None = None


class CompletedResponse(NPCResponse):
    type: ResponseType = ResponseType.COMPLETED
    result: str
    data: dict[str, Any] | None = None


class FailedResponse(NPCResponse):
    type: ResponseType = ResponseType.FAILED
    error: str
    recovery_hint: str  # Required by spec — always present on failed
    retryable: bool = False
