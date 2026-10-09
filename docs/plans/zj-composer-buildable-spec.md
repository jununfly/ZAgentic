---
doc-kind: plan
authority: process
status: proposed
plan-id: zj-composer-buildable-spec
version: 1
---

# Composer buildable spec

## Problem Statement

ZAgentic 已经拥有一组可复用的 skills、阶段化工作流、证据协议和路线图能力，但用户仍需要先理解仓库中的能力，再手工判断组合顺序、输入输出、依赖、验收方式和权限边界。这个组装动作容易遗漏能力、重复调用相近 skill，或把建议误当成已批准的执行。

本任务需要把已确认的 Composer 产品形态收敛成一项可实施的首版能力：给定一个目标和约束，生成可解释、可复核、可交给既有执行链的 Plan；当覆盖不足时，明确给出有限建议或逐项报告缺口。首版必须保持薄边界，不引入全局 router、第二个运行时、自动不可逆副作用或新的长期治理权威。

本规格覆盖 Composer skill scaffold、内置 Plan 模板 v1、能力索引和来源快照、Plan validator，以及两个固定 PoC 场景：外部仓库研究和工具组合设计。它为后续实现提供确定的输入、输出、负例、验收和撤销条件。

## Solution

实现一个 Human-invoked 的 Composer skill，稳定名称为 `zj-composer`，显式调用方式为 `/zj-composer`。Composer 读取用户目标、约束、期望产物、证据要求、权限边界和当前能力索引，生成一个带来源和理由的候选能力组合，并使用 Composer 自带的版本化 Plan 模板写出 Markdown Plan。Plan 只是一份可审阅的任务契约；Human 审阅并批准后，才交给现有的执行链。

Composer 的职责到“推荐、解释、生成 Plan”为止：

- 匹配仓库已有 skill 时，列出 skill、选择理由、前置条件、预期输入输出和排除的相近能力。
- 发现可信的外部或未来能力时，只给出带来源、适配判断和风险说明的 bounded suggestion。
- 没有可信建议时，为每个能力缺口单独输出精确格式的 `required skill：简短地描述缺失skill的形状`。
- 把 Human checkpoint、验证命令、场景 oracle、失败出口、回滚方式和副作用边界写入 Plan。
- 为每份 Plan 记录模板版本、能力索引快照、来源引用和生成上下文摘要，使结果可复核。

Composer 不批准或执行任务，不拥有 skill 语义、证据事实、Human 决策、Git 发布、网络写入、不可逆写入、失败恢复或长期文档治理。既有 skill/workflow、证据协议、执行链和文档治理分别保留这些权威。

首个 PoC 固定两个 fixture，输出版本化 Markdown Plan 和验证材料到各自的 `skills-outputs/zj-composer/` 场景目录。PoC 不修改现有 skill 定义，不自动执行不可逆动作；移除实验层后，原有工作流与历史产物必须可用。

## User Stories

