"""
Code Reviewer NPC — example NPC Protocol server

This NPC wraps a senior engineer's code review style as a sellable service.
The NPC's opinions, red lines, and taste ARE the product.

The calling agent sends a PR diff or code snippet in natural language.
The NPC reviews it, flags issues by severity, and requires confirmation
before posting a large batch of comments (so it doesn't spam small PRs).

Run:
    pip install npc-protocol openai
    export OPENAI_API_KEY=sk-...
    python main.py
"""

import json
import os

from npc import NPCCard, NPCContext, NPCServer
from npc.card import ConfirmationGateDeclaration, GateLevel, PricingHints, PricingModel
from npc.response import NPCResponse

# ---------------------------------------------------------------------------
# Reviewer persona — this is the "soul" being sold.
# Swap this out with your own opinions and this becomes a completely
# different product.
# ---------------------------------------------------------------------------

REVIEWER_PERSONA = """
You are a senior engineer with 15 years of experience doing code review.
Your style is direct and opinionated. You have strong views and you hold them.

Your red lines (always flag as BLOCKER):
- No error handling on I/O or network calls
- Secrets or credentials hardcoded in source
- SQL queries built with string concatenation (injection risk)
- Mutating function arguments without documenting it
- Any auth/authz logic that looks rolled-from-scratch

Your strong preferences (flag as MAJOR):
- Functions longer than 40 lines should be broken up
- No type hints in Python (you consider this non-negotiable post-2020)
- Global mutable state
- Catching bare `except:` or `except Exception:` and swallowing it silently
- Test files with no assertions

Your style notes (flag as MINOR):
- Variable names shorter than 3 characters (except well-known conventions: i, x, y, e)
- Magic numbers without a named constant
- TODO comments older than 30 days (if date is visible)
- Inconsistent naming conventions within the same file

For each issue found, output JSON in this format:
{
  "issues": [
    {
      "severity": "BLOCKER|MAJOR|MINOR",
      "line": "<line number or range, if identifiable>",
      "title": "<short title>",
      "explanation": "<why this matters>",
      "suggestion": "<concrete fix>"
    }
  ],
  "summary": "<1-2 sentence overall verdict>",
  "approved": true|false
}

If the code is clean, say so directly. Don't invent issues to seem thorough.
Be terse. Engineers don't want to read essays.
"""

# ---------------------------------------------------------------------------
# NPC Card — identity and capability declaration
# ---------------------------------------------------------------------------

card = NPCCard(
    name="Code Reviewer",
    version="1.0.0",
    domain="opinionated code review for Python and TypeScript",
    description=(
        "A senior engineer NPC that reviews code with strong, consistent opinions. "
        "Flags blockers, major issues, and style notes. The reviewer's taste is the product."
    ),
    confirmation_gates=[
        ConfirmationGateDeclaration(
            id="large_review",
            level=GateLevel.ADVISORY,
            description="PR has many issues — confirm before posting full comment list",
        )
    ],
    pricing_hints=PricingHints(
        model=PricingModel.CREDITS,
        unit="session",
        approximate_cost="5-15 credits",
    ),
    contact="https://github.com/macropulse/npc-protocol",
)

npc = NPCServer(card=card)


# ---------------------------------------------------------------------------
# Instruction handler — your domain logic lives here
# ---------------------------------------------------------------------------

@npc.instruction_handler
async def handle(instruction: str, session_id: str, ctx: NPCContext) -> NPCResponse:
    # Check if this is a confirmation reply to a large_review gate
    pending = ctx.get("pending_review")
    if pending and instruction.strip().lower() in ("yes", "confirm", "go ahead", "post them all"):
        await ctx.set("pending_review", None)
        return ctx.complete(
            result=_format_review(pending),
            data=pending,
        )
    if pending and instruction.strip().lower() in ("no", "cancel", "just blockers", "blockers only"):
        await ctx.set("pending_review", None)
        blockers_only = {
            **pending,
            "issues": [i for i in pending["issues"] if i["severity"] == "BLOCKER"],
        }
        return ctx.complete(
            result=_format_review(blockers_only),
            data=blockers_only,
        )

    # First turn — run the review
    return await _run_review(instruction, session_id, ctx)


async def _run_review(code: str, session_id: str, ctx: NPCContext) -> NPCResponse:
    try:
        review = await _call_llm(code)
    except Exception as e:
        return ctx.fail(
            error=f"Review failed: {e}",
            recovery_hint="Check that OPENAI_API_KEY is set and the model is accessible, then retry.",
            retryable=True,
        )

    issues = review.get("issues", [])
    blockers = [i for i in issues if i["severity"] == "BLOCKER"]
    majors = [i for i in issues if i["severity"] == "MAJOR"]
    minors = [i for i in issues if i["severity"] == "MINOR"]

    # Advisory gate: if there are many issues, ask before dumping everything
    if len(issues) > 8:
        await ctx.set("pending_review", review)
        return ctx.require_confirmation(
            gate_id="large_review",
            gate_level=GateLevel.ADVISORY,
            prompt=(
                f"Found {len(blockers)} blockers, {len(majors)} major issues, "
                f"and {len(minors)} minor notes ({len(issues)} total). "
                f"Post all of them, or just the blockers?"
            ),
            details={
                "blocker_count": len(blockers),
                "major_count": len(majors),
                "minor_count": len(minors),
                "total": len(issues),
                "approved": review.get("approved", False),
            },
        )

    return ctx.complete(
        result=_format_review(review),
        data=review,
    )


def _format_review(review: dict) -> str:
    issues = review.get("issues", [])
    if not issues:
        return f"LGTM. {review.get('summary', 'No issues found.')}"

    lines = []
    for issue in issues:
        badge = {"BLOCKER": "🚫", "MAJOR": "⚠️", "MINOR": "💬"}.get(issue["severity"], "•")
        loc = f" (line {issue['line']})" if issue.get("line") else ""
        lines.append(f"{badge} [{issue['severity']}]{loc} {issue['title']}")
        lines.append(f"   {issue['explanation']}")
        lines.append(f"   Fix: {issue['suggestion']}")
        lines.append("")

    verdict = "❌ Changes requested." if not review.get("approved") else "✅ Approved with notes."
    lines.append(f"{verdict} {review.get('summary', '')}")
    return "\n".join(lines)


async def _call_llm(code: str) -> dict:
    """
    Call an LLM to do the actual review.
    Swap this out with any model — local, API, whatever you want.
    The NPC protocol layer doesn't care what's in here.
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REVIEWER_PERSONA},
            {"role": "user", "content": f"Review this code:\n\n{code}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Code Reviewer NPC running on stdio. Connect via MCP.")
    npc.run()
