# Composer Plan

<!-- Composer template v1. Keep existing Plans pinned to their original version. -->

## Identity

- **plan_id:** `issue-180-template-registry-catalog-root`
- **title:** 修复 validate_plan.py 在 user-level 安装下的模板 registry 路径解析
- **status:** `planned`
- **template_version:** `1`
- **generated_at:** `2026-10-19T13:09:02+08:00`
- **composer_version:** `zj-composer-plan-v1`
- **human_review:** `pending`

## Intent

- **goal:** 修复 Issue #180，使 user-level flat 安装中的 validate_plan.py 不再因硬编码 skills/productivity/zj-composer 路径产生 template_registry_invalid，同时保持 Issue #177 已建立的 catalog-root 探测和模板完整性校验边界。
- **scope:** 检查并调整 skills/productivity/zj-composer/scripts/validate_plan.py、与 catalog-root 解析共享的辅助逻辑、Composer 回归测试及 validator contract；覆盖 monorepo-dev、installed-flat 和 Issue #180 所述 user-level wrapper 输入。
- **constraints:** 复用 Issue #177 的显式 --root > ZAGENTIC_ROOT > 基于脚本位置探测优先级；按内容识别布局，不依赖 parents[N] 或 productivity bucket；保持已注册 registry 的 schema、模板路径越界和 SHA-256 mismatch 为 error；缺失的可选 registry 元数据按 Issue #180 方案降为可见 warning。
- **desired_output:** 一份可合并的代码补丁、覆盖两种布局和 registry 异常语义的回归测试、同步的 validator contract，以及能证明 Issue #180 复现用例不再阻塞 handoff 的验证结果。
- **exclusions:** 不改变 Plan v1 字段结构、catalog snapshot schema、技能 frontmatter 语义或 Composer 的无执行权限边界；不新增技能、不执行 Plan 中的 capability、不提交 Git、不发布网络内容。
- **permission_boundary:** Composer 只产出本 Plan 和 provenance；no write, network, publish, credential, or irreversible actions are allowed from this Plan; Human approval is required before any execution-chain side effect in the repository or test temporary directories。

## Capability composition

List steps in execution order. Each selected capability needs one reason tied to
an input or acceptance requirement.

### Step 1 — 固化 #177/#180 代码证据

- **skill_or_workflow:** `zj-code-research`
- **role:** 建立 Issue、实现、测试和契约之间的证据映射
- **reason:** 需要把 Issue #180 的复现、Issue #177 的实际 diff 及当前 validator/discovery 代码对齐，作为后续实现和验收的输入证据。
- **inputs:** Issue #180 正文与复现命令、Issue #177 修复提交 30a999d 与合并提交 fcb0586、当前 validate_plan.py、discover_catalog.py、generate_snapshot.py、相关测试和 validator contract。
- **outputs:** 带文件与行号的证据清单，明确 resolver 优先级、布局识别、当前硬编码点、现有测试盲区及不可回归的行为。
- **prerequisites:** 当前仓库可读且 Issue #177/#180 的本地或远程引用可核对。
- **dependencies:** `none`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

### Step 2 — 复现并界定失败边界

- **skill_or_workflow:** `zj-diagnosing-bugs`
- **role:** 建立可重复的根因诊断和场景矩阵
- **reason:** 验收要求同时证明 monorepo 原路径继续通过、flat user-level 路径通过、缺失 registry 不再制造致命误报，并且真正损坏的 registry 仍被拒绝。
- **inputs:** Step 1 证据、flat 安装临时目录、monorepo fixture、模板 registry/template 文件及当前 validate_template_pin 输出。
- **outputs:** 最小复现、期望/实际对照、根因链和四类场景矩阵：monorepo、flat catalog-root、Issue #180 的 wrapper root、registry 缺失或损坏。
- **prerequisites:** 可创建隔离临时 fixture，且不触碰真实安装目录或仓库 Git 状态。
- **dependencies:** `Step 1`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

### Step 3 — 设计共享 catalog-root 与 registry 定位边界

