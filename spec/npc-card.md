# NPC Card

**Version:** 0.1.0

---

## Overview

The NPC Card is a JSON document that an NPC server publishes as an MCP resource at the URI `npc://card`. It is the identity and capability declaration for an NPC — the first thing a calling agent reads before sending any instructions.

The NPC Card answers three questions for the calling agent:
1. What domain does this NPC cover, and can it handle my task?
2. How do I interact with it (instruction interface, session model, confirmation behavior)?
3. What will it cost and what should I expect in terms of safety gates?

---

## Publishing the NPC Card

An NPC server MUST expose the NPC Card as an MCP resource with URI `npc://card` and MIME type `application/json`.

```
Resource URI:  npc://card
MIME type:     application/json
Access:        MCP resources/read
```

A calling agent reads it via a standard MCP `resources/read` call:

```json
{
  "method": "resources/read",
  "params": { "uri": "npc://card" }
}
```

---

## NPC Card Schema

### Full Example

```json
{
  "npc_protocol_version": "0.1.0",
  "name": "SwiftDeploy",
  "version": "1.0.0",
  "domain": "cloud infrastructure deployment and management",
  "description": "Deploys, manages, and decommissions cloud infrastructure on AWS. Handles ECS, RDS, Redis, S3, and related services via Terraform.",
  "instruction_interface": "natural_language",
  "capability_opacity": "opaque",
  "session_model": "persistent",
  "confirmation_gates": [
    {
      "id": "production_deploy",
      "level": "required",
      "description": "Deploying to a production environment"
    },
    {
      "id": "decommission",
      "level": "destructive",
      "description": "Destroying infrastructure and stateful resources"
    }
  ],
  "pricing_hints": {
    "model": "credits",
    "unit": "session",
    "approximate_cost": "10-50 credits"
  },
  "contact": "https://swiftdeploy.ai",
  "mcp_tools": ["execute"]
}
```

---

## Field Reference

### Required Fields

| Field | Type | Description |
|---|---|---|
| `npc_protocol_version` | string | Version of NPC Protocol this card conforms to (e.g. `"0.1.0"`) |
| `name` | string | Human-readable name of the NPC service |
| `domain` | string | Plain-language description of the domain this NPC covers |
| `instruction_interface` | string | How instructions are accepted. See [Instruction Interface values](#instruction_interface-values). |
| `capability_opacity` | string | Whether the NPC exposes its internal tools. See [Capability Opacity values](#capability_opacity-values). |
| `session_model` | string | Session persistence behavior. See [Session Model values](#session_model-values). |
| `mcp_tools` | string[] | List of MCP tool names this NPC exposes. MUST include `"execute"` if `instruction_interface` is `natural_language`. |

### Optional Fields

| Field | Type | Description |
|---|---|---|
| `version` | string | The NPC service's own version string |
| `description` | string | Longer description of the NPC's capabilities, suitable for display to a user |
| `confirmation_gates` | object[] | Declared gate types this NPC may emit. See [Confirmation Gates](#confirmation_gates). |
| `pricing_hints` | object | Non-binding pricing metadata. See [Pricing Hints](#pricing_hints). |
| `contact` | string | URL or email for the NPC provider |

---

## Field Values

### `instruction_interface` values

| Value | Meaning |
|---|---|
| `natural_language` | The NPC accepts free-form text instructions via the `execute` tool. The NPC is responsible for interpretation. |
| `structured` | The NPC accepts structured parameters via typed MCP tool schemas. `execute` is not required. |

Most NPCs will declare `natural_language`. The `structured` value is provided for NPCs that prefer typed interfaces over free-form instructions.

### `capability_opacity` values

| Value | Meaning |
|---|---|
| `opaque` | The NPC does not expose a meaningful `tools/list` describing its internal logic. Calling agents interact only through `execute`. The NPC's implementation is a black box. |
| `transparent` | The NPC exposes its full tool list via MCP `tools/list`. Calling agents may call internal tools directly. |

NPCs packaging proprietary domain knowledge SHOULD declare `opaque`.

### `session_model` values

| Value | Meaning |
|---|---|
| `ephemeral` | No session state is maintained. Each `execute` call is independent. |
| `session` | State is maintained within a session (while `session_id` is active), but not across sessions. |
| `persistent` | State persists across sessions for the same calling agent / project context. |

See [`session-model.md`](./session-model.md) for full semantics.

---

## `confirmation_gates`

An array of gate declarations. Each object describes a type of gate this NPC may emit during execution. Declaring gates upfront lets the calling agent prepare its user and policy before work begins.

```json
"confirmation_gates": [
  {
    "id": "production_deploy",
    "level": "required",
    "description": "Deploying to a production environment requires explicit confirmation"
  },
  {
    "id": "decommission",
    "level": "destructive",
    "description": "Destroying infrastructure permanently deletes stateful resources"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Machine-readable gate identifier, referenced in `needs_confirmation` responses |
| `level` | string | `advisory`, `required`, or `destructive`. See [`confirmation-gate.md`](./confirmation-gate.md). |
| `description` | string | Human-readable explanation of when this gate is triggered |

---

## `pricing_hints`

Non-binding metadata to help calling agents estimate cost before initiating a session. Actual billing is outside the scope of NPC Protocol.

```json
"pricing_hints": {
  "model": "credits",
  "unit": "session",
  "approximate_cost": "10-50 credits",
  "free_tier": "3 sessions/month"
}
```

| Field | Type | Description |
|---|---|---|
| `model` | string | Pricing model: `"credits"`, `"subscription"`, `"pay_per_use"`, `"free"` |
| `unit` | string | Billing unit: `"session"`, `"instruction"`, `"token"`, `"minute"` |
| `approximate_cost` | string | Non-binding human-readable cost estimate |
| `free_tier` | string | Optional description of any free tier |

---

## Versioning and Compatibility

A calling agent MUST check `npc_protocol_version` and warn if the major version is higher than what the calling agent supports. Minor version differences (e.g. `0.1.0` vs `0.2.0`) are expected to be backwards compatible within the `0.x` draft series.

---

## Minimal Valid NPC Card

```json
{
  "npc_protocol_version": "0.1.0",
  "name": "My NPC",
  "domain": "describe what your NPC does",
  "instruction_interface": "natural_language",
  "capability_opacity": "opaque",
  "session_model": "session",
  "mcp_tools": ["execute"]
}
```