1. As a ZAgentic user, I want to describe a goal and constraints in one request, so that I do not have to manually search every skill before planning the work.
2. As a ZAgentic user, I want Composer to show which existing skills it selected, so that I can inspect the proposed capability set.
3. As a ZAgentic user, I want a reason for every selected capability, so that I can challenge a weak or redundant recommendation.
4. As a ZAgentic user, I want Composer to show the order of capability steps, so that I can see how discovery, planning, execution, verification, and closeout connect.
5. As a ZAgentic user, I want each step to declare its expected inputs and outputs, so that handoff omissions are visible before execution.
6. As a ZAgentic user, I want prerequisites and blocking dependencies recorded, so that an execution chain cannot start from an incomplete plan.
7. As a ZAgentic user, I want evidence requirements recorded beside the step that produces them, so that claims remain attributable to observable sources.
8. As a ZAgentic user, I want Human decision points called out explicitly, so that approval is required where the task or side effect warrants it.
9. As a ZAgentic user, I want permission and side-effect boundaries stated in the Plan, so that a recommendation cannot silently authorize writes, network calls, or publication.
10. As a ZAgentic user, I want a bounded suggestion when a credible external or future capability exists, so that I know where the current catalog is insufficient without treating the suggestion as installed.
11. As a ZAgentic user, I want one exact `required skill：...` line per unresolved capability gap, so that missing capability requests can be reviewed or turned into future skill work.
12. As a ZAgentic user, I want unresolved gaps to distinguish “no match” from “possible external suggestion,” so that I can choose whether to research, build, or defer the capability.
13. As a ZAgentic user, I want Composer to surface conflicting or overlapping skills, so that I can choose deliberately instead of receiving an accidental duplicate workflow.
14. As a ZAgentic user, I want stale or unverifiable source metadata flagged, so that I do not mistake an old skill description for current behavior.
15. As a ZAgentic user, I want a Plan to record the Plan-template version, so that an old Plan keeps its original meaning after the template evolves.
16. As a ZAgentic user, I want a Plan to include provenance for its skill index and external sources, so that another Human can reproduce the recommendation.
17. As a ZAgentic user, I want a Plan to include verification commands and a scenario oracle, so that acceptance is based on observable behavior rather than narrative confidence.
18. As a ZAgentic user, I want failure exits and rollback steps, so that a rejected or interrupted plan has a known safe stopping point.
19. As a Human reviewer, I want to approve or reject a generated Plan before execution, so that Composer remains advisory and I retain authority over side effects.
20. As a Human reviewer, I want rejection to be represented as a review outcome rather than an implicit execution attempt, so that no side effect is attributed to a plan that was not approved.
21. As an existing skill owner, I want Composer to preserve my skill's semantic and execution ownership, so that Composer does not become a second implementation of the workflow.
22. As an evidence-protocol owner, I want Composer to cite evidence sources without rewriting evidence facts, so that provenance and verification remain governed by the evidence protocol.
23. As an execution-chain owner, I want an approved Plan to hand off through the existing chain, so that Composer does not introduce a parallel executor or runtime.
24. As a documentation-governance owner, I want generated Plans treated as process artifacts, so that they do not silently become durable rules or architecture authority.
25. As a maintainer, I want Composer to discover public skills recursively through the repository's existing catalog rules, so that a new compliant skill can become discoverable without a second registry.
26. As a maintainer, I want the capability snapshot to identify the source revision and collection time, so that a Plan can be audited against the catalog that produced it.
27. As a maintainer, I want malformed skill metadata to be reported as an index warning, so that Composer does not fabricate a capability from incomplete data.
28. As a maintainer, I want a fixed external-repository-research fixture, so that repository research composition can be tested deterministically.
29. As a maintainer, I want a fixed tool-combination-design fixture, so that multi-skill assembly can be tested independently of a live user session.
30. As a maintainer, I want negative fixtures for no match, conflict, stale source, missing prerequisite, and Human rejection, so that the advisory boundary is tested under failure and disagreement.
31. As a maintainer, I want validation to fail when a selected skill has no reason or provenance, so that plausible-looking but unauditable Plans cannot pass.
32. As a maintainer, I want validation to fail when a gap line deviates from the exact required-skill format, so that downstream gap handling remains mechanically parseable.
33. As a maintainer, I want validation to fail on authority bypass, undeclared side effects, unapproved writes or network calls, and secret leakage, so that the PoC cannot expand its authority accidentally.
34. As a maintainer, I want removal validation to restore the pre-Composer path and preserve historical artifacts, so that the experiment remains reversible.
35. As a maintainer, I want descriptive observations such as elapsed time, retries, manual edits, and Plan adoption recorded separately from hard gates, so that unstable manual-assembly comparisons are not presented as causal proof.
36. As a future contributor, I want the Plan contract and validator to be the highest test seam, so that new recommendation heuristics can evolve without duplicating end-to-end tests for every internal helper.

## Implementation Decisions

### Product boundary and invocation

- Composer is a public, Human-invoked skill in the productivity bucket. Its invocation is explicit; it is not a default router and is not automatically selected by the model for every task.
- The first implementation exposes a skill workflow and local validation helpers. It does not create a global service, session state store, hook system, transcript/model sheet, host runtime, or shipping integration.
- The consuming execution workflow remains responsible for approved execution, side effects, verification, failure recovery, and final recording.
- The generated Plan is process material. Durable rules, ADRs, glossary changes, and architecture authority require the existing documentation-governance path.

### Plan template v1

The Composer skill bundles a versioned Plan template. Every emitted Plan must identify `template_version: 1` and a stable Plan identifier. A template change requires an explicit version increment and must not silently reinterpret an existing Plan.

The v1 contract has these required sections and fields:

| Section | Required content |
| --- | --- |
| Identity | Plan id, title, status `planned`, template version, generated-at timestamp, Composer version, and Human review state |
| Intent | User goal, scope, constraints, desired output, exclusions, and permission boundary |
| Capability composition | Ordered steps; selected skill/workflow name; role; selection reason; expected inputs; expected outputs; prerequisites; dependencies; excluded alternatives |
| Gaps and suggestions | Bounded external/future suggestions with source and fit caveats, or one exact `required skill：...` line per unresolved gap |
| Human checkpoints | Approval points, decisions still needed, rejection path, and side-effect authorization requirements |
| Evidence and provenance | Skill-index snapshot id/revision, source references, evidence requirements, generated assertions, and explicit unknowns |
| Verification | Per-step verification command or observable check, fixed scenario oracle, and Plan-level acceptance result |
| Failure and rollback | Failure exits, safe stop behavior, rollback instructions, and undeclared-side-effect response |
| Handoff | Consuming execution chain, handoff preconditions, and statement that Composer has no execution authority |

