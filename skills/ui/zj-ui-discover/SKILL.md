---
name: zj-ui-discover
description: >-
  S2 DISCOVER：在 brief 草案上补齐缺口——输出问题清单、证据等级与 unknown 条目，
  追问预算固定为 2 次，不替用户做审美或业务判断。Use when brief 已成型但目标用户、
  状态、约束或成功标准仍有空白，需要在进入方向选择前把证据与未知显式登记。
  当前为契约骨架（1-6-1），可执行实现未落地。
argument-hint: "<UI-BRIEF.md 路径>"
metadata:
  status: contract-skeleton
  implemented_in: 1-6-2
source: zagentic
---

# zj-ui-discover

S2 · DISCOVER · `write` owner of `UI-BRIEF.md`（`unknown[]` 与证据字段）

> **状态：契约骨架（1-6-1）。** 本文件冻结 capability manifest、输入输出、禁止事项、停止条件
> 与失败 fixture id；可执行实现归 1-6-2，fixture 运行归 1-6-5。实现落地前不要把本 skill
> 当作可用能力。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-discover",
  "manifest_version": "0.1.0",
  "stage": "S2",
  "owner_scope": "write",
  "writes": ["UI-BRIEF.md"],
  "reads": [],
  "input": [
    {"name": "UI-BRIEF.md draft", "type": "revision", "required": "yes", "source": "S1"},
    {"name": "question_budget", "type": "int", "required": "yes", "source": "policy:2"}
  ],
  "output": [
    {"name": "question list", "type": "document", "artifact_kind": "non-canonical", "atomic": false},
    {"name": "evidence grade", "type": "object", "artifact_kind": "non-canonical", "atomic": false},
    {"name": "unknown[] entries", "type": "array", "artifact_kind": "UI-BRIEF.md", "atomic": true}
  ],
  "forbidden": [
    "替用户做审美或业务决定",
    "把证据不足写成已证实",
    "追问超过 2 次",
    "改写 S1 已冻结的必填字段值"
  ],
  "dependencies": ["S1 通过的 revision"],
  "required_capabilities": ["evidence-grading"],
  "stop_conditions": [
    {"condition": "证据不足", "action": "STOP", "next": "标 unknown 四元组后继续下一阶段，不填充猜测值"},
    {"condition": "追问用尽仍不足", "action": "WAIT_HUMAN", "next": "NEEDS_CONTEXT"}
  ],
  "owner": "brief/contract owner",
  "precedence": 20,
  "failure_fixtures": ["FF-DISC-01", "FF-DISC-02", "FF-DISC-03"],
  "human_gate": "conditional"
}
```

## 职责与边界

只补三类东西：**问题清单**（还缺什么）、**证据等级**（这条信息有多可信、来源是谁）、
**unknown 条目**（缺什么、为什么缺、原始说法是什么、证据从哪来）。不改 S1 已冻结的必填值。

- **不越界**：S2 不选方向、不写 token、不生成 flow。
- **追问是预算不是习惯**：预算 2 次由 policy 给出，不是 skill 自定义的数字。
- **证据分级**：`source` 必须可归因；"看起来像"不是证据等级。

## 停止条件与 Human gate

- 证据不足 → 标 `unknown` 四元组后继续；**不得**用猜测值填满。
- 追问用尽仍不足 → `NEEDS_CONTEXT` 并交人；零写入。
- `human_gate=conditional`：只在追问用尽时升级。

## 失败 fixture

- `FF-DISC-01` 正常：补齐 3 处缺口，unknown 清零，revision 只增一轮。
- `FF-DISC-02` 冲突：证据不足 → 必须标 unknown，写入值不得为猜测。
- `FF-DISC-03` 失败：追问超上限 → 停止且不写 artifact。

## 交接

- 上游：S1 的 draft revision（S2 不能改它的必填值）。
- 下游：S3 `zj-ui-direction` 只消费补齐后的 brief；S3 回退目标是 S2 revision。
- 交接失败不自动改派：`BLOCKED_HANDOFF` 交流程维护者。
