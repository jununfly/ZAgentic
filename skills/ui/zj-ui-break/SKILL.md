---
name: zj-ui-break
description: >-
  S8 BREAK：用版本化 fixture matrix 打断界面——长文本、空值、错误、极值、多语言，
  加 390 / 768 / 1440 三档视口，overflow、focus、恢复失败一律 FAIL 而非 warning。
  Use when preview 已过视觉复审，需要证明它在极端数据与窄屏下仍然可用。
  当前为契约骨架（1-6-1），可执行实现未落地。
argument-hint: "<preview 路径与 fixture matrix 版本>"
metadata:
  status: contract-skeleton
  implemented_in: 1-6-3
source: zagentic
---

# zj-ui-break

S8 · BREAK · `write` owner of `verification receipt`（break cell）

> **状态：契约骨架（1-6-1）。** 本文件冻结 capability manifest、输入输出、禁止事项、停止条件
> 与失败 fixture id；可执行实现归 1-6-3，fixture 运行归 1-6-5。实现落地前不要把本 skill
> 当作可用能力。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-break",
  "manifest_version": "0.1.0",
  "stage": "S8",
  "owner_scope": "write",
  "writes": ["verification receipt"],
  "reads": ["preview", "review record"],
  "input": [
    {"name": "preview / implementation slice", "type": "artifact", "required": "yes", "source": "S6"},
    {"name": "fixture matrix", "type": "object", "required": "yes", "source": "fixture-manifest"},
    {"name": "viewport set", "type": "array", "required": "yes", "source": "policy:390/768/1440"}
  ],
  "output": [
    {"name": "verification receipt (break cell)", "type": "document", "artifact_kind": "verification receipt", "atomic": true}
  ],
  "forbidden": [
    "降低 viewport 或 locale 覆盖率以通过",
    "把 overflow / focus / 恢复失败记为 warning 而非 fail"
  ],
  "dependencies": [
    "S7 通过的 review record",
    "fixture-manifest（1-5-1）"
  ],
  "required_capabilities": ["versioned-fixture-matrix", "responsive-runner"],
  "stop_conditions": [
    {"condition": "关键状态未覆盖，或 overflow / focus / 恢复失败", "action": "STOP", "next": "FAIL，receipt 记录实测值"},
    {"condition": "环境无法验证", "action": "STOP", "next": "BLOCKED，不得用部分通过冒充 PASS"}
  ],
  "owner": "verification owner",
  "precedence": 80,
  "failure_fixtures": ["FF-BRK-01", "FF-BRK-02", "FF-BRK-03"],
  "human_gate": "none"
}
```

## 职责与边界

把界面往坏里用：超长文案、空集合、错误态、极值数字、多语言展开、三档视口。break cell 只写
实测值，不写"看起来没问题"。与 S9 的分工：S8 管**数据与视口的极端**，S9 管 a11y、interaction
与 motion；两者写同一个 receipt 的不同 cell。

- **不缩范围**：减少 viewport 或 locale 通过率不是"通过"，是把验收标准改小。
- **不降级失败**：overflow / focus / 恢复失败是 FAIL，不是 warning。
- **fixture 缺失即 BLOCKED**：没有矩阵就没有断言，不能拿"部分跑过"当 PASS。

## 停止条件与 Human gate

- 关键状态未覆盖 / overflow / focus / 恢复失败 → `FAIL`。
- 环境无法验证 → `BLOCKED`。
- `human_gate=none`：自动硬门禁，人只在 FAIL 后处置。

## 失败 fixture

- `FF-BRK-01` 正常：全矩阵 + 三档视口跑完，receipt 有实测值。
- `FF-BRK-02` 冲突：1440 下 overflow → FAIL，且 receipt 记录实测值（不是结论句）。
- `FF-BRK-03` 失败：fixture 缺失 → `BLOCKED`，不得以"部分通过"冒充 PASS。

## 交接

- 上游：S7 通过的 review record、fixture-manifest。
- 下游：S9 `zj-ui-verify` 与 S8 汇合到同一 receipt；回退目标是 S6 revision。
- 环境不可验证 → `BLOCKED` 升级 verification owner，不自动降级。