- **skill_or_workflow:** `zj-codebase-design`
- **role:** 定义单一、可复用的 root/layout/package 定位 seam
- **reason:** 验收要求 validate_plan 与 Issue #177 保持同一 root 解析行为，不能再复制一个 skills/productivity 路径分支或固定祖先深度。
- **inputs:** Step 1 的代码证据、Step 2 的场景矩阵、Issue #177 的 resolve_root/detect_layout/skill_files 逻辑和 snapshot contract。
- **outputs:** 一个共享定位方案：显式 --root 优先于 ZAGENTIC_ROOT，再回退到脚本位置探测；内容识别 installed-flat 与 monorepo-dev；从已识别的 Composer skill package 定位 registry；对 `--root ~/.workbuddy` 这类包裹 flat catalog 的输入定义兼容归一化或结构化失败行为。
- **prerequisites:** Human 明确接受“--root 兼容 wrapper 输入”与“缺失 registry 为 warning、损坏 registry 为 error”两项边界。
- **dependencies:** `Step 1`, `Step 2`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

### Step 4 — 先行建立回归测试

- **skill_or_workflow:** `zj-tdd`
- **role:** 把 Issue #180 的行为契约固化为可执行测试
- **reason:** 现有 21 个 discovery 测试和 template-pinning regression 只证明 monorepo 路径，不能证明 flat validator；这些输入和验收要求必须先转成失败用例，以防修复只通过当前布局。
- **inputs:** Step 2 场景矩阵和 Step 3 定位契约。
- **outputs:** 覆盖以下断言的测试：monorepo registry pin baseline 通过；flat catalog-root registry pin 通过；Issue #180 wrapper root 能被归一化或给出明确结构化诊断；显式 root/env/location-derived 优先级一致；缺失 registry 是 warning；非法 JSON/schema、越界 path、缺失 template 和 digest mismatch 仍是 error。
- **prerequisites:** 测试 fixture 使用临时目录，测试结果不写入真实安装目录，且不会修改 checked-in Plan 或 snapshot。
- **dependencies:** `Step 3`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

### Step 5 — 实现并同步契约

- **skill_or_workflow:** `zj-implement`
- **role:** 按已批准 seam 完成 validator、共享解析逻辑和文档的代码补丁
- **reason:** 验收要求代码实际复用 #177 的 root precedence/layout detection，并让完整合规 Plan 不再因 user-level registry 位置误报而失去 handoff eligibility。
- **inputs:** Step 3 的设计决策、Step 4 的红绿测试、当前 Composer 脚本和 validator/snapshot contract。
- **outputs:** validate_plan 使用共享 catalog-root/package 定位；模板 registry 读取不再硬编码 productivity bucket；缺失 registry 产生 warning 而非 error；registry 内容损坏或模板 digest 不符仍拒绝；CLI、snapshot 默认路径和文档使用同一 resolved root 语义。
- **prerequisites:** Step 4 回归测试已明确失败原因，且 Human 已批准 root 兼容和 registry warning 语义。
- **dependencies:** `Step 4`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

### Step 6 — 做标准与规格双重复核

- **skill_or_workflow:** `zj-code-review`
- **role:** 复核补丁是否同时满足 Issue #180 和仓库工程约束
- **reason:** 最终验收需要确认没有重新引入硬编码 bucket、固定 parents[N]、静默吞掉 registry 损坏，且 #177 的 monorepo 行为和 #180 的 flat 行为都被测试保护。
- **inputs:** Step 5 代码补丁、测试输出、Issue #177/#180 证据清单和 contract diff。
- **outputs:** standards/spec 两轴复核结果、未解决 finding 清单、完整回归命令及可复核的通过条件。
- **prerequisites:** Step 5 代码和测试结果已落盘。
- **dependencies:** `Step 5`
- **excluded_alternatives:** The fixed skills/productivity path and duplicated parents[N] resolver are excluded by the Issue #177 contract.

## Gaps and suggestions

No unresolved installed capability gap; all selected workflows are present in the pinned catalog snapshot. No external suggestion or skill installation is required.

## Human checkpoints

- **approval_point:** Human must approve the shared root contract, the compatibility treatment for `--root ~/.workbuddy`, and the distinction between missing optional registry metadata (warning) and malformed or mismatched registry data (error) before Step 4 or Step 5 starts.
- **decisions_needed:** Confirm that validator input root is normalized to the same effective catalog root used by snapshot generation; confirm that a missing registry may not block an otherwise complete Plan, while an unreadable or integrity-invalid registry remains blocking.
- **rejection_path:** preserve this Plan and record the reason; do not execute.
- **side_effect_authorization:** Before approval, no implementation or repository change is authorized. After approval, only scoped code/test artifact writes in the repository and isolated temporary directories are allowed; Git publication, network release, credentials, and irreversible actions require a separate Human authorization.

