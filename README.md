# NPC Protocol

[繁體中文](./README.zh-TW.md)

---

**Stop selling APIs. Wrap yourself into an NPC and let it earn for you while you sleep.**

Don't sell access to your tools. Sell your soul — your domain knowledge, your workflows, your hard-earned expertise — packaged as an autonomous agent that other AI agents can hire, delegate to, and pay. You built the knowledge. Now make it work the night shift.

---

> *Your coworker became a skill. Your ex became a skill. Now it's your turn.*

---

NPC Protocol is an open standard for packaging domain knowledge as a "black box" agent service that AI agents can delegate to — in natural language, with persistent memory and explicit safety contracts. Built on top of MCP.

---

## The Problem

MCP gives AI agents tools to call. A2A lets agents route tasks between organizations. But neither answers: **how does a domain expert package their knowledge as an agent service and sell it to other AI agents?**

If you've built something like:
- A cloud deployment service driven by natural language
- A legal research agent that knows your firm's playbook
- A financial analysis NPC that wraps your proprietary models
- Any "AI-powered service" that another agent should be able to delegate complex work to

...you've probably invented your own ad-hoc conventions for: how the calling agent discovers what you can do, how you communicate progress, how you pause and require confirmation before irreversible actions, and how you maintain context across turns.

NPC Protocol names and standardizes those conventions.

---

## The NPC Metaphor

In games, NPCs (Non-Player Characters) are domain experts you interact with in natural language. They have their own knowledge, memory, and rules. Some actions require confirmation. Their internal logic is opaque — you don't see their code, you just talk to them.

That's the right mental model for a domain-expert agent service. You are the NPC. Your knowledge is the quest reward.

---

## What It Defines

Four things, built on top of MCP as transport:

**1. NPC Card** — A JSON identity document published at `npc://card`. Declares domain, instruction interface, session model, confirmation gate types, and pricing hints. How calling agents discover an NPC's capabilities.

**2. Instruction Interface** — A standard `execute` tool that accepts free-form natural language. Standard response envelope: `in_progress`, `needs_input`, `needs_confirmation`, `completed`, `failed`. Multi-turn conversations via `session_id`.

**3. Confirmation Gates** — A first-class protocol primitive for agent-to-agent authorization. Three levels: `advisory` (caller may auto-approve), `required` (must ask user), `destructive` (must show full resource list to user). The gap that doesn't exist in MCP or A2A.

**4. Session Model** — Session ownership semantics, three memory tiers (ephemeral / session / persistent), and lifecycle rules. Sessions are NPC-owned; calling agents carry opaque `session_id` tokens.

---

## What It Doesn't Define

- How your NPC implements its logic (LLM, rules, hardcoded — your choice)
- Whether your NPC uses AI internally at all
- Payment processing (pricing hints only)
- NPC discovery/registry
- The calling agent's internals

---

## Quick Start (Python SDK)

```bash
pip install npc-protocol
```

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
        # Pause and require confirmation before destructive action
        return ctx.require_confirmation(
            gate_id="delete_zone",
            gate_level=GateLevel.DESTRUCTIVE,
            prompt="This will permanently delete the zone and all its records.",
            protected_resources=[
                {"type": "dns_zone", "name": "example.com", "risk": "All DNS records deleted"}
            ],
        )

    # Your domain logic here
    return ctx.complete(result="DNS record updated")

npc.run()
```

The calling agent interacts with this over MCP:

```python
# Calling agent reads the NPC Card first
card = mcp.call("resources/read", {"uri": "npc://card"})

# Sends a natural language instruction
result = mcp.call("execute", {"instruction": "delete the example.com zone"})
# --> needs_confirmation (gate_level: destructive)

# Relays to user, gets confirmation, sends it back
result = mcp.call("execute", {"instruction": "yes", "session_id": result["session_id"], "confirm": True})
# --> completed
```

---

## Architecture

```
CUSTOMER'S SIDE
  [ User ]
     | natural language
     v
  [ Calling Agent ]   <-- customer builds this however they want
     |
     | MCP calls
     v
NPC PROTOCOL LAYER  <-- this spec
  [ NPC Card ]  [ execute tool ]  [ Confirmation Gates ]  [ Session Model ]
     |
     | SDK implements protocol surface
     v
NPC PROVIDER'S SIDE
  [ NPC SDK ]
     |
     v
  [ Your Instruction Handler ]   <-- you write this
     |                 |
     v                 v
[ Your AI /       [ Your Backend ]
  Orchestration ]   (APIs, DBs, services)
```

The protocol boundary is only the middle layer. Everything above and below is the implementer's responsibility.

---

## Positioning

| Protocol | What it handles |
|---|---|
| MCP | Typed tool calls, resources, prompts between host and server |
| A2A | Cross-org task routing between agents |
| **NPC Protocol** | **Domain-expert agent packaging: NL interface, identity, safety gates, session semantics** |

NPC Protocol rides on top of MCP (not a replacement) and is complementary to A2A.

---

## Example: Code Reviewer NPC

[`examples/code-reviewer-npc/`](examples/code-reviewer-npc/) — a fully working NPC that wraps a senior engineer's code review opinions as a sellable service. Shows knowledge packaging, session memory, and a confirmation gate in ~150 lines.

```bash
git clone https://github.com/macropulse/npc-protocol
cd npc-protocol/examples/code-reviewer-npc
pip install npc-protocol openai
export OPENAI_API_KEY=sk-...
python main.py
```

The reviewer's persona — red lines, strong preferences, style notes — lives at the top of `main.py`. **Change it and you have a completely different product.**

---

## Production Reference: SwiftDeploy

[SwiftDeploy](https://swiftdeploy.ai) independently converged on this pattern before the spec was written. See the full case study: [`sdk/python/examples/swiftdeploy_case_study.md`](sdk/python/examples/swiftdeploy_case_study.md).

---

## Spec

- [`spec/README.md`](spec/README.md) — Overview and motivation
- [`spec/npc-card.md`](spec/npc-card.md) — NPC Card specification
- [`spec/instruction-interface.md`](spec/instruction-interface.md) — Instruction interface
- [`spec/confirmation-gate.md`](spec/confirmation-gate.md) — Confirmation gate primitives
- [`spec/session-model.md`](spec/session-model.md) — Session and memory semantics

---

## Status

**v0.1.0 — Draft.** The spec and SDK are in active development. Breaking changes may occur before v1.0.

Feedback and contributions welcome. Open an issue or a pull request.

---

## License

Apache 2.0
