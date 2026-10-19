# UI Agent Skills — Canonical Artifact Schema Lock (v0.1)

> **冻结文档。** 本文件定义六类 ZAgentic-owned canonical artifact 的 schema、字段 `owner/source/requiredness`、`unknown policy` 与版本校验。它是跨会话、文档编辑与 adapter 删除后的**唯一恢复边界**（见 roadmap 1-2 决策：「六类 ZAgentic-owned canonical artifact，尤其是 ui-flow/v1；adapter 只能提交带 source_revision/projection_id 的投影」）。
>
> 本文件属于路线图**计划层交付物**（roadmap 1-2-1），仅冻结契约，不落地产品代码。后续 1-2-4 用 golden fixture 实测「必填保留率 100% / 静默丢失=0 / 未声明 warning=0」。

## 全局不变式（来自 MASTER L50-56，逐字落地为本 schema 的硬约束）

- **唯一 owner**：每个字段有且只有一个 canonical owner；adapter 只能提交带 `projection_id` / `source_revision` 的**投影**，不得拥有 canonical 字段值。
- **unknown 不压空**：`unknown` 必须保留 `{path, raw, reason, source}` 四元组，禁止压成空值或省略。
- **必填零丢失**：必填语义字段转换后 100% 保留；静默丢失数 = 0、未声明 warning 数 = 0。
- **幂等键**：转换绑定 `(fixture_id, input_revision, adapter_version, mapping_version)`；临时版本校验通过后**原子提交**。
- **恢复边界**：adapter 删除 / 远程服务关闭 / 网络断开时，最后一个完整 canonical revision 是唯一恢复路径。

## 六类 artifact 总览

| # | Artifact | Canonical owner | 必须表达 |
| --- | --- | --- | --- |
| 1 | `UI-BRIEF.md` | brief/contract owner | 目标用户、任务、约束、成功标准、unknown/source |
| 2 | `UI-DESIGN.md` | direction/design owner | 方向选择、token、字体/颜色、组件原则、取舍、provenance |
| 3 | `ui-flow/v1` | flow/schema owner | screen/component/state/action/intent/acceptance/source/unknown |
| 4 | `review record` | review owner | Human gate、问题、决策、理由、期限、审阅者 |
| 5 | `verification receipt` | verification owner | claim/threshold/command/commit/fixture+env hash/artifact/状态 |
| 6 | `handoff` | handoff owner | 变更摘要、运行命令、风险、已知限制、fallback、责任人 |

字段表约定：`owner` = canonical 字段所有者；`source` = 字段值的可归因来源；`required` = 必填性（`yes` / `conditional` / `required-if-external` / `no`）；`unknown policy` = 缺失或不明时的处置。

---

### 1. `UI-BRIEF.md`

- **owner**：brief/contract owner（唯一写 owner）
- **version**：`brief_schema_version`(semver, 初值 `1.0.0`) + `revision`(sha256 of canonical content) + `input_revision`(引用来源对话/文档版本)。迁移：minor 追加可选字段；major 需 migration 脚本且 golden round-trip 通过。
- **fields**：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `goal_users` | string[] | brief/contract owner | Human dialogue / `UI-BRIEF.md` 编辑 | yes | 缺失 → `unknown{path:"goal_users",raw:null,reason:"未声明目标用户",source:<对话/文档ID>}` |
| `goal_task` | string | brief/contract owner | Human dialogue / `UI-BRIEF.md` | yes | 同上 |
| `constraints` | string[] | brief/contract owner | Human dialogue / `UI-BRIEF.md` | yes（至少 1 条，或显式 `empty-with-reason`） | 允许含 unknown 条目 |
| `success_criteria` | string[] | brief/contract owner | Human dialogue / `UI-BRIEF.md` | yes | 缺失 → `unknown` |
| `unknown[]` | list<{path,raw,reason,source}> | brief/contract owner | 解析/校验过程 | conditional | 必须保留四元组，禁止空值 |
| `source_ref` | object | brief/contract owner | adapter 输入引用 | no | adapter 仅可拥有**引用**，不得拥有字段值 |

