"""
NPC Protocol — Python SDK

Build domain-expert agent services that AI agents can delegate to.

Quick start:

    from npc import NPCServer, NPCCard, NPCContext
    from npc.response import GateLevel

    card = NPCCard(
        name="My NPC",
        domain="describe what your NPC does",
    )

    npc = NPCServer(card=card)

    @npc.instruction_handler
    async def handle(instruction: str, session_id: str, ctx: NPCContext):
        return ctx.complete(result="Done")

    npc.run()
"""

from .card import (
    CapabilityOpacity,
    ConfirmationGateDeclaration,
    InstructionInterface,
    NPCCard,
    PricingHints,
    PricingModel,
    SessionModelType,
)
from .context import NPCContext
from .response import (
    CompletedResponse,
    FailedResponse,
    GateLevel,
    InProgressResponse,
    NeedsConfirmationResponse,
    NeedsInputResponse,
    NPCResponse,
    ProtectedResource,
    ResponseType,
)
from .server import NPCServer
from .session import InMemorySessionStore, SessionStore

__version__ = "0.1.0"
__all__ = [
    "NPCServer",
    "NPCCard",
    "NPCContext",
    "SessionStore",
    "InMemorySessionStore",
    # Response types
    "NPCResponse",
    "InProgressResponse",
    "NeedsInputResponse",
    "NeedsConfirmationResponse",
    "CompletedResponse",
    "FailedResponse",
    "ProtectedResource",
    # Enums
    "ResponseType",
    "GateLevel",
    "InstructionInterface",
    "CapabilityOpacity",
    "SessionModelType",
    "PricingModel",
    "ConfirmationGateDeclaration",
    "PricingHints",
]
