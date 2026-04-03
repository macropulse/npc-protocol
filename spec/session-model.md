# Session Model

**Version:** 0.1.0

---

## Overview

The Session Model defines how NPC servers maintain context across multiple `execute` calls, who owns that state, and what guarantees the calling agent can rely on. Sessions enable multi-turn conversations where the NPC builds up context incrementally rather than requiring the calling agent to re-explain everything on each call.

---

## Core Principles

1. **Sessions are NPC-owned.** The NPC controls session creation, storage, and termination. The calling agent does not manage session state — it only carries the opaque `session_id` token.

2. **`session_id` is opaque.** Calling agents MUST NOT attempt to parse, construct, or derive meaning from `session_id` values. They are handles, not structured data.

3. **Session continuity is the caller's responsibility.** The calling agent MUST pass `session_id` in every subsequent call to maintain continuity. Omitting `session_id` starts a new session.

4. **Memory tiers are declared in the NPC Card.** The `session_model` field tells the calling agent what persistence to expect before any work begins.

---

## Session Model Values

Declared in the NPC Card as `session_model`. Three values are defined:

### `ephemeral`

No session state is maintained between calls. Each `execute` is fully independent. The NPC MAY still return a `session_id` for multi-turn flows within a single logical request, but that state is not guaranteed to persist beyond the immediate exchange.

**Appropriate for:** Stateless NPCs (e.g. a translation NPC, a code formatter).

### `session`

State is maintained for the duration of an active session. Once a session ends (by timeout, explicit termination, or inactivity), the state is discarded. Starting a new `execute` without a `session_id` creates a fresh session with no memory of prior sessions.

**Appropriate for:** NPCs where context is needed within a task but cross-task history is not meaningful.

### `persistent`

State persists across sessions, keyed to a stable project or user context. A calling agent that returns after days or weeks will find the NPC still has memory of previous work. This enables NPCs to maintain long-term project context, learned preferences, and historical records.

**Appropriate for:** NPCs managing ongoing infrastructure, long-running projects, or accumulated domain knowledge about the calling agent's environment.

---

## Memory Tiers

Within a session or persistent context, NPCs may maintain multiple tiers of memory. These tiers are not protocol-enforced — they are a conceptual model to help NPC providers design their memory architecture and communicate it to callers.

### Tier 1: Ephemeral (call-scoped)

Memory that exists only for the duration of a single `execute` call. Intermediate reasoning, temporary variables, in-flight state. Discarded after the response is returned.

### Tier 2: Session (multi-turn)

Memory that persists across `execute` calls within the same `session_id`. Accumulated context from the current conversation: what the user asked, what was decided, what actions were taken so far. Discarded when the session ends.

### Tier 3: Persistent (cross-session)

Memory that survives session boundaries. Project-level context, historical records, learned configuration. Only available when `session_model: persistent`. The calling agent can rely on this memory being available on future interactions.

---

## Session Lifecycle

```
[New call, no session_id]
        |
        v
  NPC creates session
  returns session_id
        |
        v
[Subsequent calls with session_id]
        |
        v
  NPC maintains context
        |
        +---> [session_id omitted or expired] ---> New session created
        |
        v
[Explicit termination]
        |
        v
  NPC discards session state
```

### Session Creation

A new session is created when `execute` is called without a `session_id`, or with an expired/unknown `session_id`. The NPC MUST return a `session_id` in the response for all session models except `ephemeral`.

### Session Expiry

NPCs MAY expire sessions after a period of inactivity. If a calling agent presents an expired `session_id`, the NPC MUST either:
- Start a new session and return a new `session_id`, OR
- Return a `failed` response with `recovery_hint` explaining that the session expired

The NPC MUST NOT silently treat an expired session as a new session without indicating this to the calling agent.

### Session Termination

A calling agent MAY request session termination by calling `execute` with `instruction: "end session"` or a similar natural language instruction. The NPC SHOULD honor this and confirm termination in the response.

---

## Caller-Injected Memory

An NPC MAY expose a `write_memory` tool to allow the calling agent to inject context into the NPC's persistent memory tier. This is useful for recording manual actions taken outside the NPC's knowledge.

```json
{
  "name": "write_memory",
  "inputSchema": {
    "type": "object",
    "required": ["note"],
    "properties": {
      "project_id": { "type": "string" },
      "note": { "type": "string", "description": "Context to store" }
    }
  }
}
```

If exposed, `write_memory` MUST be listed in the NPC Card's `mcp_tools` array. The calling agent can also inject memory via natural language: `execute(instruction="remember: we manually scaled to 3 instances yesterday")`.

---

## Multi-Project Sessions

Some NPCs manage multiple independent project contexts (e.g. a deployment NPC managing staging and production for different apps). In this case:

- The NPC SHOULD use a `project_id` parameter on `execute` to scope session state
- Each `project_id` maintains its own independent persistent memory
- The `session_id` is still used for multi-turn conversation threading within a project context

---

## Calling Agent Responsibilities

- MUST store and pass `session_id` for all calls in a conversation
- MUST NOT modify or construct `session_id` values
- MUST handle expired session responses gracefully (start fresh or inform user)
- SHOULD inform the user when starting a new session after expiry, if context was lost
- MAY use `write_memory` to keep the NPC's persistent memory accurate

---

## NPC Provider Responsibilities

- MUST return `session_id` in every response when `session_model` is `session` or `persistent`
- MUST honor `session_id` continuity — the same `session_id` MUST return the same session context
- MUST NOT change `session_id` mid-conversation for the same session
- MUST handle expired session IDs gracefully and communicate expiry clearly
- SHOULD document their session expiry policy (e.g. "sessions expire after 24 hours of inactivity")
