# NPC 協議

[English](./README.md)

---

**別再賣 API 了。把自己包成一個 NPC，讓它替你賺錢，你去睡覺。**

不要賣工具的使用權。賣你的靈魂——你的領域知識、你的工作流程、你用血汗換來的專業——把它打包成一個自主 Agent，讓其他 AI Agent 可以雇用你、委託你、付錢給你。知識是你建立的，現在讓它去上夜班。

---

> *同事變成了 skill，前任也變成了 skill，現在到你自己了。*

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

## 快速開始（Python SDK）

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
        return ctx.require_confirmation(
            gate_id="delete_zone",
            gate_level=GateLevel.DESTRUCTIVE,
            prompt="This will permanently delete the zone and all its records.",
            protected_resources=[
                {"type": "dns_zone", "name": "example.com", "risk": "All DNS records deleted"}
            ],
        )

    return ctx.complete(result="DNS record updated")

npc.run()
```

呼叫 Agent 透過 MCP 與其互動：

```python
# 呼叫 Agent 先讀取 NPC Card
card = mcp.call("resources/read", {"uri": "npc://card"})

# 發送自然語言指令
result = mcp.call("execute", {"instruction": "delete the example.com zone"})
# --> needs_confirmation (gate_level: destructive)

# 轉達給用戶，獲得確認後回傳
result = mcp.call("execute", {"instruction": "yes", "session_id": result["session_id"], "confirm": True})
# --> completed
```

---

## 架構

```
客戶端
  [ 用戶 ]
     | 自然語言
     v
  [ 呼叫 Agent ]   <-- 客戶自行建構，愛怎麼做就怎麼做
     |
     | MCP 呼叫
     v
NPC 協議層  <-- 這份規格
  [ NPC Card ]  [ execute 工具 ]  [ 確認閘門 ]  [ 會話模型 ]
     |
     | SDK 實現協議介面
     v
NPC 提供者端
  [ NPC SDK ]
     |
     v
  [ 你的指令處理器 ]   <-- 你來寫這個
     |                 |
     v                 v
[ 你的 AI /       [ 你的後端 ]
  編排邏輯 ]       （API、資料庫、服務）
```

協議邊界只有中間那層。上下的一切都是實作者的責任。

---

## 定位

| 協議 | 處理的內容 |
|---|---|
| MCP | 主機與伺服器之間的型別工具呼叫、資源、提示 |
| A2A | Agent 之間的跨組織任務路由 |
| **NPC 協議** | **領域專家 Agent 打包：NL 介面、身份、安全閘門、會話語義** |

NPC 協議架設在 MCP 之上（不是替代品），並與 A2A 互補。

---

## 生產環境參考：SwiftDeploy

[SwiftDeploy](https://swiftdeploy.ai) 在這份規格寫出來之前，就已獨立收斂到這個模式。完整案例研究：[`sdk/python/examples/swiftdeploy_case_study.md`](sdk/python/examples/swiftdeploy_case_study.md)。

---

## 規格文件

- [`spec/README.md`](spec/README.md) — 概覽與動機
- [`spec/npc-card.md`](spec/npc-card.md) — NPC Card 規格
- [`spec/instruction-interface.md`](spec/instruction-interface.md) — 指令介面
- [`spec/confirmation-gate.md`](spec/confirmation-gate.md) — 確認閘門原語
- [`spec/session-model.md`](spec/session-model.md) — 會話與記憶語義

---

## 狀態

**v0.1.0 — 草稿。** 規格與 SDK 正在積極開發中。v1.0 之前可能有破壞性變更。

歡迎反饋與貢獻。開一個 Issue 或 Pull Request。

---

## 授權

Apache 2.0