## Evidence and provenance

- **skill_index_snapshot:** `catalog-v1-df316e12beb071712f283a80fc86a6139bda2bbea38d188fd2d4a94d07e721d0`
- **catalog_revision_or_digest:** `df316e12beb071712f283a80fc86a6139bda2bbea38d188fd2d4a94d07e721d0`
- **source_references:** `selected=[zj-code-research -> skills/research/zj-code-research/SKILL.md | zj-diagnosing-bugs -> skills/engineering/zj-diagnosing-bugs/SKILL.md | zj-codebase-design -> skills/engineering/zj-codebase-design/SKILL.md | zj-tdd -> skills/engineering/zj-tdd/SKILL.md | zj-implement -> skills/engineering/zj-implement/SKILL.md | zj-code-review -> skills/engineering/zj-code-review/SKILL.md]; excluded=[Step 1 -> skills/productivity/zj-composer/references/snapshot-contract.md | Step 2 -> skills/productivity/zj-composer/references/snapshot-contract.md | Step 3 -> skills/productivity/zj-composer/references/snapshot-contract.md | Step 4 -> skills/productivity/zj-composer/references/snapshot-contract.md | Step 5 -> skills/productivity/zj-composer/references/snapshot-contract.md | Step 6 -> skills/productivity/zj-composer/references/snapshot-contract.md]`
- **evidence_requirements:** Verify Issue #180 at https://github.com/jununfly/ZAgentic/issues/180; verify Issue #177 implementation in commit 30a999d and merge commit fcb0586; cite validate_plan.py:295 and :831, discover_catalog.py:128-159, generate_snapshot.py:174-197, and run_regressions.py:881-900; reproduce flat user-level failure and rerun all relevant unit/regression tests.
- **generated_assertions:** Current code still has the Issue #180 hard-coded registry path and fixed-depth default; Issue #177 already provides the reusable root precedence and layout detection model; existing green regression output does not cover flat validator layout; the repair must preserve digest/schema hard gates while changing only missing-registry severity.
- **unknowns:** The issue's `--root ~/.workbuddy` form names the installation container rather than the flat catalog directory described by the #177 contract; this Plan assumes backward-compatible normalization for that wrapper and requires Human approval before implementation. The exact final helper module location is intentionally left to Step 3, but duplicate resolver logic is not allowed.

## Verification

- **step_checks:** Step 1 produces line-linked evidence; Step 2 reproduces the current error in an isolated flat fixture; Step 3 records the root/layout/package contract; Step 4 fails before the fix and passes after it; Step 5 passes the focused tests and full Composer regressions; Step 6 reports no unresolved standards/spec finding.
- **scenario_oracle:** A valid Plan using template_version 1 and a snapshot generated from a flat user-level catalog has no template_registry_invalid error and remains handoff-eligible when its other Human/provenance/acceptance gates pass; the monorepo fixture remains valid; missing registry is a visible warning; malformed registry, path escape, missing template, and digest mismatch remain errors.
- **plan_acceptance:** `pending`

## Failure and rollback

- **failure_exits:** Stop if root resolution is ambiguous, a registry is malformed, a template digest mismatches, a snapshot source is stale, or any test reveals a monorepo regression; preserve diagnostics and do not claim handoff eligibility.
- **safe_stop:** Keep the Plan in planned/pending state, retain the failing fixture and command output as evidence, and escalate the unresolved root or registry policy decision to the Human.
- **rollback:** Revert only the scoped code, test, and contract changes from the approved implementation patch; retain the Plan, snapshot, and diagnostic evidence for review. Do not delete or rewrite existing immutable snapshots.
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** Human-approved `zj-tdd` -> `zj-implement` -> `zj-code-review` execution chain, followed by the repository's normal test and review gate.
- **handoff_preconditions:** Human approval of the root and registry semantics, complete provenance, focused and full regression checks passing, no unresolved standards/spec findings, and a valid template-version binding whenever the registry is present.
- **authority_statement:** Composer proposes and documents; it has no execution authority.
