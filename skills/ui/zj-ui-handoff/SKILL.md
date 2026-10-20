---
name: zj-ui-handoff
description: >-
  S10 HANDOFF：把全部 canonical artifact revision、PASS 的 verification receipt 与 commit sha
  收成一份 handoff——变更摘要、运行命令、风险、已知限制、fallback、责任人；
  receipt 非 PASS 或任一项缺失都不产出完整 handoff。Use when 验证已 PASS，
  需要把这条 UI 链路交给下一个人、下一个 Agent 或下一次会话。
  已实现于 1-6-4（run_handoff，确定性实现见 ui_stages.py）。
argument-hint: "<artifact 目录、receipt 路径与 commit sha>"
metadata:
  status: implemented
  implemented_in: 1-6-4
source: zagentic
---

# zj-ui-handoff

S10 · HANDOFF · `write` owner of `handoff`

> **状态：已实现（1-6-4）。** capability manifest、输入输出、禁止事项、停止条件与失败
> fixture id 已冻结；可执行实现落在 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_handoff`
> （复用 `ui_skill_core.py` 的 deny-first / unknown 四元组 / 幂等 commit 原语），由
> `tests/ui-agent-skills/fixtures/skills/FF-HO-*` 验收。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-handoff",
  "manifest_version": "0.1.0",
  "stage": "S10",
  "owner_scope": "write",
  "writes": ["handoff"],
  "reads": ["UI-BRIEF.md", "UI-DESIGN.md", "ui-flow/v1", "review record", "verification receipt"],
  "input": [
    {"name": "canonical artifact revisions", "type": "revision", "required": "yes", "source": "S1-S9"},
    {"name": "verification receipt (PASS)", "type": "revision", "required": "yes", "source": "S9"},
    {"name": "commit sha", "type": "string", "required": "yes", "source": "repo"}
  ],
  "output": [
    {"name": "handoff", "type": "document", "artifact_kind": "handoff", "atomic": true}
  ],
  "forbidden": [
    "在 receipt 非 PASS 时产出完整 handoff",
    "省略 fallback 或责任人",
    "把外部项目链接写成唯一依赖"
  ],
  "dependencies": [
    "S9 status=PASS",
    "adapter manifest / receipt（只读）"
  ],
  "required_capabilities": ["change-summary-generation", "reproducible-command-registration"],
  "stop_conditions": [
    {"condition": "缺 artifact、commit、风险责任人或 fallback", "action": "WAIT_HUMAN", "next": "handoff incomplete，列出缺口"},
    {"condition": "adapter 不可用", "action": "STOP", "next": "仍必须产出 handoff，证明可脱离 adapter 维护"}
  ],
  "owner": "handoff owner",
  "precedence": 100,
  "failure_fixtures": ["FF-HO-01", "FF-HO-02", "FF-HO-03"],
  "human_gate": "conditional"
}
```

## 职责与边界

handoff 是这条链的出口，也是最容易被写成"总结"的地方。它必须含：变更摘要、可复现的运行命令、
风险、已知限制、fallback、责任人。没有 fallback 的交接不是交接，是把不确定性留给下一个人。

- **不越权**：receipt 非 PASS 就不产出完整 handoff（可以产出缺口清单）。
- **不依赖 adapter**：外部服务关掉、adapter 删掉，handoff 仍要能读懂、能重跑。
- **不写链接当依赖**：外部项目链接只是参考，不是唯一恢复路径。

## 停止条件与 Human gate

- 缺 artifact / commit / 风险责任人 / fallback → `handoff incomplete`，逐项列缺口。
- adapter 不可用 → 仍必须可产出 handoff。
- `human_gate=conditional`：缺任一项必填时停下来列缺口，不自行补齐。

## 失败 fixture

- `FF-HO-01` 正常：完整 handoff（六项齐全）。
- `FF-HO-02` 冲突：缺 fallback → incomplete，不标记完成。
- `FF-HO-03` 失败：adapter 已删除 → 仍能产出 handoff。

## 交接

- 上游：S1–S9 的 canonical revision + PASS receipt + commit sha。
- 下游：无（链路终点）；可由新的会话从 handoff 冷启动。
- 缺项不自动补：列出缺口交 handoff owner。
