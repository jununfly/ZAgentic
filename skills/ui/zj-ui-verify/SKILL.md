---
name: zj-ui-verify
description: >-
  S9 VERIFY：跑 DOM / ARIA、focus、contrast、reduced-motion 与网络边界硬门禁，
  产出带完整链路字段的 verification receipt 并聚合状态；receipt 缺链路、用 baseline 冒充新通过、
  把 stale 基线当当前证据，都不生成成功 receipt。Use when 视觉复审与极限测试都过了，
  需要一次可归因、可重放的自动化验证结论。
  当前为契约骨架（1-6-1），可执行实现未落地。
argument-hint: "<preview 路径、verification matrix 与 environment fingerprint>"
metadata:
  status: contract-skeleton
  implemented_in: 1-6-4
source: zagentic
---

# zj-ui-verify

S9 · VERIFY · `write` owner of `verification receipt`（a11y / interaction / motion cell）

> **状态：契约骨架（1-6-1）。** 本文件冻结 capability manifest、输入输出、禁止事项、停止条件
> 与失败 fixture id；可执行实现归 1-6-4，fixture 运行归 1-6-5。实现落地前不要把本 skill
> 当作可用能力。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-verify",
  "manifest_version": "0.1.0",
  "stage": "S9",
  "owner_scope": "write",
  "writes": ["verification receipt"],
  "reads": ["preview", "review record"],
  "input": [
    {"name": "preview / implementation slice", "type": "artifact", "required": "yes", "source": "S6"},
    {"name": "verification matrix", "type": "object", "required": "yes", "source": "1-5-1"},
    {"name": "environment fingerprint", "type": "object", "required": "yes", "source": "1-5-2"},
    {"name": "oracle_version", "type": "string", "required": "yes", "source": "runner"}
  ],
  "output": [
    {"name": "verification receipt", "type": "document", "artifact_kind": "verification receipt", "atomic": true},
    {"name": "aggregate status", "type": "enum", "artifact_kind": "verification receipt", "atomic": false}
  ],
  "forbidden": [
    "receipt 缺链路字段仍生成成功结论",
    "用 baseline 冒充新通过",
    "把 stale 基线当当前证据"
  ],
  "dependencies": [
    "S7 与 S8 完成",
    "Storybook active adapter（B1，1-7-3）",
    "verification receipt 契约（1-5-4）"
  ],
  "required_capabilities": [
    "dom-aria-check",
    "focus-check",
    "contrast-check",
    "reduced-motion-check",
    "network-boundary-check"
  ],
  "stop_conditions": [
    {"condition": "visual blocker / a11y blocker / receipt 缺链路", "action": "STOP", "next": "不生成成功 receipt，下游冻结"},
    {"condition": "fingerprint 变化", "action": "STOP", "next": "stale / revalidation_required"}
  ],
  "owner": "verification owner",
  "precedence": 90,
  "failure_fixtures": ["FF-VER-01", "FF-VER-02", "FF-VER-03"],
  "human_gate": "conditional"
}
```

## 职责与边界

receipt 的每一格都要能回答"谁跑的、跑的是什么、环境是哪一版"。`claim` / `threshold` /
`command` / `commit` / `fixture 与 env hash` / `artifact` / `status` 缺一个，就不是成功 receipt。

- **baseline 不等于通过**：baseline 只证明"和上次一样"，不证明"这次对了"。
- **stale 要显式**：fingerprint 变了，旧证据自动作废为 `stale / revalidation_required`。
- **空证据不放行**：`checked==0` 一律 `HUMAN_REVIEW_REQUIRED`，不判 PASS（1-5-3 的框架级兜底）。

## 停止条件与 Human gate

- visual blocker / a11y blocker / receipt 缺链路 → 不生成成功 receipt，下游冻结。
- fingerprint 变化 → `STALE`，旧基线只能作 fallback。
- `human_gate=conditional`：人工未签 → `HUMAN_REVIEW_REQUIRED`。

## 失败 fixture

- `FF-VER-01` 正常：全链路 PASS。
- `FF-VER-02` 冲突：a11y blocker → 无成功 receipt，下游冻结。
- `FF-VER-03` 失败：fingerprint mismatch → `STALE`，旧基线只作 fallback。

## 交接

- 上游：S7 review record、S8 break cell、环境 fingerprint、oracle 版本。
- 下游：S10 `zj-ui-handoff` 只在 `status=PASS` 时接手；回退目标是 S6 revision。
- 无法归因 → `QUARANTINED`，交 verification owner，不自动重跑掩盖。