- **adapter-owned**：provider 输入引用（仅引用，不拥有字段值）。
- **recovery**：无服务也能编辑并生成下一步 plan。

---

### 2. `UI-DESIGN.md`

- **owner**：direction/design owner（唯一写 owner）
- **version**：`design_schema_version` + `revision` + `source_revision`(来自 `UI-BRIEF.md`)。迁移同 brief 规则。
- **fields**：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `direction_choice` | string/enum | direction/design owner | `zj-ui-direction` 方向卡 + Human gate | yes | 无来源 → Human gate，不自动替选 |
| `tokens` | object{typography,color,spacing,density,motion} | direction/design owner | 方向卡 / Human 选择 | yes | contrast 不达标 → 阻断 |
| `typography` | object | direction/design owner | 方向卡 / Human 选择 | yes | 含字体 license 未知 → quarantine |
| `color` | object | direction/design owner | 方向卡 / Human 选择 | yes | contrast 不达标 → 阻断 |
| `component_principles` | string[] | direction/design owner | 方向卡 / Human 选择 | yes | — |
| `tradeoffs` | string[] | direction/design owner | 方向卡 | yes | — |
| `provenance` | object{source,reference,license} | direction/design owner | 外部参考 | required-if-external | 外部来源必须可归因；unknown source → quarantine |
| `unknown[]` | list<{path,raw,reason,source}> | direction/design owner | 解析 | conditional | 四元组保留 |

- **adapter-owned**：外部参考链接、渲染参数（仅投影）。
- **recovery**：可从文档重建 preview。

---

### 3. `ui-flow/v1`

- **owner**：flow/schema owner（**唯一写 owner**，语义 round-trip 与迁移器优先）
- **version**：`ui_flow_v1_schema_version` + `revision`；**schema lock**：`screen/component/state/action/intent/acceptance` 分义固定，breaking-change 走 gate。
- **fields**（六义分列，互不可合并）：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `screen` | object | flow/schema owner | brief/design/Human | yes | 缺失 → hard fail |
| `component` | object[] | flow/schema owner | design catalog | yes | 未注册组件 → 阻断 |
| `state` | object[] | flow/schema owner | flow 推导 | yes | 缺失 → hard fail |
| `action` | object[] | flow/schema owner | flow 推导 | yes | 危险 action → deny |
| `intent` | object[] | flow/schema owner | brief/Human | yes | 缺失 → hard fail |
| `acceptance` | object[] | flow/schema owner | brief/Human | yes | 缺失 → hard fail |
| `source` | object | flow/schema owner | 上游 artifact 引用 | yes | 必须可归因 |
| `unknown[]` | list<{path,raw,reason,source}> | flow/schema owner | 解析 | conditional | 四元组保留 |

- **语义 round-trip**：`screen ↔ component ↔ state ↔ action ↔ intent ↔ acceptance` 全链路可离线重建；双 owner / 状态·动作·意图丢失 → **hard fail**。
- **adapter-owned**：provider projection ID、布局映射（仅投影，不拥有 canonical）。
- **recovery**：可离线重放状态/动作/意图。

---

### 4. `review record`

- **owner**：review owner（唯一写 owner）
- **version**：`review_schema_version` + `revision`
- **fields**：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `human_gate` | enum{APPROVED,REJECTED,NEEDS_CHANGES} | review owner | Human 审阅 | yes | 未签 → `HUMAN_REVIEW_REQUIRED` |
| `questions` | string[] | review owner | 审阅过程 | yes（可为空但需理由） | — |
| `decision` | string | review owner | Human | yes | — |
| `rationale` | string | review owner | Human | yes | — |
| `deadline` | date | review owner | 项目约束 | no | — |
| `reviewer` | string | review owner | Human/系统 | yes | — |
| `unknown[]` | list<{path,raw,reason,source}> | review owner | 解析 | conditional | 四元组保留 |

