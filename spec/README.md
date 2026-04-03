# NPC Protocol — Specification Overview

**Version:** 0.1.0
**Status:** Draft

---

## The Problem

The AI agent ecosystem has two well-defined layers:

- **MCP (Model Context Protocol)** — lets an AI agent call typed tools exposed by a server
- **A2A (Agent-to-Agent)** — lets one agent send tasks to another agent across organizational boundaries

Neither defines what sits in between: a **domain-expert agent service** that a calling agent can delegate complex, multi-step work to, in natural language, with persistent memory and explicit safety contracts.

Today, if you want to sell your domain expertise (cloud infrastructure, legal research, financial analysis, DNS management) as a service that AI agents can consume, there is no standard way to:

- Package your knowledge as a discoverable, identifiable agent service
- Declare a natural language instruction interface as a formal contract
- Define safety gates where the calling agent must confirm before you take a consequential action
- Maintain session memory across multiple turns with a specific calling agent
- Signal your pricing model to the calling agent

Every implementation invents its own conventions. NPC Protocol names and standardizes this pattern.

---

## The NPC Metaphor

In games, NPCs (Non-Player Characters) are autonomous agents with their own domain knowledge, personalities, and rules. You interact with them in natural language. They remember your history. Some actions require confirmation ("Are you sure you want to sell all your items?"). Their internal logic is opaque — you don't see their code, you just interact with the interface they present.

This is exactly the pattern for domain-expert agent services:

- **The NPC provider** packages their domain knowledge and business logic into a service
- **The calling agent** (the player) delegates tasks to the NPC in natural language
- **The NPC** handles complexity internally, maintains session state, and pauses for confirmation at critical steps
- **The internal implementation** — whether it uses an LLM, a rule engine, or hardcoded logic — is entirely opaque to the caller

---

## What NPC Protocol Defines

NPC Protocol is a thin specification layer that sits **on top of MCP** (as transport) and is **complementary to A2A** (for cross-org discovery). It defines five things:

### 1. [NPC Card](./npc-card.md)
A JSON identity document published as an MCP resource at `npc://card`. Declares the NPC's domain, instruction interface type, session model, confirmation gate types, pricing hints, and a pointer to the Skill File. This is how calling agents discover what an NPC can do before sending any instructions.

### 2. [Instruction Interface](./instruction-interface.md)
A standard contract for natural language instruction exchange. Every NPC exposes a single MCP tool — `execute` — that accepts free-form text instructions. The response envelope defines standard types (`in_progress`, `needs_input`, `needs_confirmation`, `completed`, `failed`) and threading via `session_id`.

### 3. [Confirmation Gates](./confirmation-gate.md)
A first-class protocol primitive for agent-to-agent authorization. When an NPC is about to take a consequential or irreversible action, it pauses and emits a `needs_confirmation` response. The calling agent must relay this to its user or resolve it according to its own policy. Gate levels define whether auto-approval is permitted.

### 4. [Session Model](./session-model.md)
Defines session ownership, memory tiers, and lifecycle semantics. Sessions are NPC-owned. Three memory tiers are defined: ephemeral (call-scoped), session (multi-turn), and persistent (cross-session). Calling agents thread sessions via `session_id`.

### 5. [Skill File](./skill-file.md)
A versioned Markdown document published at `npc://skill` that teaches calling agents how to operate the NPC correctly. Where the NPC Card says *what* the NPC can do, the Skill File says *how* to use it well — primary interface patterns, response extensions, operational timing constraints, and ordered best practices. The NPC injects `skill_version` into every response so calling agents detect when the Skill File has been updated.

---

## What NPC Protocol Does NOT Define

- **How the NPC implements its logic** — LLM, rules, hardcoded logic, or any combination
- **How the NPC runs its AI or orchestration** — entirely the provider's concern
- **Payment processing** — pricing hints are included in the NPC Card, but actual billing is out of scope
- **NPC discovery/registry** — how calling agents find NPCs is not specified in v0.1
- **The calling agent's internals** — the protocol only defines the surface between caller and NPC

---

## Architecture

```
CUSTOMER'S SIDE
  [ User ]
     | natural language
     v
  [ Calling Agent ]   <-- customer builds this however they want
     | loads npc://skill on connect, reloads on skill_version drift
     | MCP calls
     v
NPC PROTOCOL LAYER  <-- this spec
  [ NPC Card ]  [ Skill File ]  [ execute tool ]  [ Confirmation Gates ]  [ Session Model ]
  npc://card    npc://skill     standard tool      advisory/required/      ephemeral/session/
                npc://skill-    + response         destructive levels      persistent tiers
                version         envelope
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

## Positioning Relative to Existing Protocols

| Protocol | Layer | What it handles |
|---|---|---|
| MCP | Transport + tool primitives | Typed tool calls, resources, prompts between host and server |
| A2A | Cross-org task routing | Sending tasks between agents at different organizations |
| **NPC Protocol** | **Domain-expert agent packaging** | **NL instruction interface, identity, skill file, safety gates, session semantics** |

NPC Protocol does not compete with MCP or A2A. An NPC server:
- **Uses MCP** as its transport (NPC Card is an MCP resource, `execute` is an MCP tool)
- **Can publish an A2A Agent Card** for cross-org discovery
- **Adds the NPC Protocol layer** on top for the instruction interface, gates, and session model

---

## Production Reference: SwiftDeploy

[SwiftDeploy](https://swiftdeploy.ai) is a cloud infrastructure deployment service that independently converged on this pattern before NPC Protocol was named. It is used as the production reference implementation throughout the spec.

SwiftDeploy's NPC Card, confirmation gate flows, and session memory model are documented in [`../sdk/python/examples/swiftdeploy_case_study.md`](../sdk/python/examples/swiftdeploy_case_study.md).

---

## Spec Documents

- [`npc-card.md`](./npc-card.md) — NPC Card specification
- [`skill-file.md`](./skill-file.md) — Skill File specification
- [`instruction-interface.md`](./instruction-interface.md) — Natural language instruction interface
- [`confirmation-gate.md`](./confirmation-gate.md) — Confirmation gate primitives
- [`session-model.md`](./session-model.md) — Session and memory semantics

---

## Versioning

The spec follows semantic versioning. Breaking changes increment the minor version during the `0.x` draft period. The `npc_protocol_version` field in the NPC Card carries the spec version the server was built against.
