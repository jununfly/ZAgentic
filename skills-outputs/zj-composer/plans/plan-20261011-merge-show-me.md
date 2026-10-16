# Composer Plan

## Identity

- **plan_id:** `plan-20261011-merge-show-me`
- **title:** 将 humanlayer/skills 的 show-me skill 合并进本仓库（ZAgentic）
- **status:** `approved`
- **template_version:** `1`
- **generated_at:** 2026-10-11T20:40:00+08:00
- **composer_version:** zj-composer（user-level 安装，模板 v1）
- **human_review:** `approved`

## Intent

- **goal:** 把上游 humanlayer/skills@main 的 `plugins/show-me/skills/show-me`（会话内可视化解释技能：伪代码、调用树、组件树、文件树、Mermaid、diff、聚焦 HTML）以忠实合并方式引入本仓库公共技能目录，命名 `zj-show-me`。
- **scope:** 新增一个技能目录及唯一实体文件，完成两级 README 索引登记与条件性术语登记；不改动任何既有技能，不改构建脚本与 CI。
- **constraints:** ZJ- 前缀命名约定；公共技能须在所属 bucket README 与顶层 README 各有一条 name-linked 条目并参与递归发现（AGENTS.md）；Git 一律走 `./scripts/zj-git` 且分支加 PR、不直推 main；内容除 frontmatter 改名外逐字节忠实上游固定 revision（AGENTS.md 约束与验收证据要求）。
- **desired_output:** 一个可审阅的分支加 PR：新增 `skills/productivity/zj-show-me/SKILL.md`，两级 README 各一条目，`discover_catalog.py` 复跑零告警，四项验收输出留存 PR 描述。
- **exclusions:** 上游 `agents/openai.yaml`（内容仅 `policy: allow_implicit_invocation: false`，属 humanlayer 运行时策略文件，与 frontmatter `disable-model-invocation: true` 语义重复，本仓库无对应机制）；不做示例改写或本地化（如需另开切片）；不合并上游仓库其他 plugin。
- **permission_boundary:** 经 Human approval 后仅允许：新建技能目录一个文件、两个 README 各加一行、ZJ-CONTEXT.md 视判定加一行、建一次分支并做一个 feat commit、开一次 PR；除此之外禁止任何其他 write、network、publish、delete、install、modify 类副作用。

## Capability composition

### Step 1 — 上游取证与钉版

- **skill_or_workflow:** `zj-research`
- **role:** 上游证据生产与 revision 固定
- **reason:** 验收要求产物与上游固定 revision 逐字节一致（除改名），因此需要先把上游原始字节与 revision 钉住作为证据基线。
- **inputs:** 上游 humanlayer/skills@`653b6411c1f70c275a18e37673b042ff99f67ceb`（2026-10-08T21:54:25Z），SKILL.md blob `f0ccd047c136d7b702b385e0ecad775ccb773eae`（3328 字节），经 raw.githubusercontent.com 拉取。
- **outputs:** `/tmp/show-me-SKILL.md` 原始字节副本与 revision 记录（随 PR 描述留存）。
- **prerequisites:** 网络可达 raw.githubusercontent.com。
- **dependencies:** `none`
- **excluded_alternatives:** git submodule（本仓库技能为平面 vendored 结构，不引入子模块）；不记 revision 的裸拷贝（丢失证据基线，验收无从比对）。

### Step 2 — 技能本体落盘

- **skill_or_workflow:** `zj-implement`
- **role:** 新技能实体在目标 bucket 落地
- **reason:** 技能本体是本次合并唯一实体产物，验收要求 frontmatter 之外与上游逐字节一致，落盘属实现步骤，用 zj-implement 按既定输入落地最贴合。
- **inputs:** Step 1 的 `/tmp/show-me-SKILL.md`；目标名 `zj-show-me`（仅 frontmatter `name` 改一行，保留 `disable-model-invocation: true`，与本仓库 zj-teach、zj-debrief 等用户手调技能一致）。
- **outputs:** `skills/productivity/zj-show-me/SKILL.md`。
- **prerequisites:** Step 1 完成，且 Human approval 已选定 bucket 归属与命名（见 decisions_needed）。
- **dependencies:** `Step 1`
- **excluded_alternatives:** misc/ 或 engineering/ bucket（show-me 是高频会话内解释技能，与 zj-teach 同类归 productivity；若 Human 另选 bucket 则整体平移，索引步随动）。

### Step 3 — 索引与术语登记

- **skill_or_workflow:** `zj-neat-freak`
- **role:** 目录索引与治理登记收口
- **reason:** AGENTS.md 的验收约束要求公共技能在两级 README 有 name-linked 条目并参与递归发现，新领域术语需入 ZJ-CONTEXT.md，属治理收口范畴。
- **inputs:** Step 2 产物；`README.md` 与 `skills/productivity/README.md` 的既有条目格式（仿 zj-teach 行）；ZJ-CONTEXT.md 现状（924 行，不含逐技能条目）。
- **outputs:** 顶层 `README.md` 加一条目、bucket README 加一条目；ZJ-CONTEXT.md 视判定加一行，或将"不加"的判定理由记录进 PR 描述。
- **prerequisites:** Step 2 完成。
- **dependencies:** `Step 2`
- **excluded_alternatives:** `scripts/zagentic-skills-list`（实测仅枚举 engineering bucket 共 53 行，无 productivity 条目，无需改动）；`skills/engineering/zj-guide/SKILL.md`（未枚举 productivity 技能，若验收复跑报缺登记再补）。

### Step 4 — 机械验收与移交

