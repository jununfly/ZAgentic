---
name: zj-ui-brief
description: >-
  S1 INTAKE：把用户对话或 UI-BRIEF.md 的编辑解析成 brief 草案——目标、目标用户、任务、约束、
  成功标准与 unknown 四元组，缺口最多追问两次。Use when 用户说“做一个页面 / 审批流”，
  或直接编辑 UI-BRIEF.md 需要被校验并生成下一阶段 plan。
  实现见 zj-ui-core 的 scripts/ui_stages.py（1-6-2），失败 fixture 已落地。
argument-hint: "<对话要点，或 UI-BRIEF.md 路径>"
metadata:
  status: implemented
  implemented_in: 1-6-2
source: zagentic
---

# zj-ui-brief

S1 · INTAKE · `write` owner of `UI-BRIEF.md`

> **状态：已实现（1-6-2）。** 契约不变；确定性实现在 `skills/ui/zj-ui-core/scripts/ui_stages.py`
> 的 `run_brief`，三条 fixture 已落地并逐条通过（见 `## 实现与证据`）。链上串联归 1-6-5，
> 本 skill 仍不能单独当作端到端流程。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-brief",
  "manifest_version": "0.1.0",
  "stage": "S1",
  "owner_scope": "write",
  "writes": ["UI-BRIEF.md"],
  "reads": [],
  "input": [
    {"name": "conversation_or_brief_edit", "type": "text", "required": "yes", "source": "user"},
    {"name": "artifact_revision", "type": "revision", "required": "no", "source": "existing-artifact"}
  ],
  "output": [
    {"name": "UI-BRIEF.md draft", "type": "document", "artifact_kind": "UI-BRIEF.md", "atomic": true},
    {"name": "unknown[]", "type": "array", "artifact_kind": "UI-BRIEF.md", "atomic": false}
  ],
  "forbidden": [
    "执行 effect：代码执行、网络访问、凭据使用、远程写回",
    "替用户编造 goal_users 或 success_criteria",
    "把 unknown 压成空值或猜测值",
    "连续追问超过 2 个问题"
  ],
  "dependencies": [
    "canonical artifact schema（1-2-1，UI-BRIEF.md 字段定义）",
    "input_revision（用户对话或文档编辑）"
  ],
  "required_capabilities": ["document-parsing", "schema-validation"],
  "stop_conditions": [
    {"condition": "缺目标、目标用户或成功标准", "action": "WAIT_HUMAN", "next": "最多补 2 问，仍缺转 NEEDS_CONTEXT"},
    {"condition": "schema 校验失败（非法字段）", "action": "STOP", "next": "不提交 revision，保留 draft 供人修"}
  ],
  "owner": "brief/contract owner",
  "precedence": 10,
  "failure_fixtures": ["FF-BRIEF-01", "FF-BRIEF-02", "FF-BRIEF-03"],
  "human_gate": "conditional"
}
```

## 职责与边界

把"人说的话"变成可校验的 brief：四类必填（目标、目标用户、任务、成功标准）齐全，或对每个缺口
留下 `unknown` 四元组（`path` / `raw` / `reason` / `source`）。只写 draft，不执行任何副作用。

- **不替用户做决定**：审美、业务优先级、目标用户的取舍属于 S3 的 Human gate 或用户本人。
- **不越界写下游 artifact**：`UI-DESIGN.md` 归 S3/S4，`ui-flow/v1` 归 S5。
- **unknown 不是失败**：证据不足时标 unknown 继续，比编造一个值更符合本仓库语义。

## 停止条件与 Human gate

- 必填缺失 → 一次列出缺口并追问，**最多 2 问**；追问用尽仍缺 → `NEEDS_CONTEXT`，零写入。
- schema 校验失败 → `STOP`，不提交 revision（非法字段一律 deny-first）。
- `human_gate=conditional`：仅当"缺失必填且已追问 2 次"才升级给人，其余情况自行收敛。

## 失败 fixture

- `FF-BRIEF-01` 正常：对话含四类必填 → 产出 draft + 空 unknown，retries=0。
- `FF-BRIEF-02` 冲突：缺 `success_criteria` → `NEEDS_CONTEXT`，写入次数为 0。
- `FF-BRIEF-03` 失败：draft 含非法字段 → deny-first 拒绝，不提交 revision。

## 实现与证据

- 实现：`skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_brief`
- fixture：`tests/ui-agent-skills/fixtures/skills/FF-BRIEF-{01,02,03}/`（input/expected 分离）
- 跑批：`python skills/ui/zj-ui-core/scripts/run_fixture.py tests/ui-agent-skills/fixtures/skills --recursive`

三条 fixture 断言的是状态与副作用，不是文案：01 = `OK` + `writes=1`；02 = `NEEDS_CONTEXT` +
`writes=0` 且 unknown 四元组完整；03 = `REJECTED` 且被拒字段精确等于 `successCriteria`
（camelCase 笔误不会被静默丢弃）。

## 交接

- 上游：用户对话 / `UI-BRIEF.md` 编辑（`input_revision` 必须落进 draft 的 source）。
- 下游：S2 `zj-ui-discover` 接手补证据与 unknown；S1 撤销不是回滚点，S2 回退目标是 S1 最后 revision。
- 交接超时未确认 → `BLOCKED_HANDOFF` 升级流程维护者，**不自动改派**。
