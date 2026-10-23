---
name: zj-ui-design-system
description: >-
  S4 DESIGN_SYSTEM：把已选方向固化成 tokens 与 component catalog（含状态、禁用组合），
  contrast 必须达标，组件必须有来源与注册记录；未注册组件、token 冲突、contrast 不达标一律阻断。
  Use when 方向已由 Human 选定，需要产出可被 flow / prototype 直接引用的设计系统。
  实现见 `skills/ui/zj-ui-core/scripts/ui_stages.py`，失败 fixture 已落地。
argument-hint: "<UI-DESIGN.md 路径>"
metadata:
  status: implemented
source: zagentic
---

# zj-ui-design-system

S4 · DESIGN_SYSTEM · `write` owner of `UI-DESIGN.md`（tokens 与 catalog）

> 契约不变；确定性实现在 `skills/ui/zj-ui-core/scripts/ui_stages.py`
> 的 `run_design_system`，三条 fixture 已落地并逐条通过（见 `## 实现与证据`）。链上串联由 resolver 完成，
> 本 skill 仍不能单独当作端到端流程。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-design-system",
  "manifest_version": "0.1.0",
  "stage": "S4",
  "owner_scope": "write",
  "writes": ["UI-DESIGN.md"],
  "reads": [],
  "input": [
    {"name": "UI-DESIGN.md direction_choice", "type": "revision", "required": "yes", "source": "S3"},
    {"name": "token_catalog_draft", "type": "object", "required": "no", "source": "user-or-method"}
  ],
  "output": [
    {"name": "tokens", "type": "object", "artifact_kind": "UI-DESIGN.md", "atomic": true},
    {"name": "component catalog", "type": "object", "artifact_kind": "UI-DESIGN.md", "atomic": false},
    {"name": "forbidden combinations", "type": "array", "artifact_kind": "non-canonical", "atomic": false}
  ],
  "forbidden": [
    "注册未声明来源的组件",
    "输出 contrast 不达标的配色",
    "合并外部 runtime",
    "让 adapter 拥有 catalog 字段值"
  ],
  "dependencies": [
    "S3 Human 选择",
    "canonical design schema",
    "字体与图标 license 台账"
  ],
  "required_capabilities": ["contrast-computation", "component-registry"],
  "stop_conditions": [
    {"condition": "未注册组件", "action": "STOP", "next": "阻断，零写入"},
    {"condition": "token 冲突或 contrast 不达标", "action": "STOP", "next": "阻断，不得静默替换为相近色"},
    {"condition": "font license unknown", "action": "STOP", "next": "quarantine"}
  ],
  "owner": "direction/design owner",
  "precedence": 40,
  "failure_fixtures": ["FF-DS-01", "FF-DS-02", "FF-DS-03"],
  "human_gate": "none"
}
```

## 职责与边界

把"选定的方向"变成"可引用的系统"：tokens（色阶、字号、间距、圆角、动效时长）与 component
catalog（组件名、来源、状态、禁止组合）。catalog 的字段值由本仓库拥有，adapter 只能提交投影。

- **阻断优先**：未注册组件、token 冲突、contrast 不达标都是 `STOP`，不降级通过。
- **不静默修**：contrast 不达标时不得"换成相近色再算达标"——那是把验收改成自证。
- **不接管 runtime**：合并外部 runtime 会让 catalog 的事实源漂走，禁止。

## 停止条件与 Human gate

- 未注册组件 / token 冲突 / contrast 不达标 → `STOP`，零写入。
- font license unknown → `quarantine`，不进默认产物。
- `human_gate=none`：审美判断已在 S3 签过，本阶段无第二次 gate。

## 失败 fixture

- `FF-DS-01` 正常：tokens + catalog 落盘，contrast 全达标。
- `FF-DS-02` 冲突：未注册组件 → 阻断、零写入。
- `FF-DS-03` 失败：contrast 不达标 → 阻断，且不得静默替换。

## 实现与证据

- 实现：`skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_design_system`
- fixture：`tests/ui-agent-skills/fixtures/skills/FF-DS-{01,02,03}/`
- 跑批：`python skills/ui/zj-ui-core/scripts/run_fixture.py tests/ui-agent-skills/fixtures/skills --recursive`

01 = tokens + 三个已注册组件落盘、两对 contrast 全达标；02 = `DateRangePicker` 未注册 →
`BLOCKED` + `writes=0`（adapter 不得扩表）；03 = `#777777 on #FFFFFF = 4.478 < 4.5` →
`BLOCKED`，且产物为空 —— 证明没有"换成相近色再算达标"。

## 交接

- 上游：S3 的 `direction_choice`（Human 已签）。
- 下游：S5 `zj-ui-flow` 只允许引用 catalog 内的组件；回退目标是 S3 revision。
- 交接失败 → `BLOCKED_HANDOFF`，不自动改派。
