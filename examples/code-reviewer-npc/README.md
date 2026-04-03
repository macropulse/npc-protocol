# Code Reviewer NPC

An opinionated code reviewer wrapped as an NPC Protocol server.

This example demonstrates the core idea of NPC Protocol: **the reviewer's opinions are the product**. The persona defined in `main.py` — the red lines, the strong preferences, the style notes — is the domain knowledge being sold. Two engineers wrapping themselves as NPCs would produce completely different reviewers.

---

## What it shows

- **Knowledge packaging** — a senior engineer's taste baked into a `REVIEWER_PERSONA` prompt
- **Confirmation gate** — when a PR has more than 8 issues, the NPC pauses and asks: post all of them, or just the blockers?
- **Session memory** — the NPC holds the pending review in session state across the confirmation turn
- **`recovery_hint`** — if the LLM call fails, the caller gets an actionable message

---

## Setup

```bash
pip install npc-protocol openai
export OPENAI_API_KEY=sk-...
python main.py
```

The server runs on stdio (standard MCP transport). Connect to it from any MCP-compatible host (Claude Desktop, OpenCode, a custom agent, etc.).

---

## Interaction trace

```
# Turn 1 — send some code to review
execute("review this:\n\ndef get_user(id):\n    return db.query('SELECT * FROM users WHERE id=' + id)")

--> {
      "type": "completed",
      "result": "🚫 [BLOCKER] SQL injection via string concatenation\n   ..."
    }

# Turn 2 — send a large PR diff
execute("review this diff: ...")

--> {
      "type": "needs_confirmation",
      "gate_id": "large_review",
      "gate_level": "advisory",
      "prompt": "Found 3 blockers, 6 major issues, and 5 minor notes (14 total). Post all of them, or just the blockers?"
    }

# Turn 3 — reply
execute("just blockers", session_id="sess_abc")

--> {
      "type": "completed",
      "result": "🚫 [BLOCKER] ..."  # only blockers returned
    }
```

---

## Customise it

The entire reviewer persona lives in `REVIEWER_PERSONA` at the top of `main.py`. Change it to match your own opinions:

- Different red lines (e.g. "no raw React state for server data — use React Query")
- Different tech stack (Rust, Go, Java)
- Different tone (gentler, more mentoring-focused)
- Org-specific rules (internal naming conventions, banned libraries)

That's the point. **Your taste is the product.** Wrap it, serve it, charge for it.

---

## Swap out the LLM

The `_call_llm` function at the bottom of `main.py` uses OpenAI. Replace it with anything:

```python
# Use a local model via Ollama
async def _call_llm(code: str) -> dict:
    import ollama
    response = ollama.chat(model="llama3", messages=[...])
    return json.loads(response["message"]["content"])
```

The NPC Protocol layer doesn't care what's inside.
