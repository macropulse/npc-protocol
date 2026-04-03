---
name: code-reviewer
description: Opinionated code review for Python and TypeScript — a senior engineer's taste as a service
type: knowledge
version: 1.0.0
npc_protocol_version: 0.1.0
---

# Code Reviewer NPC — Skill File

This file teaches you how to operate the Code Reviewer NPC correctly.
Load it once at session start. Reload it whenever `skill_version` in a response
differs from `1.0.0`.

---

## Primary Interface

Use `execute` for all instructions. Send code as plain text, a unified diff, or a
paste of a file. The NPC figures out the rest.

```python
# Review a snippet
execute(instruction="review this:\n\ndef get_user(id):\n    return db.query('SELECT * FROM users WHERE id=' + id)")

# Review a diff
execute(instruction="review this diff:\n--- a/auth.py\n+++ b/auth.py\n@@ -10,6 +10,8 @@\n...")

# Ask follow-up questions in the same session
execute(instruction="why is the SQL injection a blocker and not a major?", session_id="sess_abc")
```

**What the NPC handles autonomously:**
- Classifying issues into BLOCKER / MAJOR / MINOR without caller guidance
- Deciding when to trigger the `large_review` confirmation gate (>8 total issues)
- Formatting output with severity badges and fix suggestions
- Holding the pending review in session state across a confirmation gate turn

**What requires your input:**
- Responding to the `large_review` gate when it fires (see Response Extensions)
- Providing the code — the NPC does not read files from disk

---

## Response Extensions

This NPC uses no custom response types beyond the standard NPC Protocol envelope.

All responses follow the standard types: `in_progress`, `needs_input`,
`needs_confirmation`, `completed`, `failed`.

### `skill_version` field

Every response includes a `skill_version` field:

```json
{
  "type": "completed",
  "session_id": "sess_abc",
  "result": "🚫 [BLOCKER] SQL injection...",
  "skill_version": "1.0.0"
}
```

Compare this against the version you loaded at session start. If it differs,
reload this file from `npc://skill` before the next instruction.

### The `large_review` gate

When a review produces more than 8 issues, the NPC pauses before returning results
and emits a `needs_confirmation` gate:

```json
{
  "type": "needs_confirmation",
  "session_id": "sess_abc",
  "gate_id": "large_review",
  "gate_level": "advisory",
  "prompt": "Found 3 blockers, 6 major issues, and 5 minor notes (14 total). Post all of them, or just the blockers?",
  "details": {
    "blocker_count": 3,
    "major_count": 6,
    "minor_count": 5,
    "total": 14,
    "approved": false
  }
}
```

Reply with one of:
- `"yes"` / `"all"` / `"post them all"` — returns the full review
- `"no"` / `"blockers only"` / `"just blockers"` — returns only BLOCKER-level issues

```python
# Reply to the gate
execute(instruction="just blockers", session_id="sess_abc")
```

This gate is `advisory` — you may auto-approve if your policy allows it, but
you should still relay the issue count summary to the user before doing so.

---

## Operational Notes

- **Sessions expire after 60 minutes of inactivity.** If your `session_id` is
  rejected, start a new session and re-submit the code.

- **Do not re-submit code after a `large_review` gate fires.** The review is
  already complete and held in session state. Just reply to the gate prompt.
  Re-submitting will trigger a new LLM call and a new review from scratch.

- **LLM failures are retryable.** If you receive `type: failed` with
  `retryable: true`, re-submit the same instruction with the same `session_id`.
  The session context is preserved.

- **The NPC requires `OPENAI_API_KEY` to be set** in the server environment.
  If the key is missing or invalid, every `execute` call returns `type: failed`
  with a `recovery_hint` explaining the fix. The NPC does not expose the key
  or any internal error details to the calling agent.

- **Issue severity is opinionated and fixed.** The reviewer's red lines, major
  flags, and style notes are baked into the server persona. The calling agent
  cannot override severity thresholds at runtime — this is intentional. The
  reviewer's taste is the product.

---

## Best Practices

1. **Always pass `session_id`** when replying to a `needs_confirmation` gate.
   Omitting it loses the pending review and forces a re-submission.

2. **Always surface `recovery_hint`** to the user on `failed` responses.
   It contains the exact fix required (e.g. "set OPENAI_API_KEY").

3. **Check `skill_version`** on every response. If it differs from `1.0.0`,
   reload this file from `npc://skill` before the next instruction.

4. **Use the `choice` parameter for gate replies** when possible — it signals
   intent more clearly than free-form text:
   ```python
   execute(instruction="blockers only", session_id="...", choice="blockers only")
   ```

5. **Show gate details to the user before auto-approving.** Even though
   `large_review` is `advisory`, the `details.total` count is meaningful context
   for the user to decide whether they want everything or just blockers.

6. **Don't send entire repositories.** The NPC is optimised for single files,
   functions, or PR diffs. Very large inputs may exceed LLM context limits and
   return a `failed` response with `retryable: false`.