The Plan status is limited to `planned`, `approved`, `rejected`, `superseded`, or `cancelled` while Composer owns the artifact. Once approved, the consuming workflow owns any `running`, `blocked`, `failed`, `verified`, `recorded`, or `rolled_back` transitions; Composer must not simulate these transitions.

### Capability index and provenance snapshot

- Composer reads the existing recursive public-skill discovery surface and derives a per-skill capability record from compliant frontmatter, bucket index entry, root index entry, and the skill's declared inputs, outputs, dependencies, and boundaries.
- The index is a generated read view, not a second durable registry. It must record the source file revision or content digest, discovery timestamp, and any metadata warnings.
- A Plan stores the snapshot identifier and the source references used for each selected, excluded, suggested, or gap-related capability.
- Stale or missing source metadata is a validation warning or hard failure when it affects a selected capability's name, boundary, or output contract; Composer must not invent missing semantics.
- Existing skill names and their semantic owners remain authoritative. Composer may normalize presentation but cannot rewrite a skill's contract.

### Selection and gap protocol

- A match is valid only when the capability's declared scope covers the requested need and its prerequisites fit the stated constraints.
- Each selected capability has exactly one concise reason tied to an input requirement or acceptance requirement. Additional caveats go in constraints or risks.
- Conflicting candidates are retained as alternatives with the conflict reason; Composer chooses only when the declared constraints resolve the conflict, otherwise it emits a Human decision point.
- A credible external/future suggestion must include its source, why it may fit, what is unverified, and the boundary that prevents it from being treated as installed.
- If no credible suggestion exists, emit one line for each gap using exactly `required skill：简短地描述缺失skill的形状`; no extra prefix, ASCII colon, numbering, or merged gap line is allowed.
- Gap lines are recommendations for future work. They do not create a skill, alter the index, or add a roadmap node automatically.

### PoC fixtures and output contract

The first fixture asks Composer to plan an external repository research task with fixed repository URL/revision, research questions, evidence requirements, and a no-write permission boundary. Its oracle checks that research discovery, primary-source evidence capture, capability-fit analysis, and report synthesis are ordered with reasons and provenance.

The second fixture asks Composer to design a tool combination for a bounded user goal with a fixed skill index, explicit constraints, required Human checkpoint, and no automatic execution. Its oracle checks that candidate skills, dependencies, missing capabilities, verification, handoff, and rollback are represented without introducing a router or executor.

Each fixture has fixed input, fixed skill-index snapshot, expected capability properties, forbidden capabilities, and an oracle result. A fixture may use a checked-in expected pattern rather than a byte-identical Plan, provided the validator checks the contract and the oracle checks the scenario-specific properties.

Generated artifacts are versioned Markdown Plans plus supporting snapshot, validation, and oracle records under the Composer output namespace. The two first-version fixture directories are fixed as `skills-outputs/zj-composer/external-repository-research/` and `skills-outputs/zj-composer/tool-combination-design/`. The output contract must preserve the input fixture id, Plan id, template version, and source revision so a result can be reproduced or compared later.

### Validation seam and mechanical gates

The primary seam is `Composer output → Plan validator → fixed-fixture oracle`. The validator operates on external behavior and artifact contents, not helper implementation details. It must report stable failure categories for:

- missing required Plan sections or fields;
- missing template version, source snapshot, or per-capability reason;
- incomplete provenance or unverifiable selected capability;
- malformed `required skill：...` gap lines;
- unresolved prerequisite or dependency contradictions;
- missing Human checkpoint for a side-effect-capable step;
- authority bypass, undeclared side effect, unapproved write or network call, or secret leakage;
- oracle mismatch, missing failure/rollback contract, or broken removal regression.

Hard acceptance gates for the PoC are:

1. Both fixed fixture oracles pass.
2. Every Plan satisfies the v1 schema and provenance contract.
3. Every selected capability has a reason, prerequisite assessment, and source reference.
4. Every unresolved gap uses the exact required-skill format.
5. Authority bypass, undeclared side effects, unapproved writes or network calls, and secret leakage are all zero.
6. Removing the experimental layer restores the original execution path and preserves historical artifacts.

Elapsed time, interaction count, manual edits, retries, recovery steps, rejection count, and Plan adoption are recorded only as descriptive observations. They are not acceptance gates and are not compared causally to an unstable “manual assembly baseline.”

### Negative cases and safe behavior

The validator and fixtures must cover:

