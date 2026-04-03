# Skill File

**Version:** 0.1.0

---

## Overview

The Skill File is a versioned, structured document that an NPC publishes to guide calling agents on how to use it effectively. Where the NPC Card answers *"what can this NPC do?"*, the Skill File answers *"how do I operate it correctly?"*

The NPC Card is a machine-readable JSON identity declaration. The Skill File is a human-and-agent-readable instruction manual — written for an AI agent to load as context before interacting with the NPC. It encodes operational knowledge that cannot be expressed in a JSON schema: timing constraints, multi-step flow patterns, response extensions, things that will fail silently if done wrong, and ordered best practices.

Every non-trivial NPC SHOULD publish a Skill File. Without one, calling agents must discover operational details through trial and error.

---

## Publishing the Skill File

An NPC that provides a Skill File MUST publish it as two MCP resources:

| Resource URI | MIME type | Description |
|---|---|---|
| `npc://skill` | `text/markdown` | Full skill file content |
| `npc://skill-version` | `application/json` | Version string only, for lightweight drift checks |

```json
// npc://skill-version response
{ "version": "1.2.0" }
```

The NPC Card SHOULD declare both:
```json
{
  "skill_file_uri": "npc://skill",
  "skill_version": "1.2.0"
}
```

A calling agent SHOULD read the Skill File once per session (on first connection) and reload it whenever version drift is detected.

---

## Version Drift Detection

The NPC MUST inject a `skill_version` field into every `execute()` response:

```json
{
  "type": "completed",
  "session_id": "sess_abc",
  "result": "...",
  "skill_version": "1.2.0"
}
```

The calling agent MUST compare this value against the version it loaded at session start. If they differ, the calling agent MUST reload the Skill File from `npc://skill` before sending the next instruction. This ensures the agent is always operating with current guidance without requiring explicit polling.

---

## File Format

A Skill File is a Markdown document with a YAML frontmatter block.

### Frontmatter

```yaml
---
name: <string>                    # Required. Matches NPCCard.name
description: <string>             # Required. One-line summary for agent discovery
type: knowledge                   # Required. Always "knowledge" in v0.1
version: <semver>                 # Required. Skill file version (independent of NPC service version)
npc_protocol_version: <semver>    # Required. NPC Protocol spec version this file targets
---
```

### Mandatory Sections

The body MUST contain the following H2 sections, in this order:

1. `## Primary Interface`
2. `## Response Extensions`
3. `## Operational Notes`
4. `## Best Practices`

Additional sections are permitted after the mandatory ones.

---

## Section Specifications

### `## Primary Interface`

Documents how to use the `execute` tool. This is the most important section — it tells the calling agent:

- What kinds of instructions the NPC understands
- What parameters matter and when to use them
- What the NPC handles autonomously (so the calling agent doesn't over-specify)
- Example calls with expected response types

**Required content:**
- At least one annotated `execute()` call example
- A description of what the NPC handles autonomously vs. what requires caller input
- How to continue a multi-turn conversation (session_id threading)

**Example:**
```markdown
## Primary Interface

Use `execute` for all instructions. Send code as plain text, a unified diff, or a GitHub PR URL.

    execute(instruction="review this function: def foo(x): ...")
    execute(instruction="review PR diff:\n--- a/main.py\n+++ b/main.py\n...")

The NPC handles autonomously:
- Identifying issue severity without caller guidance
- Deciding when to trigger the large_review confirmation gate (>8 issues)
- Formatting output with severity badges

To continue a conversation (e.g. after a needs_confirmation gate):

    execute(instruction="just the blockers", session_id="sess_abc")
```

---

### `## Response Extensions`

Documents any NPC-specific response types or fields beyond the standard NPC Protocol envelope.

If the NPC uses only standard response types (`in_progress`, `needs_input`, `needs_confirmation`, `completed`, `failed`), this section MUST still be present and MUST state that explicitly:

```markdown
## Response Extensions

This NPC uses no custom response types beyond the standard NPC Protocol envelope.
```

If the NPC adds custom fields or subtypes, each MUST be documented:

```markdown
## Response Extensions

### `needs_sampling`

Emitted when the NPC needs to read local files before it can proceed.

    {
      "type": "needs_sampling",
      "session_id": "...",
      "request": {
        "files": ["/path/to/file"],
        "purpose": "detect stack"
      }
    }

Reply by passing file contents in `sampling_response`:

    execute(
      instruction="here are the files",
      session_id="...",
      sampling_response={"files": {"/path/to/file": "<content>"}}
    )
```

---

### `## Operational Notes`

Documents timing constraints, sequencing requirements, and failure modes that are not obvious from the tool schemas. This is where the NPC provider encodes hard-won operational knowledge.

**What belongs here:**
- Actions that have time windows (e.g. "poll within 30 minutes or the job times out")
- Sequencing requirements (e.g. "always call X before Y on first use")
- Silent failure modes (e.g. "if you omit session_id the gate context is lost")
- Rate limits or concurrency constraints

**Example:**
```markdown
## Operational Notes

- Sessions expire after 60 minutes of inactivity. If your session_id is rejected,
  start a new session — the NPC has no memory of the previous conversation.

- When a `needs_confirmation` gate fires for `large_review`, the pending review is
  held in session state. You must reply with the same `session_id` or the review
  is lost and the code must be re-submitted.

- The NPC does not retry LLM calls automatically. If a `failed` response is returned
  with `retryable: true`, re-submit the same instruction with the same session_id.
```

---

### `## Best Practices`

An ordered list of things the calling agent should always do. Written as imperatives. Numbered for easy reference.

**Required items (every Skill File MUST include these):**
1. Always pass `session_id` when continuing a conversation
2. Always surface `recovery_hint` to the user on a `failed` response
3. Check `skill_version` on every response and reload the Skill File if it changes

Additional items are NPC-specific.

**Example:**
```markdown
## Best Practices

1. **Always pass `session_id`** when replying to a `needs_*` response.
2. **Always surface `recovery_hint`** to the user on `failed` responses.
3. **Check `skill_version`** on every response — if it differs from the version you loaded,
   call `npc://skill` to reload before the next instruction.
4. **Don't re-submit code after a gate** — the review is already done and held in session.
   Just reply to the gate prompt with your choice.
5. **Use the `choice` parameter** when the gate offers explicit options — it signals intent
   more clearly than free-form text.
```

---

## Optional Sections

The following sections are optional but recommended where applicable:

### `## Authentication`

How to authenticate with the NPC server. Include token format, where to obtain credentials, and any per-environment differences.

### `## Tool Reference`

For NPCs that declare `capability_opacity: transparent` — documents each exposed MCP tool with parameters and return values.

### `## Flows`

State machine diagrams or step-by-step walkthroughs of common multi-step interactions. Useful for NPCs with complex prerequisite chains.

### `## Version History`

A brief changelog so calling agents can understand what changed between versions.

---

## Minimal Valid Skill File

```markdown
---
name: My NPC
description: One-line description of what this NPC does
type: knowledge
version: 1.0.0
npc_protocol_version: 0.1.0
---

## Primary Interface

Use `execute` for all instructions.

    execute(instruction="do something")

The NPC handles all domain logic autonomously.

## Response Extensions

This NPC uses no custom response types beyond the standard NPC Protocol envelope.

## Operational Notes

- Sessions expire after 24 hours of inactivity.

## Best Practices

1. Always pass `session_id` when continuing a conversation.
2. Always surface `recovery_hint` to the user on `failed` responses.
3. Check `skill_version` on every response and reload if it changes.
```

---

## Relationship to the NPC Card

| | NPC Card | Skill File |
|---|---|---|
| Format | JSON | Markdown + YAML frontmatter |
| Audience | Machines | AI agents (and humans) |
| Purpose | Identity and capability declaration | Operational instructions |
| URI | `npc://card` | `npc://skill` |
| Versioning | Via `npc_protocol_version` | Independent `version` field |
| Required | Yes | Recommended for non-trivial NPCs |
| Update signal | Static | `skill_version` injected in every response |
