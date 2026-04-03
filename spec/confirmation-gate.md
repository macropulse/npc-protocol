# Confirmation Gates

**Version:** 0.1.0

---

## Overview

Confirmation Gates are a first-class protocol primitive for agent-to-agent authorization. When an NPC is about to take a consequential, costly, or irreversible action, it MUST pause and emit a `needs_confirmation` response before proceeding. The calling agent is then responsible for resolving the gate — either by relaying it to a human user, or by applying its own automated policy.

This is distinct from MCP's `elicitation` primitive, which asks a human user for input. Confirmation Gates are a contract between the NPC and the **calling agent**, not directly between the NPC and a human.

---

## Why This Matters

Without a standardized gate primitive:

- NPCs make destructive actions silently, or invent their own ad-hoc confirmation patterns
- Calling agents cannot build consistent "pause and ask" policies across different NPCs
- There is no way for the NPC to signal the **severity** of a required confirmation

NPC Protocol formalizes this as three gate levels with clear behavioral contracts for both sides.

---

## Gate Levels

### `advisory`

The NPC recommends confirmation but the calling agent MAY auto-approve without human input.

**Use when:** The action is significant but reversible, or the cost is non-trivial but not destructive.

**Calling agent behavior:** MAY auto-confirm based on its own policy. SHOULD log the gate event.

```json
{
  "type": "needs_confirmation",
  "session_id": "sess_abc123",
  "gate_id": "large_deployment",
  "gate_level": "advisory",
  "prompt": "This deployment will create 15 AWS resources (~$50/month). Proceed?",
  "details": {
    "resource_count": 15,
    "estimated_monthly_cost_usd": 50
  }
}
```

### `required`

The calling agent MUST obtain explicit confirmation before proceeding. Auto-approval is NOT permitted.

**Use when:** The action has significant consequences that a user should be aware of — production changes, large costs, actions that are difficult to reverse.

**Calling agent behavior:** MUST relay the prompt to the user or a human-in-the-loop mechanism. MUST NOT auto-confirm.

```json
{
  "type": "needs_confirmation",
  "session_id": "sess_abc123",
  "gate_id": "production_deploy",
  "gate_level": "required",
  "prompt": "Deploy my-app to production (affects live traffic). Confirm?",
  "details": {
    "environment": "production",
    "app": "my-app"
  }
}
```

### `destructive`

The action is **irreversible** and will permanently destroy data or resources. The calling agent MUST present the full list of affected resources to a human user before confirming. Auto-confirmation is strictly prohibited.

**Use when:** Permanent deletion of data, credentials, databases, infrastructure, or any action that cannot be undone.

**Calling agent behavior:** MUST relay the full `protected_resources` list to a human. MUST NOT auto-confirm under any circumstances. SHOULD require explicit user acknowledgment of what will be permanently lost.

```json
{
  "type": "needs_confirmation",
  "session_id": "sess_abc123",
  "gate_id": "decommission",
  "gate_level": "destructive",
  "prompt": "This will permanently destroy all infrastructure for 'my-app' in staging, including stateful resources that cannot be recovered.",
  "protected_resources": [
    {
      "type": "aws_rds_instance",
      "name": "my-app-db",
      "risk": "All database data will be permanently deleted"
    },
    {
      "type": "aws_secretsmanager_secret",
      "name": "my-app-credentials",
      "risk": "Credentials will be permanently deleted"
    },
    {
      "type": "aws_s3_bucket",
      "name": "my-app-uploads",
      "risk": "All stored files will be permanently deleted"
    }
  ]
}
```

---

## `needs_confirmation` Response Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Always `"needs_confirmation"` |
| `session_id` | string | Yes | Session to continue with confirmation reply |
| `gate_id` | string | Yes | Matches a gate declared in the NPC Card's `confirmation_gates` |
| `gate_level` | string | Yes | `"advisory"`, `"required"`, or `"destructive"` |
| `prompt` | string | Yes | Human-readable description of the action requiring confirmation |
| `details` | object | No | Structured metadata about the action (NPC-specific) |
| `protected_resources` | object[] | Required if `destructive` | List of resources that will be permanently affected |

### `protected_resources` item schema

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Resource type identifier (e.g. `"aws_rds_instance"`) |
| `name` | string | Yes | Resource name or identifier |
| `risk` | string | Yes | Human-readable description of what will be permanently lost |

---

## Responding to a Gate

### Confirming

```json
{
  "instruction": "yes, proceed",
  "session_id": "sess_abc123",
  "confirm": true
}
```

### Cancelling

```json
{
  "instruction": "no, cancel",
  "session_id": "sess_abc123",
  "confirm": false
}
```

When `confirm: false`, the NPC MUST abort the pending action and return a `completed` or `failed` response indicating the action was cancelled. The session remains open for further instructions.

---

## Calling Agent Responsibilities by Gate Level

| Gate Level | May auto-confirm? | Must show to human? | Must list protected resources? |
|---|---|---|---|
| `advisory` | Yes | No (recommended) | N/A |
| `required` | No | Yes | N/A |
| `destructive` | No | Yes | Yes — full list required |

A calling agent that auto-confirms a `required` or `destructive` gate is in violation of this spec. NPC providers SHOULD NOT rely on calling agents following this rule and SHOULD implement server-side safeguards as well.

---

## NPC Provider Responsibilities

- An NPC MUST declare all gate types it may emit in the NPC Card's `confirmation_gates` array
- An NPC MUST NOT take a `required` or `destructive` action without first emitting a `needs_confirmation` response
- An NPC SHOULD implement server-side protection for `destructive` actions independent of the calling agent's compliance
- An NPC MUST accept `confirm: false` gracefully and abort the pending action without side effects

---

## Multiple Gates in a Single Session

A session may encounter multiple confirmation gates. Each gate is independent. The calling agent resolves them sequentially. A `session_id` thread connects them:

```
execute("decommission staging") 
  --> needs_confirmation (gate_level: destructive, session_id: "sess_abc")

execute(confirm=true, session_id: "sess_abc")
  --> needs_confirmation (gate_level: required, gate_id: "final_warning", session_id: "sess_abc")

execute(confirm=true, session_id: "sess_abc")
  --> completed
```

An NPC MAY emit multiple sequential gates for the same action if the domain warrants it (e.g. a first advisory gate followed by a destructive gate).
