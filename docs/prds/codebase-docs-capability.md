# Codebase Docs Capability Spec

## One-page overview

### Decision

Decision: approve. The Human owner accepted the `codebase-docs` capability boundary and its controlled migration model. Blocking findings: none. Non-blocking follow-up: tool selection for cross-project knowledge refinement remains a separate Initiative.

### Summary

Create a public `codebase-docs` skill bucket that governs one codebase's full documentation system without turning process material or raw evidence into durable truth. The change gives Human and Agent a shared map, a safe migration seam and a verifiable architecture-handbook layer.

### Platforms and scope

The skills run against local Git repositories on the existing supported Agent platforms. In scope are ZAgentic skill packaging, target-repository Markdown documentation and local source-map validation. External shared-knowledge publishing, automatic deletion and prescribed evidence-storage directories are out of scope.

### Ownership and tracking

Human owns the decision, migration confirmations and deletion approvals. This file is the delivery spec; [Issue #19](https://github.com/jununfly/ZAgentic/issues/19) and child Issues #20–#24 are the source architecture and acceptance record. Evidence: the reviewed Issues and current repository layout named in this Spec.

## Problem and goals

### Intent

建立 `codebase-docs` 作为 `skills/` 下与 `engineering/`、`research/` 等平行的公共 skill bucket。它服务于一个具体 codebase 的完整文档体系：发现、建立、阅读、维护和治理文档地图，并将当前事实、长期知识、过程上下文和证据面保持在清楚的边界内。

这不是一个通用知识库、共享研究产物仓库或自动归档器。它维护的是目标 codebase 的文档体系；Human 通过 prompt 明确发起治理任务，保有权威冲突、迁移和删除的最终决定权。

现有 GitHub Issues #19–#24 是本能力的架构手册与文档治理验收输入。本 Spec 固化它们之间的边界、目录归属和交付顺序。

### Goals

- 一个绿地 codebase 可以在 Human 确认后建立最小文档地图和所需类别，而不被强制套用不兼容的目录结构。
- 一个已有文档积累的 codebase 可以先得到只读分类和迁移提案；只有 Human 明确确认后才移动文件、修复链接、合并权威内容或删除过程材料。
- `docs/README.md` 成为人和 Agent 可读的文档地图：按问题导航，说明类别、权威范围、生命周期与入口；不另建容易漂移的机器 manifest。
- 长期文档与过程文档统一纳管、分类隔离。过程材料支撑动态规划、可观测/可介入执行、焦点对齐和执行决策；它们完成使命后经沉淀、审计和 Human 确认才删除。
- 每个长期问题只有一个权威页面。冲突、重复权威、死链接、失效 source map 和不当的过程内容由 validator 报告为机械失败或 Human-review signal。
- 架构手册通过互补视图回答系统、分层、子系统、流程和横切规则问题；它不取代领域建模、ADR 决策或实现/运行时证据。

### Non-goals

- 不规定所有 codebase 的 `research/`、`evaluation/`、`artifacts/` 或 `evidence/` 目录。证据面由目标仓库发现；具体托管、创建或迁移由该仓库的 Human 在治理任务中决定。
- 不把代码、测试、fixture、原始 benchmark profile、日志、一次性评测输出或 Git history 复制为长期文档事实。
- 不由 Plan 完成、Issue 关闭或其他事件自动触发 closeout。治理仅由 Human 显式请求启动。
- 不自动裁决矛盾的权威断言、不接受 ADR、不把推断写成已实现能力，且不在没有二次确认时删除过程材料。
- 不在本版本实现跨项目共享知识炼制、工具选型、GitHub 知识发布或现有 `skills-outputs/` 的实际迁移。

## Design

### Alternatives considered

The accepted C1 topology keeps `zj-docs-ontology` as the Human-invoked governance entry point and composes focused skills. It rejects a separate top-level router that duplicates the ontology boundary and a monolithic documentation skill that absorbs domain modeling, debrief and workspace governance. It also excludes a shared-knowledge publisher because its data model and tool choice require a separate decision.

### Document map and navigation

默认文档地图为 `docs/README.md`。它按读者的问题路由，而不是复制各页面的内容；目标仓库已有兼容地图时优先发现并遵循。

Discovery is deterministic and read-only:

1. read an explicit documentation-map pointer in active `AGENTS.md`, `CLAUDE.md` or the root README;
2. when that pointer resolves, use its target as the map;
3. otherwise use an existing `docs/README.md`;
4. when exactly one compatible map candidate is found, present it as the proposed map;
5. when candidates conflict or no map exists, report the ambiguity or greenfield state and ask the Human to confirm a proposal before writing.

The skill never creates a second map merely because a compatible map uses a different path or name.

推荐的阅读入口顺序是：根级领域语言 → 方法 → 产品需求 → 架构/设计 → 团队约定 → 质量与参考 → ADR → 活跃过程材料。

根级 `ZJ-CONTEXT.md` 是领域语言入口，`ZJ-CONTEXT-MAP.md` 是多上下文入口。两者继续留在仓库根目录；`docs/README.md` 只把它们登记为 docs 体系外的入口，不将其迁入 `docs/`。

### Categories and lifecycle

| Path | Lifecycle | Primary question / boundary |
| --- | --- | --- |
| `docs/methods/` | Long-lived | What repeatable method should this codebase use? |
| `docs/prds/` | Long-lived | What product problem, outcome and user value matter? |
| `docs/architecture/` | Long-lived | What is the current technical, business or product architecture? Names use `ta-*`, `ba-*`, and `pa-*` prefixes. |
| `docs/agreements/` | Long-lived | What team or Human–Agent agreements govern collaboration? |
| `docs/designs/` | Long-lived | Why and how does this bounded design idea work? |
| `docs/testing/` | Long-lived | What quality strategy, test boundaries and evidence standards apply? |
| `docs/benchmarks/` | Long-lived | What stable benchmark definition, measurement method or confirmed interpretation applies? |
| `docs/references/` | Long-lived / external reference | What enduring external reference, runbook or integration knowledge is relevant? |
| `docs/zj-adr/` | Long-lived decision history | What accepted hard-to-reverse decision explains an intentional boundary or trade-off? |
| `docs/plans/` | Process | What is the current plan, roadmap, wayfinder map, focus or execution decision context? |
| `docs/zj-retros/` | Process | What did one completed work session reveal before its durable value is extracted? |
| Target-defined fixture documentation | Long-lived supporting documentation | What behavior, purpose and maintenance boundary does a fixture establish? It may live beside its fixture; the map records its path rather than prescribing a directory. |

The map may recognise additional target-repository categories. It must identify their lifecycle and question rather than treating an unfamiliar directory as an error.

### Authority model

Navigation order is not a global truth hierarchy. Each document category and page declares the bounded question it owns. For example, `agreements/` owns collaboration rules; `architecture/` owns current architecture; a PRD owns the product problem; and an accepted ADR retains decision rationale without duplicating the current architecture page.

If two pages make incompatible normative claims about the same question, the validator reports a Human-review signal. It does not pick a winner, silently remove prose or infer that newer text is authoritative.

### Page contract

New or normalised pages use a small mechanical header plus readable Markdown:

```yaml
---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.<stable-slug>
---
```

`doc-kind` is one of `method`, `prd`, `architecture-map`, `architecture-overview`, `architecture-layers`, `architecture-subsystem`, `architecture-flow`, `architecture-cross-cutting`, `agreement`, `design`, `testing`, `benchmark`, `reference`, `adr`, `plan`, `retro`, or `fixture-documentation`. `authority` is one of `primary`, `supporting`, `historical`, `process`, or `external`; only `primary` pages require an `authority-id`.

The document map maps every `authority-id` to exactly one primary page and names the question it answers. This gives the validator a deterministic duplicate-ownership seam without asking it to infer semantic equivalence from prose.

Every long-lived primary page has `Question`, `Scope`, `Boundaries`, `Source map` and `Related authority` sections. Architecture pages additionally satisfy their view contract: subsystem pages name responsibility, owned state, interface and failure behavior; flow pages name trigger, sequence, state/effects, failure/exit behavior and observable evidence; cross-cutting pages own shared rules; the architecture map contains routing entries rather than duplicate explanation. Existing compatible documents are not rewritten merely to acquire frontmatter; a migration proposal reports the missing contract elements.

Source maps point to observable evidence such as code, tests, fixtures, accepted ADRs or external references. Every claim remains labelled as target architecture, implemented behavior, inference or explicit unknown as appropriate.

## Skill Topology

### New skills in `skills/codebase-docs/`

#### `zj-docs-ontology`

The Human-invoked overall governance entry point. It performs one explicit governance task in these stages:

```text
discover → classify → governance proposal → Human confirmation
        → scoped execution → validation → pending-synthesis / pending-deletion report
```

It supports the same workflow for greenfield and existing repositories:

- discover the document map, root context entry, Agent rules, ADR layout, existing docs categories and evidence surfaces;
- propose a minimal map and lazy category creation when the repository lacks a docs system;
- classify material as long-lived authority, external reference/runbook, fixture documentation, process material or separate evidence surface;
- produce a migration plan before making mutations;
- detect broken navigation, stale indexes, duplicate authority claims and prohibited process/status content in long-lived pages;
- when a Human asks for a full governance pass, selectively orchestrate `zj-domain-modeling`, `zj-docs-architecture`, `zj-debrief` and `zj-neat-freak` without absorbing their specialist workflows.

It does not prescribe a universal evidence directory, manufacture a second docs taxonomy in a compatible repository, or treat a plan lifecycle event as permission to govern or delete.

#### `zj-docs-architecture`

Owns the architecture-handbook layer, formerly proposed as `zj-architecture-docs`. It discovers the target documentation contract, maintains a single architecture map and creates pages lazily across five complementary views:

- system overview;
- layers and allowed dependencies;
- subsystem ownership;
- end-to-end flows;
- cross-cutting concerns.

It routes readers by question, names a unique owner for each durable rule, validates source-map targets and keeps target architecture, implemented behavior, inference and unknowns distinct. It delegates undefined terms to `zj-domain-modeling` and hard-to-reverse trade-offs to `zj-grill-with-docs` / ADR work.

### Existing skills moved to `skills/codebase-docs/`

These commands retain their established names; the bucket expresses their shared codebase-documentation capability:

- `zj-domain-modeling`
- `zj-grill-with-docs`
- `zj-debrief`
- `zj-neat-freak`
- `zj-wayfinder`
- `zj-roadmap-driven`

`zj-debrief` writes process material. Its reusable conclusions are deliberately extracted into a long-lived authority by a subsequent governance task; retro records are not permanent history by default.

### Repository configuration skill

Hard-rename `zj-agents-init` to `zj-repo-init` and retain it in `skills/engineering/`. Its actual responsibility is repository collaboration setup: issue tracker, triage labels and concise Agent-rule entry points. It delegates docs-map and domain-document establishment to `zj-docs-ontology`.

When it detects missing documentation-system setup, `zj-repo-init` provides the explicit `/zj-docs-ontology` pointer and explains what that next Human-invoked task will establish. It never invokes that skill, creates a docs map or performs a migration implicitly.

Its durable Human–Agent workflow details migrate from `docs/zj-agents/` to:

```text
docs/agreements/agent-workflow/
  issue-tracker.md
  triage-labels.md
  domain-docs.md
```

`AGENTS.md` or `CLAUDE.md` remains the immediate Agent rule surface and links to these agreements rather than duplicating them.

### Retirement

Remove `zj-initiative-registry`. It is a temporary transitional skill that has become an information-maintenance liability. The implementation must remove its skill directory, packaging metadata, README/install-list entries, in-skill and repository references, historical PRD/roadmap artifacts, and glossary entries.

The sole current root-level `skills-inputs/` template moves into the owning skill's `references/` directory. ZAgentic no longer uses root `skills-inputs/` as generic cross-project material storage.

## Process-material Lifecycle

Process documents strengthen a long-running Human–Agent collaboration: they preserve dynamic planning context, execution observability, intervention points, focus and decisions while the work is active. Their lifecycle is:

```text
process material → extract durable value → audit authoritative docs
                 → deletion proposal → Human confirmation → deletion
```

`zj-debrief` and `zj-neat-freak` remain orthogonal capabilities in this loop. Neither becomes an automatic event handler. `zj-docs-ontology` may compose them only in a Human-requested governance task.

## Migration Contract

Migration is always two-stage:

1. **Read-only proposal.** Inventory every relevant document; classify it; identify existing conventions and authority conflicts; list proposed `git mv` operations, broken links to repair, content requiring human synthesis and deletion candidates.
2. **Confirmed execution.** After Human confirmation, preserve document meaning by default while applying scoped moves, link repairs and map updates. Rewriting content, merging authorities and deleting process material are separately named actions and require the applicable confirmation.

The skill must preserve Git history through `git mv` where a tracked move is approved. A greenfield setup is simply the same contract with no prior material: propose the smallest useful map and directories, then create only the approved items.

## Evidence and Shared Knowledge Boundary

Code, tests, fixtures, runtime traces, research packages and evaluation outputs are evidence surfaces outside the long-lived docs taxonomy. `zj-docs-ontology` discovers and registers their boundary when they already exist, but makes no assumption about their directory names or storage policy.

The current `skills-outputs/` contains project-specific, non-atomic research and report artifacts. It is not a ZAgentic product surface. This version may inventory it and describe a future migration proposal, but must not move or delete it.

Producing reusable cross-project knowledge from such artifacts is a separate future Initiative: a local knowledge-refinement workflow would transform source packages into provenance-linked knowledge units and publish them for GitHub consumption. Selecting Semantica, OpenWiki or another producer, defining that unit schema, choosing a publication repository and migrating historical output are out of scope here. The attempted primary-source comparison must be rerun with a fresh sealed evidence ledger before a tool-specific decision.

## Metrics and experiments

The baseline is four recognised public skill buckets and a documentation system without a cross-category validator. Unit: pass/fail per fixture, migration-proposal action and repository-layout check. Method: run the relevant skill validators against self-contained fixtures and a read-only ZAgentic dogfood scan.

Target: every valid fixture exits successfully; every invalid fixture reports the expected stable diagnostic; one `authority-id` maps to exactly one primary page; and a scan emits no mutation before Human confirmation. Regression signal: a new bucket fails recursive plugin validation, a validator reads excluded process/evidence content, or a proposed migration changes a target before confirmation.

## Rollout, recovery, and lifecycle

### Delivery order

1. **Foundation:** create the `codebase-docs` bucket; move the agreed existing skills; hard-rename `zj-repo-init`; migrate Agent workflow agreements; retire `zj-initiative-registry`; move the current shared skill input into its owning skill; update recursive plugin discovery, all bucket indexes, top-level README, installer list and references.
2. **Architecture contract:** implement `zj-docs-architecture` discovery, map and initial page contract (Issue #20), then multi-view maintenance (#21), validator (#22) and fixtures/contributor guidance (#23).
3. **Documentation-system governance:** implement `zj-docs-ontology` over the proven architecture seam (Issue #24): full document map, classification, migration proposal, lifecycle orchestration and cross-category drift checks.
4. **Dogfood:** run the completed capability against ZAgentic in read-only mode. Human separately chooses whether to execute any resulting migration, cleanup or deletion proposal.

Every skill-touching change follows the repository 1-3-3-1 A-only checklist: recursive registration, safe Git through `./scripts/zj-git` or `env -u NODE_OPTIONS git`, and vocabulary sync in `ZJ-CONTEXT.md`.

### Packaging migration seam

Foundation explicitly updates `PUBLIC_BUCKETS` in `scripts/validate-zagentic-plugin.py` and `scripts/check-private-naming.sh`, the category list in `scripts/list-skills.sh`, their tests, `AGENTS.md` / `CLAUDE.md` bucket policy, bucket README indexes, the top-level README and regenerated `scripts/zagentic-skills-list`. The rename also updates every active command consumer and the path contract in `scripts/check-private-naming.sh` from `docs/zj-agents/` to `docs/agreements/agent-workflow/`; append-only retros and explicit migration history may retain the old name as historical text.

### Recovery

Each implementation slice is independently validated before the next begins. Pause rollout when a packaging validator rejects the new bucket, a migration proposal contains an unresolved authority conflict, or a planned deletion has not received Human confirmation. Rollback a failed slice by reverting its scoped Git change; never recover by deleting an unreviewed target document or process artifact.

## Principle considerations

### Performance

The validator performs bounded local reads of the map, the governed long-lived pages, their source-map targets and ADR metadata. It does not recurse through or preserve evidence packages merely to classify their boundary.

### Simplicity and accessibility

The map is Markdown and routes by reader question. Human confirmation gates only mutation and deletion; discovery and proposal remain inspectable and usable in ordinary repository tooling.

### Security and privacy

Source maps expose only repository-relative paths or existing external references. The skills must not copy credentials, raw ledgers, runtime traces or other sensitive evidence into durable documentation, validation logs or migration proposals.

## Testing and validation

Validation distinguishes mechanical failures from Human-review signals.

Mechanical checks cover map reachability, links, stable naming, page shape, `authority-id` uniqueness, source-map target existence, required architecture-page contract fields and accepted/superseded ADR references. Human-review signals cover likely duplicate normative rules, ambiguous authority and unsupported implications.

The architecture validator may read the selected map, governed architecture pages, accepted ADR metadata and the local targets explicitly named by their source maps. It may inspect process/evidence locations only by map entry and path existence; it must not read or retain plans, roadmaps, raw evaluation records, research ledgers, runtime traces or fixture payloads. Tests prove this minimum-read boundary.

The suite includes three layers:

1. self-contained valid and invalid fixtures for a greenfield docs system, existing docs, missing categories, broken links, source-map drift, duplicate authority, process content presented as durable fact, unaccepted ADR use and explicit unknowns;
2. a fixed ZWorkbench-style ontology/wiki fixture with glossary, architecture map, ADRs, code and tests as distinct observable surfaces;
3. a ZAgentic dogfood run: first a read-only governance/migration proposal, then changes only after Human confirmation.

Architecture coverage additionally includes minimal and multi-subsystem handbooks, shared cross-cutting rules, module moves, multiple flows sharing one rule, and ADR acceptance/supersession.

## Open decisions

| Question | Evidence needed | Owner | Due/exit condition |
| --- | --- | --- | --- |
| Which local tool and publication contract should refine project-specific research packages into reusable shared knowledge? | A fresh, sealed primary-source comparison and a local producer trial. | Human | A separate Initiative approves a tool, knowledge-unit schema and publication repository. |

## Review record

The initial review found five blocking specification gaps: static public-bucket registries, global-index removal order, an unverifiable authority contract, missing validator read boundaries and an implicit `zj-repo-init` delegation. This revision resolves them with explicit seams and acceptance gates. Non-blocking follow-up remains the separate shared-knowledge Initiative.

## Acceptance Criteria

- [ ] `skills/codebase-docs/` is a public recursively discoverable bucket with the agreed skills, local index and top-level README registration.
- [ ] `zj-docs-ontology` supports discovery, greenfield proposal, legacy migration proposal, explicit Human confirmation, scoped validation and process-material lifecycle reporting without prescribing evidence storage.
- [ ] `zj-docs-architecture` meets the discovery, five-view maintenance, validator and fixture contracts represented by Issues #20–#23.
- [ ] The default map and document contracts support the declared categories while preserving a target repository's compatible taxonomy and root context entry points.
- [ ] `zj-repo-init` replaces every active `zj-agents-init` reference and delegates document-system setup rather than owning a competing docs layout.
- [ ] `zj-initiative-registry`, its active references and its obsolete ZAgentic documents are removed according to the applicable global-roadmap maintenance rule.
- [ ] `zj-debrief` output is process material; durable content reaches one long-lived authority before a retro is proposed for deletion.
- [ ] Fixtures and the ZAgentic read-only dogfood proposal prove greenfield and migration behavior without changing any target repository before Human confirmation.
- [ ] Root `skills-inputs/` is removed after its sole reusable template is placed with its owning skill; `skills-outputs/` remains untouched pending the separate shared-knowledge Initiative.
