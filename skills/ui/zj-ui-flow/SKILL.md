---
name: zj-ui-flow
description: >-
  S5 FLOW：维护 ui-flow/v1 的六义（screen、component、state、action、intent、acceptance），
  semantic round-trip 必须通过，unknown 四元组必须保留；丢义、双写 owner、unknown 未保留都是
  hard fail。Use when 设计系统已定，需要把界面结构、状态迁移、动作与意图写成可重放的 flow。
  确定性实现见 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_flow`。
argument-hint: "<UI-DESIGN.md 路径与目标 ui-flow/v1 输出路径>"
metadata:
  status: implemented
source: zagentic
---

# zj-ui-flow

S5 · FLOW · `write` owner of `ui-flow/v1`

> capability manifest、输入输出、禁止事项、停止条件与失败 fixture id
> 已冻结；可执行实现落在 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_flow`（复用
> `ui_skill_core.py` 的 deny-first / unknown 四元组 / 幂等 commit 原语），由
> `tests/ui-agent-skills/fixtures/skills/FF-FLOW-*` 验收。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-flow",
  "manifest_version": "0.1.0",
  "stage": "S5",
  "owner_scope": "write",
  "writes": ["ui-flow/v1"],
  "reads": ["UI-DESIGN.md", "UI-BRIEF.md"],
  "input": [
    {"name": "UI-DESIGN.md", "type": "revision", "required": "yes", "source": "S4"},
    {"name": "UI-BRIEF.md", "type": "revision", "required": "yes", "source": "S2"}
  ],
  "output": [
    {"name": "ui-flow/v1 six distinct meanings", "type": "document", "artifact_kind": "ui-flow/v1", "atomic": true},
    {"name": "migration output", "type": "document", "artifact_kind": "ui-flow/v1", "atomic": false}
  ],
  "forbidden": [
    "合并六义中的任意两义",
    "让协议或外部 schema 拥有 ui-flow/v1",
    "丢弃 unknown 四元组",
    "接受第二个写 owner"
  ],
  "dependencies": [
    "S4 revision",
    "ui-flow/v1 schema lock",
    "A2UI / M3E 仅作为 B1 adapter 输入"
  ],
  "required_capabilities": ["semantic-round-trip", "offline-replay", "migration-map"],
  "stop_conditions": [
    {"condition": "状态、动作或意图丢失，双写 owner，unknown 未保留", "action": "STOP", "next": "hard fail，下游不得继续"},
    {"condition": "major version mismatch", "action": "STOP", "next": "BLOCKED_CONTRACT_MISMATCH，不寻找相似替代"}
  ],
  "owner": "flow/schema owner",
  "precedence": 50,
  "failure_fixtures": ["FF-FLOW-01", "FF-FLOW-02", "FF-FLOW-03"],
  "human_gate": "none"
}
```

## 职责与边界

`ui-flow/v1` 是语义层，不是渲染描述。六义必须**分义**存续：`screen`、`component`、`state`、
`action`、`intent`、`acceptance` 各占各的位置，合并任意两义都会让下游无法归因。
本 skill 是它唯一的写 owner，语义 round-trip 与迁移器优先于便利性。

- **不借协议**：A2UI / M3E 只能作为 adapter 输入，协议不拥有 schema。
- **不丢 unknown**：`path` / `raw` / `reason` / `source` 四元组必须原样过一遍 round-trip。
- **不接受第二 owner**：并发写同一 artifact → 冻结并 `BLOCKED_OWNER_CONFLICT`。

## 停止条件与 Human gate

- 丢义 / 双 owner / unknown 未保留 → **hard fail**，且下游（S6 起）不得继续。
- major version mismatch → `BLOCKED_CONTRACT_MISMATCH`，不找"看起来相似"的替代。
- `human_gate=none`：本阶段是语义机械检查，不设人工 gate。

## 失败 fixture

- `FF-FLOW-01` 正常：六义齐全 + round-trip 通过。
- `FF-FLOW-02` 冲突：双 owner 并发写 → 冻结 + `BLOCKED_OWNER_CONFLICT`。
- `FF-FLOW-03` 失败：intent 丢失 → hard fail，禁止下游继续。

## 交接

- 上游：S4 的 `UI-DESIGN.md`、S2 的 `UI-BRIEF.md`。
- 下游：S6 `zj-ui-prototype` 消费 flow 生成 preview；回退目标是 S4 revision。
- 交接失败 → `BLOCKED_HANDOFF`；未确认前不释放写锁。
