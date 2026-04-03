# npc-protocol

Python SDK for building [NPC Protocol](https://github.com/macropulse/npc-protocol) servers.

**Stop selling APIs. Wrap yourself into an NPC and let it earn for you while you sleep.**

---

## What is NPC Protocol?

NPC Protocol is an open standard for packaging domain knowledge as a "black box" agent service that AI agents can delegate to — in natural language, with persistent memory and explicit safety contracts. Built on top of MCP.

> *Your coworker became a skill. Your ex became a skill. Now it's your turn.*

## Install

```bash
pip install npc-protocol
```

## Quick Start

```python
from npc import NPCServer, NPCCard, NPCContext
from npc.response import GateLevel

card = NPCCard(
    name="DNS Manager",
    domain="DNS record management",
    confirmation_gates=[
        {"id": "delete_zone", "level": "destructive", "description": "Deleting a DNS zone"}
    ],
)

npc = NPCServer(card=card)

@npc.instruction_handler
async def handle(instruction: str, session_id: str, ctx: NPCContext):
    if "delete" in instruction.lower():
        return ctx.require_confirmation(
            gate_id="delete_zone",
            gate_level=GateLevel.DESTRUCTIVE,
            prompt="This will permanently delete the zone and all its records.",
            protected_resources=[
                {"type": "dns_zone", "name": "example.com", "risk": "All DNS records deleted"}
            ],
        )
    return ctx.complete(result="DNS record updated")

npc.run()
```

## Links

- [Full spec and docs](https://github.com/macropulse/npc-protocol)
- [NPC Card spec](https://github.com/macropulse/npc-protocol/blob/main/spec/npc-card.md)
- [Confirmation Gates spec](https://github.com/macropulse/npc-protocol/blob/main/spec/confirmation-gate.md)

## License

Apache 2.0