- **skill_or_workflow:** `zj-dry-run`
- **role:** 提交前置闸门与 PR 移交
- **reason:** 仓库约定提交前走 zj-dry-run；验收 oracle 是 discover_catalog 复跑出现 zj-show-me 且四项 declaration 为真、零告警，机械可复核。
- **inputs:** Steps 1 至 3 全部产物；验收清单四项（见 Verification.step_checks）。
- **outputs:** 分支 `feat/merge-zj-show-me` 上一个 feat commit、一个 PR URL，PR 描述附四项验收输出与上游 revision 记录。
- **prerequisites:** 验收清单四项全绿后才进入提交。
- **dependencies:** `Step 2`、`Step 3`
- **excluded_alternatives:** 直推 main（违反分支加 PR 约定）；squash 合并（保留单一 feat commit 即可，无需压缩）。

## Gaps and suggestions

本合并所需能力（取证、建技能、治理登记、提交前验收）均已由现有目录技能覆盖，无未解决缺口。

suggested capability：若 WorkBuddy 运行时内建可视化机制与本技能出现行为重叠，另开切片裁定边界归属

- 建议来源与 fit caveat：用户级安装的 html-effectiveness 技能族（diagram、research 等子技能）在"用图解释话题"上粒度重叠——show-me 偏轻量内联文本图（伪代码、调用树、diff），html-effectiveness 偏单文件 HTML 产物与场景路由。二者不是同一能力，不构成合并阻断；仅当未来在同一运行时中出现行为重叠时才需裁定。

## Human checkpoints

- **approval_point:** Human approval：执行链启动前整体批准本 Plan，并就 decisions_needed 四项给出决定。
- **decisions_needed:** 1) bucket 归属：推荐 productivity/（备选 engineering/，理由见 Step 2）；2) 命名：推荐 zj-show-me（ZJ- 约定），保留原名需明确豁免；3) 内容忠实度：推荐除改名外逐字节保留上游文本；4) 确认排除上游 agents/openai.yaml。
- **rejection_path:** preserve this Plan and record the reason; do not execute.
- **side_effect_authorization:** 仅限 Human approval 授权的 permission_boundary 五类动作；任何未经审批的动作都不在授权范围内，发现即停。

## Evidence and provenance

- **skill_index_snapshot:** `catalog-v1-762896ae543a87d50757d3320845357e6efc3b4a69fa74057d5b21abdb760767`
- **catalog_revision_or_digest:** `762896ae543a87d50757d3320845357e6efc3b4a69fa74057d5b21abdb760767`
- **source_references:** selected=[zj-research -> skills/research/zj-research/SKILL.md | zj-implement -> skills/engineering/zj-implement/SKILL.md | zj-neat-freak -> skills/codebase-docs/zj-neat-freak/SKILL.md | zj-dry-run -> skills/engineering/zj-dry-run/SKILL.md]; excluded=[Step 1 -> github.com/humanlayer/skills 仓库结构（submodule 与裸拷贝为放弃项） | Step 2 -> 本仓库 misc/、engineering/ bucket 既有条目（bucket 取舍依据见 AGENTS.md 分工） | Step 3 -> scripts/zagentic-skills-list 与 skills/engineering/zj-guide/SKILL.md 实测枚举范围 | Step 4 -> 仓库分支加 PR 约定（直推与 squash 为放弃项）]; suggested=[suggested capability：若 WorkBuddy 运行时内建可视化机制与本技能出现行为重叠，另开切片裁定边界归属 -> ~/.workbuddy/skills/html-effectiveness/（用户级安装，非本仓库目录）]; gap=[none]
- **evidence_requirements:** 验收清单四项的全部命令输出必须留存于 PR 描述，缺一即不通过。
- **generated_assertions:** 上游目录仅含 SKILL.md（3328 字节）与 agents/openai.yaml（43 字节）两项（GitHub contents API 实测）；SKILL.md frontmatter 含 `disable-model-invocation: true`；上游 HEAD `653b6411c1f70c275a18e37673b042ff99f67ceb`（2026-10-08）。
- **unknowns:** 上游 revision 之后的上游更新不在本 Plan 追踪范围（按固定 revision 合并）。

## Verification

- **step_checks:** 1) 重跑 `discover_catalog.py`：productivity/zj-show-me 出现，四项 declaration 为 true，metadata_warnings 与 warnings 为空；2) frontmatter 之外与 `/tmp/show-me-SKILL.md` diff 为空；3) 两级 README 各 grep 命中 `zj-show-me` 一处；4) `./scripts/zj-git status` 仅含 permission_boundary 授权文件。
- **scenario_oracle:** discover_catalog.py 复跑 JSON 中 productivity/zj-show-me 条目 declarations 全 true 且零告警，机械可复核，不接受口头完成。
- **plan_acceptance:** `passed`

## Failure and rollback

- **failure_exits:** 验收第 1 项失败即停并回查 Step 3 登记；第 2 项失败即停并重放 Step 2，禁止手改内容迁就；第 3、4 项失败则修正后重跑全清单。
- **safe_stop:** 任一步失败即停，保留全部产物与证据，不回滚不清理，升级 Human review。
- **rollback:** PR 未合并前关闭 PR 并删除分支即完成回退（main 无污染）；若已误合 main，用 `./scripts/zj-git revert` 追加 revert commit，不改写已推历史。
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** zjj 主会话执行链（Human approval 后可由本会话按 Steps 1 至 4 推进），或交由具备文件编辑与 git 能力的执行 agent。
- **handoff_preconditions:** Human approval、完整 provenance、验收清单四项通过（plan_acceptance 置 passed）。
- **authority_statement:** Composer 仅组合与记录，无执行权；既有技能保留各自语义，执行副作用归 Human 授权的执行链。
