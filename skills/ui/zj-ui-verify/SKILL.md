---
name: zj-ui-verify
description: >-
  S9 VERIFY：跑 DOM / ARIA、focus、contrast、reduced-motion 与网络边界硬门禁，
  产出带完整链路字段的 verification receipt 并聚合状态；receipt 缺链路、用 baseline 冒充新通过、
  把 stale 基线当当前证据，都不生成成功 receipt。Use when 视觉复审与极限测试都过了，
  需要一次可归因、可重放的自动化验证结论。
  确定性实现见 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_verify`。
argument-hint: "<preview 路径、verification matrix 与 environment fingerprint>"
metadata:
  status: implemented
source: zagentic
---

# zj-ui-verify

S9 · VERIFY · `write` owner of `verification receipt`（a11y / interaction / motion cell）

> capability manifest、输入输出、禁止事项、停止条件与失败
> fixture id 已冻结；可执行实现落在 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_verify`
> （复用 `ui_skill_core.py` 的 deny-first / unknown 四元组 / 幂等 commit 原语），由
> `tests/ui-agent-skills/fixtures/skills/FF-VER-*` 验收。

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
    {"name": "verification matrix", "type": "object", "required": "yes", "source": "contract"},
    {"name": "environment fingerprint", "type": "object", "required": "yes", "source": "contract"},
    {"name": "oracle_version", "type": "string", "required": "yes", "source": "runner"}
  ],
  "output": [
    {"name": "verification receipt", "type": "document", "artifact_kind": "verification receipt", "atomic": true},
    {"name": "aggregate status", "type": "enum", "artifact_kind": "verification receipt", "atomic": false}
  ],
  "forbidden": [
    "receipt 缺链路字段仍生成成功结论",
    "用 baseline 冒充新通过",
    "把 stale 基线当当前证据",
    "状态机可达但 UI 无入口仍判通过（G-V1）",
    "error/failed 终态渲染或汇报为 success、持久化失败静默吞掉（G-V2）",
    "非法/未定义迁移返回值被静默丢弃（G-V3）",
    "必填输入验证失败时缺失 aria-describedby 关联仍判通过（G-V4）"
  ],
  "dependencies": [
    "S7 与 S8 完成",
    "Storybook active adapter（B1；实现见 skills/ui/zj-ui-core/scripts/adapters/storybook_adapter.py，确定性引擎产出 checks 后由本 skill 聚合 receipt）",
    "verification receipt 契约"
  ],
  "required_capabilities": [
    "dom-aria-check",
    "focus-check",
    "contrast-check",
    "reduced-motion-check",
    "network-boundary-check",
    "state-transition-ui-reachability",
    "no-fake-success",
    "illegal-transition-return-checked",
    "required-input-aria-describedby"
  ],
  "stop_conditions": [
    {"condition": "visual blocker / a11y blocker / receipt 缺链路", "action": "STOP", "next": "不生成成功 receipt，下游冻结"},
    {"condition": "fingerprint 变化", "action": "STOP", "next": "stale / revalidation_required"},
    {"condition": "G-V1 状态迁移无 UI 可达入口", "action": "STOP", "next": "不生成成功 receipt，下游冻结"},
    {"condition": "G-V2 失败态被渲染/汇报为成功 或 持久化失败静默", "action": "STOP", "next": "不生成成功 receipt，下游冻结"},
    {"condition": "G-V3 非法迁移返回值未校验", "action": "STOP", "next": "不生成成功 receipt，下游冻结"},
    {"condition": "G-V4 必填输入缺失 aria-describedby 关联", "action": "STOP", "next": "不生成成功 receipt，下游冻结"}
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
- **空证据不放行**：`checked==0` 一律 `HUMAN_REVIEW_REQUIRED`，不判 PASS（框架级兜底）。

## 停止条件与 Human gate

- visual blocker / a11y blocker / receipt 缺链路 → 不生成成功 receipt，下游冻结。
- fingerprint 变化 → `STALE`，旧基线只能作 fallback。
- `human_gate=conditional`：人工未签 → `HUMAN_REVIEW_REQUIRED`。

## 失败 fixture

- `FF-VER-01` 正常：全链路 PASS。
- `FF-VER-02` 冲突：a11y blocker → 无成功 receipt，下游冻结。
- `FF-VER-03` 失败：fingerprint mismatch → `STALE`，旧基线只作 fallback。

## 强制门禁（毕业 gate 派生）

以下 4 条硬门禁在本 skill 成为强制验证项。`run_verify` 已实现门禁强制（见 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `REQUIRED_VERIFY_GATES` + `enforce_gates` 分支）：当 verification request 带 `enforce_gates=true` 且 checks 含 `gate` 标记时，缺覆盖或任一门禁非 PASS → BLOCKED、不生成成功 receipt。通用 Storybook adapter 产出五维通用 checks（不含 gate 标记），故默认不触发门禁；状态机/表单 UI 的验收须以 `enforce_gates=true` + 4 条 gate-tagged checks 叠加验收。任一门禁 fail → 不生成成功 receipt，下游冻结。

- **G-V1 state-transition UI reachability**：契约层状态机的每个合法迁移都必须有对应 UI 可达入口/控件；状态可达但 UI 无入口 = 验证失败。
- **G-V2 no-fake-success / no-silent-data-loss**：任何 `error`/`failed` 终态不得渲染或汇报为 `success`；持久化/提交失败必须显式报错，禁止静默吞掉空成功。
- **G-V3 illegal-transition return checked**：非法/未定义迁移的返回值不得被静默丢弃，必须显式校验并拒绝。
- **G-V4 required-input aria-describedby linkage**：每个必填输入在验证失败时必须通过 `aria-describedby` 关联错误提示区域；缺失关联 = 验证失败（无障碍）。

> 这些门禁的判定口径源自本仓库的 UI Agent Skills 契约（源仓库维护，不随 skill 安装）。一旦落地，direct 与 skills 两条链路的漏检都被硬拦截，质量差异在验证层被抹平。

## 交接

- 上游：S7 review record、S8 break cell、环境 fingerprint、oracle 版本。
- 下游：S10 `zj-ui-handoff` 只在 `status=PASS` 时接手；回退目标是 S6 revision。
- 无法归因 → `QUARANTINED`，交 verification owner，不自动重跑掩盖。
