"""
NPC Card — the identity and capability declaration for an NPC server.

Published as an MCP resource at npc://card.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InstructionInterface(str, Enum):
    NATURAL_LANGUAGE = "natural_language"
    STRUCTURED = "structured"


class CapabilityOpacity(str, Enum):
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"


class SessionModelType(str, Enum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    PERSISTENT = "persistent"


class GateLevel(str, Enum):
    ADVISORY = "advisory"
    REQUIRED = "required"
    DESTRUCTIVE = "destructive"


class PricingModel(str, Enum):
    CREDITS = "credits"
    SUBSCRIPTION = "subscription"
    PAY_PER_USE = "pay_per_use"
    FREE = "free"


class ConfirmationGateDeclaration(BaseModel):
    id: str = Field(..., description="Machine-readable gate identifier")
    level: GateLevel
    description: str = Field(..., description="Human-readable explanation of when this gate triggers")


class PricingHints(BaseModel):
    model: PricingModel
    unit: str = Field(..., description="Billing unit: session, instruction, token, minute")
    approximate_cost: str | None = None
    free_tier: str | None = None


class NPCCard(BaseModel):
    """
    The NPC Card identifies an NPC server and declares its capabilities.
    Published as an MCP resource at npc://card.
    """

    npc_protocol_version: str = Field(default="0.1.0", description="NPC Protocol spec version")
    name: str = Field(..., description="Human-readable name of the NPC service")
    domain: str = Field(..., description="Plain-language description of the domain this NPC covers")
    instruction_interface: InstructionInterface = InstructionInterface.NATURAL_LANGUAGE
    capability_opacity: CapabilityOpacity = CapabilityOpacity.OPAQUE
    session_model: SessionModelType = SessionModelType.SESSION
    mcp_tools: list[str] = Field(default_factory=lambda: ["execute"])

    # Optional fields
    version: str | None = None
    description: str | None = None
    confirmation_gates: list[ConfirmationGateDeclaration] = Field(default_factory=list)
    pricing_hints: PricingHints | None = None
    contact: str | None = None
    skill_file_uri: str | None = Field(default=None, description="URI of the Skill File resource (default: npc://skill)")
    skill_version: str | None = Field(default=None, description="Current version of the Skill File")

    def model_post_init(self, __context: Any) -> None:
        # Enforce spec: natural_language NPCs must expose execute
        if (
            self.instruction_interface == InstructionInterface.NATURAL_LANGUAGE
            and "execute" not in self.mcp_tools
        ):
            self.mcp_tools = ["execute", *self.mcp_tools]

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