- **adapter-owned**：provider 评论 ID（仅引用）。
- **recovery**：远程评论消失不影响审计。

---

### 5. `verification receipt`

- **owner**：verification owner（唯一写 owner）
- **version**：`receipt_schema_version` + `revision`；绑定幂等键 `(fixture_id, input_revision, adapter_version, mapping_version)`。
- **fields**（对应 MASTER L109）：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `claim` | string | verification owner | verification | yes | — |
| `check` | string | verification owner | matrix | yes | — |
| `risk` | string | verification owner | matrix | yes | — |
| `fixture_hash` | sha256 | verification owner | fixture-manifest | yes | — |
| `environment_fingerprint` | object | verification owner | env | yes | 缺失 → `BLOCKED` |
| `oracle_version` | string | verification owner | oracle | yes | — |
| `threshold` | object | verification owner | metrics | yes | — |
| `command` | string | verification owner | run | yes | — |
| `commit` | sha | verification owner | VCS | yes | — |
| `artifact_hash` | sha256 | verification owner | artifact | yes | — |
| `observed` | object | verification owner | run | yes | — |
| `status` | enum{PASS,FAIL,BLOCKED,HUMAN_REVIEW_REQUIRED,QUARANTINED,STALE} | verification owner | aggregation | yes | — |
| `reviewer` | string | verification owner | Human | yes | — |
| `expiry` | date | verification owner | policy | yes | 过期 → `STALE` |
| `unknown[]` | list<{path,raw,reason,source}> | verification owner | 解析 | conditional | 四元组保留 |

- **adapter-owned**：runner/provider metadata（仅 metadata，不拥有 canonical 字段）。
- **recovery**：可从本地 fixture 重放。

---

### 6. `handoff`

- **owner**：handoff owner（唯一写 owner）
- **version**：`handoff_schema_version` + `revision`
- **fields**：

| field | type | owner | source | required | unknown policy |
| --- | --- | --- | --- | --- | --- |
| `change_summary` | string | handoff owner | skill 输出 | yes | — |
| `run_commands` | string[] | handoff owner | skill 输出 | yes | — |
| `risks` | string[] | handoff owner | 分析 | yes | — |
| `known_limitations` | string[] | handoff owner | 分析 | yes | — |
| `fallback` | string | handoff owner | 分析 | yes | — |
| `owner` | string | handoff owner | 项目 | yes | — |
| `unknown[]` | list<{path,raw,reason,source}> | handoff owner | 解析 | conditional | 四元组保留 |

- **adapter-owned**：外部项目链接（仅引用）。
- **recovery**：项目可脱离 adapter 继续维护。

---

## 校验通过判据（对齐 1-2-1 退出条件）

1. **字段 owner/source/requiredness/unknown policy 已冻结**：上表六类逐字段定义完毕，每个字段恰有一个 canonical owner；adapter 仅拥有投影/引用，不拥有 canonical 字段值。✅（本文件声明）
2. **版本校验**：每类含 `schema_version` + `revision` + `source_revision`（ui-flow/v1 另含 schema lock 与 breaking-change gate）；adapter 投影带 `projection_id`/`source_revision`；临时版本校验通过后原子提交。✅（本文件声明）
3. **unknown policy**：`unknown` 一律保留 `{path,raw,reason,source}` 四元组，禁止压空。✅（全局不变式）
4. **实测项（由 1-2-4 用 golden fixture 落实，不在本文件内）**：必填字段保留率 100%、静默丢失=0、未声明 warning=0、语义 round-trip 通过、离线恢复通过。

> 本文件为 schema **冻结**层；第 4 项的数值化验证将在 1-2-3（ui-flow/v1 迁移规则）与 1-2-4（golden fixtures / semantic round-trip / 离线恢复）中实测，不在本节点内完成。