- no matching skill and no credible suggestion: emit only the required-skill line(s) and stop before handoff;
- multiple conflicting skills: preserve alternatives and require a Human choice;
- stale or changed source revision: mark the Plan stale and require regeneration or explicit review;
- missing prerequisite: keep the Plan unapproved and identify the blocking prerequisite;
- Human rejects the Plan: record rejection and reason, perform no execution, and preserve the rejected artifact;
- a request that would require a second authority or automatic irreversible action: refuse that step and explain the boundary.

### Implementation order

1. Freeze the v1 Plan schema, status transitions, index snapshot contract, gap syntax, and two fixture oracles.
2. Scaffold the public Composer skill and register it through existing recursive discovery and README rules.
3. Bundle the Plan template and supporting references with the Composer skill.
4. Implement capability-index reading and provenance snapshot generation without adding a durable registry.
5. Implement the Plan validator at the output seam.
6. Add the external-repository-research fixture and oracle.
7. Add the tool-combination-design fixture and oracle.
8. Add negative-case, security, handoff, and removal-regression checks.
9. Run Human review on the evidence package and decide whether to continue beyond the PoC.

Each implementation step must leave the original execution path usable. A failure in the experimental layer must stop at the Plan boundary and report evidence; it must not fall through to an unapproved side effect.

### Tracker publication status

This repository currently has no selected issue-tracker mapping or triage agreement in the active documentation surface. The requested buildable spec is therefore published as a local `docs/plans/` process artifact. Before converting it into an issue or applying `ready-for-agent`, run the repository collaboration setup that selects the tracker and triage vocabulary; the tracker issue, if created later, must link back to this file rather than become a second specification.

## Testing Decisions

- Test the external behavior of the Composer output and validator through the single high seam: fixture input and index snapshot in, Plan plus validation/oracle records out.
- Prefer deterministic fixture tests over live skill discovery, live network access, or model-output snapshots. Network-backed research is represented by fixed source references and a no-write boundary in the first PoC.
- Validate both positive and negative behavior. A Plan that looks complete but lacks provenance, a reason, a checkpoint, or a safe failure exit must fail mechanically.
- Test the exact Unicode gap prefix and reject ASCII-colon, numbered, merged, or otherwise malformed variants.
- Test template version pinning by changing the template fixture and verifying that an existing Plan is not reinterpreted silently.
- Test stale-source handling by changing the recorded source revision and requiring regeneration or explicit Human review.
- Test authority boundaries by instrumenting the PoC harness for writes, network calls, Git publication, and secret-shaped output; all undeclared or unapproved effects must fail.
- Test rejection and missing prerequisites as terminal pre-handoff states with preserved artifacts.
- Test removal by running the original pre-Composer fixture path after disabling or deleting the experimental layer and comparing its historical artifacts.
- Use the repository's existing frontmatter, recursive discovery, documentation-map, and skill-index validators as prior art for catalog and registration checks. New tests should not duplicate those validators; they should assert Composer-specific output contracts and fixture oracles.
- Keep descriptive measurements in an observation record. Do not turn them into causal performance or manual-baseline success gates.

## Out of Scope

- A global skill router, suite runtime, hook framework, transcript/model-sheet state, host-specific runtime state, or shipping/PR glue.
- Automatic execution of any irreversible action, network write, Git write, publication, credential use, or external side effect.
- A second durable capability registry, evidence database, decision database, roadmap, or governance authority.
- Automatic creation, installation, merging, or modification of a missing skill from a `required skill：...` line.
- Replacing existing skill semantics, execution chains, evidence protocols, Human approvals, or documentation governance.
- Production claims based on “30% faster than manual assembly” or execution-success comparison to a manually assembled baseline.
- Broad domain coverage beyond the two fixed PoC fixtures.
- A live external-repository crawler or unconstrained internet research service.
- Automatic publication to an issue tracker when repository tracker mapping is not configured.
- Making generated Plans long-lived architecture, ADR, glossary, or policy authority without a separate governance decision.

## Further Notes

- The governing product decisions are recorded in the Composer design authority and ADR 0005; this plan turns those decisions into an implementation contract.
- The roadmap paired with this spec is the execution map. It is a separate process artifact and must be changed through the `zj-roadmap-driven` CLI, then rendered for Human review.
- The first review checkpoint should inspect the two fixture outputs, validator diagnostics, negative-case evidence, and removal-regression result together. A passing validator alone does not authorize production rollout.
- If implementation reveals a new durable domain term, add it to the root glossary before merge. If it reveals a new authority boundary, stop and record an ADR decision before changing the product form.
- The PoC can collect time and interaction observations to inform later design, but any future metric used as a hard gate requires its own baseline definition and measurement protocol.
