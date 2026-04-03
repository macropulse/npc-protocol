# NPC Protocol

**Stop selling APIs. Wrap yourself into an NPC and let it earn for you while you sleep.**

Don't sell access to your tools. Sell your soul — your domain knowledge, your workflows, your hard-earned expertise — packaged as an autonomous agent that other AI agents can hire, delegate to, and pay. You built the knowledge. Now make it work the night shift.

---

> *"同事.skill, 前任.skill, now: you.skill"*

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

---

---

# NPC 協議

**別再賣 API 了。把自己包成一個 NPC，讓它替你賺錢，你去睡覺。**

不要賣工具的使用權。賣你的靈魂——你的領域知識、你的工作流程、你用血汗換來的專業——把它打包成一個自主 Agent，讓其他 AI Agent 可以雇用你、委託你、付錢給你。知識是你建立的，現在讓它去上夜班。

---

> *「同事.skill，前任.skill，下一個：你.skill」*

---

NPC 協議是一個開放標準，用於將領域知識打包成「黑盒子」Agent 服務，讓 AI Agent 可以用自然語言委託給它——附帶持久記憶與明確的安全確認合約。基於 MCP 之上建構。

---

## 問題所在

MCP 給 AI Agent 工具可以呼叫。A2A 讓 Agent 跨組織路由任務。但兩者都沒有回答：**領域專家要怎麼把自己的知識打包成 Agent 服務，賣給其他 AI Agent？**

如果你建立過這樣的東西：
- 用自然語言驅動的雲端部署服務
- 熟悉你公司策略的法律研究 Agent
- 包裝你專有模型的財務分析 NPC
- 任何「AI 驅動服務」，需要讓另一個 Agent 把複雜工作委託給它

...你可能已經自己發明了一套臨時的慣例：呼叫 Agent 怎麼發現你能做什麼、怎麼傳達進度、在不可逆操作前怎麼暫停並要求確認、怎麼跨對話保持上下文。

NPC 協議為這些慣例命名，並將其標準化。

---

## NPC 的比喻

在遊戲中，NPC（非玩家角色）是你用自然語言互動的領域專家。他們有自己的知識、記憶與規則。某些操作需要確認。他們的內部邏輯是不透明的——你看不到他們的程式碼，你只是跟他們說話。

這就是領域專家 Agent 服務的正確心智模型。你就是那個 NPC。你的知識就是任務獎勵。

---

## 它定義了什麼

四件事，基於 MCP 作為傳輸層建構：

**1. NPC Card（NPC 名片）** — 發佈在 `npc://card` 的 JSON 身份文件。聲明領域、指令介面、會話模型、確認閘門類型與定價提示。呼叫 Agent 藉此發現 NPC 的能力。

**2. 指令介面** — 接受自由格式自然語言的標準 `execute` 工具。標準回應封包：`in_progress`、`needs_input`、`needs_confirmation`、`completed`、`failed`。透過 `session_id` 進行多輪對話。

**3. 確認閘門** — Agent 對 Agent 授權的第一類協議原語。三個等級：`advisory`（呼叫方可自動批准）、`required`（必須詢問用戶）、`destructive`（必須向用戶展示完整資源清單）。這是 MCP 和 A2A 都不存在的缺口。

**4. 會話模型** — 會話所有權語義、三個記憶層級（短暫 / 會話 / 持久）與生命週期規則。會話由 NPC 擁有；呼叫 Agent 持有不透明的 `session_id` 令牌。

---

## 它不定義什麼

- 你的 NPC 如何實現其邏輯（LLM、規則、硬編碼——你的選擇）
- 你的 NPC 內部是否使用 AI
- 支付處理（僅限定價提示）
- NPC 發現 / 註冊表
- 呼叫 Agent 的內部邏輯

---

## 定位

| 協議 | 處理的內容 |
|---|---|
| MCP | 主機與伺服器之間的型別工具呼叫、資源、提示 |
| A2A | Agent 之間的跨組織任務路由 |
| **NPC 協議** | **領域專家 Agent 打包：NL 介面、身份、安全閘門、會話語義** |

NPC 協議架設在 MCP 之上（不是替代品），並與 A2A 互補。

---

## 狀態

**v0.1.0 — 草稿。** 規格與 SDK 正在積極開發中。v1.0 之前可能有破壞性變更。

歡迎反饋與貢獻。開一個 Issue 或 Pull Request。

---

## 授權

Apache 2.0
