---
name: zj-ui-visual-review
description: >-
  S7 REVIEW：用浏览器检查 preview 并产出 review record——问题、决策、理由、期限、审阅者，
  截图必须绑定用户任务与风险等级，环境 fingerprint 必须齐全。截图单独通过不得宣称设计完成，
  无法归因的差异一律 quarantine。Use when preview 已可交互，需要人机共签一次视觉与信息层级复审。
  已实现于 1-6-3（run_visual_review，确定性实现见 ui_stages.py）。
argument-hint: "<preview 路径与环境 fingerprint>"
metadata:
  status: implemented
  implemented_in: 1-6-3
source: zagentic
---

# zj-ui-visual-review

S7 · REVIEW · `write` owner of `review record`

> **状态：已实现（1-6-3）。** capability manifest、输入输出、禁止事项、停止条件与失败 fixture id
> 已冻结；可执行实现落在 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_visual_review`
> （复用 `ui_skill_core.py` 的 deny-first / unknown 四元组 / 幂等 commit 原语），由
> `tests/ui-agent-skills/fixtures/skills/FF-VR-*` 验收。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-visual-review",
  "manifest_version": "0.1.0",
  "stage": "S7",
  "owner_scope": "write",
  "writes": ["review record"],
  "reads": ["preview"],
  "input": [
    {"name": "preview / implementation slice", "type": "artifact", "required": "yes", "source": "S6"},
    {"name": "user task and risk class", "type": "object", "required": "yes", "source": "brief"},
    {"name": "environment fingerprint", "type": "object", "required": "yes", "source": "1-5-2"}
  ],
  "output": [
    {"name": "review record", "type": "document", "artifact_kind": "review record", "atomic": true},
    {"name": "issues + decisions + reasons", "type": "array", "artifact_kind": "review record", "atomic": false}
  ],
  "forbidden": [
    "用截图通过单独宣称设计完成",
    "把无法归因的 diff 判为 PASS",
    "把 Human 未签写成已签"
  ],
  "dependencies": [
    "S6 产物",
    "自有浏览器 runner",
    "environment fingerprint（1-5-1 / 1-5-2）"
  ],
  "required_capabilities": ["browser-inspect", "screenshot", "environment-fingerprint"],
  "stop_conditions": [
    {"condition": "fingerprint 缺失或 diff 无法归因", "action": "STOP", "next": "QUARANTINED，不产出成功结论"},
    {"condition": "Human 未签", "action": "WAIT_HUMAN", "next": "HUMAN_REVIEW_REQUIRED，下游不得继续"}
  ],
  "owner": "review owner",
  "precedence": 70,
  "failure_fixtures": ["FF-VR-01", "FF-VR-02", "FF-VR-03"],
  "human_gate": "required"
}
```

## 职责与边界

review record 的价值在**可归因**：每条问题带决策、理由、期限、审阅者；每张截图带它对应的用户
任务与风险等级。视觉层级、信息可理解性、生成式审美是 Human gate，skill 只负责把证据摆好。

- **截图不是证据链**：单张截图通过不能推出"设计完成"，它只是 review 的输入之一。
- **无法归因就隔离**：diff 说不清来源 → `QUARANTINED`，不判 PASS。
- **不代签**：Human 未签即 `HUMAN_REVIEW_REQUIRED`，不把"没反对"当同意。

## 停止条件与 Human gate

- fingerprint 缺失 / diff 无法归因 → `QUARANTINED`。
- Human 未签 → `HUMAN_REVIEW_REQUIRED`，S8 / S9 不得开工。
- `human_gate=required`。

## 失败 fixture

- `FF-VR-01` 正常：Human 签署，review record 字段齐全。
- `FF-VR-02` 冲突：fingerprint 缺失 → quarantine，不产出成功结论。
- `FF-VR-03` 失败：Human 未签 → `HUMAN_REVIEW_REQUIRED`，下游冻结。

## 交接

- 上游：S6 的 preview + 环境 fingerprint。
- 下游：S8 `zj-ui-break` 与 S9 `zj-ui-verify` 共用这份 review record；回退目标是 S6 revision。
- 远程评论（provider）消失不影响审计：本地 record 才是事实源。
