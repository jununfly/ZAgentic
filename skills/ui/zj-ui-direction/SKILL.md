---
name: zj-ui-direction
description: >-
  S3 DIRECTION：基于 brief 生成 2–3 张可比较的方向卡（色彩、字体、密度、动效、适用场景、
  取舍与参考来源），由 Human 选定一个方向后才写入 UI-DESIGN.md。方向选择是不可形式化的
  审美判断，本 skill 不替人选。Use when brief 已齐、需要给出视觉方向候选并让人拍板。
  实现见 zj-ui-core 的 scripts/ui_stages.py（1-6-2），失败 fixture 已落地。
argument-hint: "<UI-BRIEF.md 路径>"
metadata:
  status: implemented
  implemented_in: 1-6-2
source: zagentic
---

# zj-ui-direction

S3 · DIRECTION · `write` owner of `UI-DESIGN.md`（方向候选段落）

> **状态：已实现（1-6-2）。** 契约不变；确定性实现在 `skills/ui/zj-ui-core/scripts/ui_stages.py`
> 的 `run_direction`，三条 fixture 已落地并逐条通过（见 `## 实现与证据`）。链上串联归 1-6-5，
> 本 skill 仍不能单独当作端到端流程。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-direction",
  "manifest_version": "0.1.0",
  "stage": "S3",
  "owner_scope": "write",
  "writes": ["UI-DESIGN.md"],
  "reads": ["UI-BRIEF.md"],
  "input": [
    {"name": "UI-BRIEF.md", "type": "revision", "required": "yes", "source": "S2"}
  ],
  "output": [
    {"name": "direction cards x2-3", "type": "array", "artifact_kind": "non-canonical", "atomic": false},
    {"name": "direction_choice candidate", "type": "object", "artifact_kind": "UI-DESIGN.md", "atomic": true}
  ],
  "forbidden": [
    "自动替用户选定方向",
    "套用未注明来源的模板",
    "方向不唯一时默认取第一个",
    "把外部方法主体并入本 skill"
  ],
  "dependencies": [
    "S2 revision",
    "外部参考 provenance（license / source 必填）"
  ],
  "required_capabilities": ["comparable-direction-card-generation", "provenance-registration"],
  "stop_conditions": [
    {"condition": "方向不唯一或参考缺来源", "action": "WAIT_HUMAN", "next": "展示候选，不自动套模板"},
    {"condition": "参考来源 license unknown", "action": "STOP", "next": "quarantine，不进默认产物"}
  ],
  "owner": "direction/design owner",
  "precedence": 30,
  "failure_fixtures": ["FF-DIR-01", "FF-DIR-02", "FF-DIR-03"],
  "human_gate": "required"
}
```

## 职责与边界

产出**可比较**的方向卡，每张卡必须说清：色彩、字体、密度、动效、适用场景、取舍，以及参考来源
与 license。方向卡本身是非 canonical 产物；只有 Human 选定后，才把 `direction_choice` 写入
`UI-DESIGN.md`。

- **不选**：Human gate 是 required，"哪个更好看"不是 skill 能收敛的变量。
- **不抄方法**：外部方法只抽检查表或参考，不把它整条流程搬进来（1-6 的形态是自研）。
- **不默认**：两张卡并列且无法消解时展示候选并停下，不按顺序取第一。

## 停止条件与 Human gate

- 方向不唯一或参考缺来源 → `WAIT_HUMAN`（**不自动套模板**）。
- license unknown → `quarantine`，该参考不进默认产物。
- `human_gate=required`：选择必须由人签；未签则 S4 不得开工。

## 失败 fixture

- `FF-DIR-01` 正常：3 张卡 + Human 选 1，写入唯一 `direction_choice`。
- `FF-DIR-02` 冲突：两卡并列且 precedence 无法消解 → 不写入，展示候选，写入次数 0。
- `FF-DIR-03` 失败：参考 license unknown → quarantine，不进默认产物。

## 实现与证据

- 实现：`skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_direction`
- fixture：`tests/ui-agent-skills/fixtures/skills/FF-DIR-{01,02,03}/`
- 跑批：`python skills/ui/zj-ui-core/scripts/run_fixture.py tests/ui-agent-skills/fixtures/skills --recursive`

01 = Human 选定 `card-b` → `writes=1` 且 `content.direction_choice` 精确等于 `card-b`；
02 = 无 Human 选择 → `HUMAN_REVIEW_REQUIRED` + `writes=0`，候选仍完整列出（**不按顺序取第一**）；
03 = `license: unknown` 的卡片进 `quarantined`，可用候选只剩 `card-y`，零写入。

## 交接

- 上游：S2 通过的 brief revision。
- 下游：S4 `zj-ui-design-system` 只在 Human 选定方向后接手；回退目标是 S3 revision。
- 未签或超时 → `HUMAN_REVIEW_REQUIRED`，不自动改派。
