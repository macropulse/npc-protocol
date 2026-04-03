# Instruction Interface

**Version:** 0.1.0

---

## Overview

The Instruction Interface defines the standard contract for natural language communication between a calling agent and an NPC. It specifies the `execute` tool that every `natural_language` NPC must expose, the response envelope format, and the patterns for multi-turn conversations via `session_id`.

---

## The `execute` Tool

An NPC that declares `instruction_interface: natural_language` in its NPC Card MUST expose an MCP tool named `execute`.

### Input Schema

```json
{
  "name": "execute",
  "description": "Send a natural language instruction to the NPC",
  "inputSchema": {
    "type": "object",
    "required": ["instruction"],
    "properties": {
      "instruction": {
        "type": "string",
        "description": "A natural language instruction or reply to the NPC"
      },
      "session_id": {
        "type": "string",
        "description": "Resume an existing session. Omit to start a new session."
      },
      "confirm": {
        "type": "boolean",
        "description": "Confirmation reply to a needs_confirmation gate"
      },
      "choice": {
        "type": "string",
        "description": "Selection reply to a needs_input response with options"
      }
    }
  }
}
```

The NPC MAY define additional input parameters beyond these. All parameters beyond `instruction` are OPTIONAL. The calling agent MUST NOT be required to understand NPC-specific parameters to initiate a session.

---

## Response Envelope

All responses from `execute` MUST be JSON and MUST include a `type` field. The `type` field determines which other fields are present.

### Common Fields (all response types)

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Response type. One of the values defined below. |
| `session_id` | string | Yes (if session_model != ephemeral) | The session identifier for continuing this conversation |
| `message` | string | No | Human-readable status message |

---

## Response Types

### `in_progress`

The NPC has accepted the instruction and is working. Used for long-running operations where intermediate status is meaningful.

```json
{
  "type": "in_progress",
  "session_id": "sess_abc123",
  "message": "Provisioning infrastructure, this may take a few minutes...",
  "progress": {
    "step": "creating_database",
    "elapsed_seconds": 45
  }
}
```

The calling agent SHOULD poll or wait for a terminal response (`completed` or `failed`) after receiving `in_progress`. How to poll (e.g. a separate `get_status` tool) is the NPC's implementation choice.

### `needs_input`

The NPC requires clarification before it can proceed. The calling agent MUST relay this to the user or resolve it according to its own policy.

```json
{
  "type": "needs_input",
  "session_id": "sess_abc123",
  "question": "Which environment do you want to deploy to?",
  "options": ["staging", "production"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | string | Yes | The question or prompt for the calling agent / user |
| `options` | string[] | No | If present, the calling agent SHOULD restrict replies to one of these values via the `choice` parameter |

**Continuing after `needs_input`:**

```json
{
  "instruction": "staging",
  "session_id": "sess_abc123",
  "choice": "staging"
}
```

### `needs_confirmation`

The NPC is about to take a consequential action and requires authorization. See [`confirmation-gate.md`](./confirmation-gate.md) for full semantics and gate levels.

```json
{
  "type": "needs_confirmation",
  "session_id": "sess_abc123",
  "gate_id": "production_deploy",
  "gate_level": "required",
  "prompt": "Deploy my-app to production (this will cause ~30 seconds of downtime). Confirm?",
  "details": {
    "environment": "production",
    "estimated_downtime_seconds": 30
  }
}
```

**Continuing after `needs_confirmation`:**

```json
{
  "instruction": "yes",
  "session_id": "sess_abc123",
  "confirm": true
}
```

Or to cancel:

```json
{
  "instruction": "no",
  "session_id": "sess_abc123",
  "confirm": false
}
```

### `completed`

The instruction has been executed successfully. This is a terminal response.

```json
{
  "type": "completed",
  "session_id": "sess_abc123",
  "result": "Deployment successful. App is live at https://my-app.example.com",
  "data": {
    "app_url": "https://my-app.example.com",
    "deployment_id": "dep_xyz789"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `result` | string | Yes | Human-readable summary of what was done |
| `data` | object | No | Structured result data. Contents are NPC-specific. |

### `failed`

The instruction could not be completed. This is a terminal response. The calling agent MUST surface `recovery_hint` to the user.

```json
{
  "type": "failed",
  "session_id": "sess_abc123",
  "error": "Infrastructure provisioning failed: RDS subnet group already exists",
  "recovery_hint": "Run execute('delete the stale subnet group') and then retry deployment.",
  "retryable": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `error` | string | Yes | Machine-readable or human-readable error description |
| `recovery_hint` | string | **Yes** | Actionable instruction for the calling agent to recover. MUST always be present on `failed`. |
| `retryable` | boolean | No | Whether the same instruction can be retried directly |

---

## Multi-Turn Conversation Pattern

Sessions allow a calling agent and NPC to maintain context across multiple `execute` calls. The `session_id` returned in any response MUST be passed back in subsequent calls to continue the same conversation.

```
Call 1:  execute(instruction="deploy my app")
         --> {type: "needs_input", session_id: "sess_abc", question: "Which environment?"}

Call 2:  execute(instruction="staging", session_id="sess_abc", choice="staging")
         --> {type: "in_progress", session_id: "sess_abc", message: "Deploying..."}

Call 3:  execute(instruction="status", session_id="sess_abc")
         --> {type: "needs_confirmation", session_id: "sess_abc", gate_level: "required", ...}

Call 4:  execute(instruction="yes", session_id="sess_abc", confirm=true)
         --> {type: "completed", session_id: "sess_abc", result: "Deployed successfully"}
```

The `session_id` is opaque to the calling agent. It MUST NOT attempt to parse or construct `session_id` values.

---

## Error Handling Requirements

- An NPC MUST return `type: "failed"` (not an MCP protocol error) for domain-level failures
- An NPC MUST include `recovery_hint` on every `failed` response
- An NPC MUST return an MCP protocol error only for protocol-level failures (invalid tool call, authentication failure, etc.)
- A calling agent MUST distinguish between MCP protocol errors and NPC `failed` responses and handle them separately

---

## Implementation Notes

The `execute` tool is intentionally minimal. NPC providers are free to:

- Add additional MCP tools alongside `execute` (e.g. `get_status`, `write_memory`) for non-instruction operations
- Add custom parameters to `execute` beyond the standard set
- Stream progress via SSE on the MCP transport for long-running operations

What they MUST NOT do:

- Remove the `type` field from any response
- Omit `recovery_hint` from a `failed` response
- Return a `session_id` that changes mid-conversation for the same session
