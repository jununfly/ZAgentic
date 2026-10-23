---
doc-kind: doc-map
---

# ZAgentic documentation map

> **本仓库文档化系统以【统一本体 + 知识图谱】驱动**（见 [`ontology/ONTOLOGY.md`](ontology/ONTOLOGY.md)）。
> 概念主干（实体/属性/关联/规则，含 Module G 治理层 + Module P 产品域层）在
> [`ontology/ONTOLOGY.md`](ontology/ONTOLOGY.md)；机器可读本体在
> [`ontology/ontology.schema.json`](ontology/ontology.schema.json)；知识图谱与约束校验在
> [`ontology/validate.py`](ontology/validate.py)（一次覆盖 Module G 的 `MAP_*` 与 Module P 全部规则）。
> 本文档地图是**按实体类型组织的导航层**，不重述各页内容。

本地图区分长生命周期权威、过程材料与证据面；导航顺序不确立全局真值优先。每个 `authority-id`
用独立条目绑定到恰好一页（治理契约 `rule.G1-docmap-binding`）。

## Start here

| 问题 | 入口 | 边界 |
| --- | --- | --- |
| 文档化系统的概念主干是什么？ | [`docs/ontology/`](ontology/ONTOLOGY.md) | 实体/属性/关联/规则 + 推理校验 + 保鲜工作流 |
| ZAgentic 用什么词汇？ | [ZJ-CONTEXT.md](../ZJ-CONTEXT.md) | 根级外部文档入口；术语表拥有词汇 |
| 该用哪个技能/流程？ | [根 README](../README.md) 与 [`zj-guide`](../skills/engineering/zj-guide/SKILL.md) | 公共技能目录与路由，非架构权威 |
| Agent 在本仓库须怎么工作？ | [AGENTS.md](../AGENTS.md) | 即时仓库规则；协议按需惰性创建 |

## 文档实体清单（按本体类型）

下面每一类对应本体中的一种 `DocPage` 子类型（`ArchitectureView` / `Design` / `ADR` /
`Agreement` / `CapabilitySpec` / `Contract` / `DocMap`）。地图把每个 `authority-id` 绑到一页。

### ArchitectureView（架构手册主视图，authority: primary）
- [architecture/README.md](architecture/README.md) — 当前架构是什么、哪页答哪问？; authority-id: `architecture.map.zagentic`
- [architecture/ta-zagentic-overview.md](architecture/ta-zagentic-overview.md) — ZAgentic 是什么/不是什么？; authority-id: `architecture.overview.zagentic`
- [architecture/ta-zagentic-layers.md](architecture/ta-zagentic-layers.md) — 层间允许/禁止哪些依赖？; authority-id: `architecture.layers.zagentic`
- [architecture/ta-zagentic-pipelines.md](architecture/ta-zagentic-pipelines.md) — 安装/校验/治理流程端到端？; authority-id: `architecture.flow.install-and-docs-governance`
- [architecture/ta-skill-bucket-boundary.md](architecture/ta-skill-bucket-boundary.md) — 单一共享桶纪律是什么？; authority-id: `architecture.cross-cutting.bucket-discipline`
- [architecture/ta-skill-bucket-engineering.md](architecture/ta-skill-bucket-engineering.md) — engineering 桶拥有什么？; authority-id: `architecture.subsystem.bucket.engineering`
- [architecture/ta-skill-bucket-codebase-docs.md](architecture/ta-skill-bucket-codebase-docs.md) — codebase-docs 桶拥有什么？; authority-id: `architecture.subsystem.bucket.codebase-docs`
- [architecture/ta-skill-bucket-productivity.md](architecture/ta-skill-bucket-productivity.md) — productivity 桶拥有什么？; authority-id: `architecture.subsystem.bucket.productivity`
- [architecture/ta-skill-bucket-misc.md](architecture/ta-skill-bucket-misc.md) — misc 桶拥有什么？; authority-id: `architecture.subsystem.bucket.misc`
- [architecture/ta-skill-bucket-research.md](architecture/ta-skill-bucket-research.md) — research 桶拥有什么？; authority-id: `architecture.subsystem.bucket.research`
- [architecture/ta-skill-bucket-ui.md](architecture/ta-skill-bucket-ui.md) — ui 桶拥有什么？（2026-10-23 新增，见 ADR 0006）; authority-id: `architecture.subsystem.bucket.ui`
- [architecture/ta-zagentic-personal-tree.md](architecture/ta-zagentic-personal-tree.md) — personal 树拥有什么？; authority-id: `architecture.subsystem.personal-tree`

> ⚠️ **保鲜提示**：架构视图的桶清单由 ontology/validate.py 自动核对活树 `skills/`。当前活树含 `ui/` 公共桶（11 技能），`ta-zagentic-overview.md` 已同步为 6+1 模型 + ADR 0006（见 ontology/README.md）。

### Design（设计权威，authority: primary）
- [designs/zj-cross-stage-skills.md](designs/zj-cross-stage-skills.md) — 跨阶段检查点模型; authority-id: `design.cross-stage-checkpoints`
- [designs/zj-skill-frontmatter-schema.md](designs/zj-skill-frontmatter-schema.md) — 技能 frontmatter schema; authority-id: `design.skill-frontmatter-schema`
- [designs/zj-wayfinder-roadmap-dual-mode.md](designs/zj-wayfinder-roadmap-dual-mode.md) — wayfinder/roadmap carrier seam; authority-id: `design.wayfinder-roadmap-carrier-seam`
- [designs/zj-roadmap-concurrency-model.md](designs/zj-roadmap-concurrency-model.md) — roadmap 并发模型; authority-id: `design.roadmap-concurrency-model`
- [designs/zj-roadmap-execution-graph.md](designs/zj-roadmap-execution-graph.md) — roadmap 执行图; authority-id: `design.roadmap-execution-graph`
- [designs/zj-discuss/product.md](designs/zj-discuss/product.md) — zj-discuss 产品模型; authority-id: `design.zj-discuss-product`
- [designs/zj-discuss/architecture.md](designs/zj-discuss/architecture.md) — zj-discuss 架构; authority-id: `design.zj-discuss-architecture`
- [designs/zj-discuss/design.md](designs/zj-discuss/design.md) — zj-discuss 设计; authority-id: `design.zj-discuss-spec`
- [designs/zj-composer-plan-product-form.md](designs/zj-composer-plan-product-form.md) — composer plan/product form; authority-id: `design.composer-plan-product-form`
- [designs/zj-skill-runtime-closure.md](designs/zj-skill-runtime-closure.md) — skill 运行期闭包自包含（源仓 docs 不得运行时依赖、SSOT 不迁单 skill）; authority-id: `design.skill-runtime-closure`

### Contract（ui-agent-skills 子系统机器可读契约/清单/账本等）
机器可读契约：`skills/ui/zj-ui-core/contracts/`（随 skill 安装，closure 合规）。
决策收敛（毕业裁定 CONDITIONAL_ADOPTION）：ADR 0008 — `zj-adr/0008-ui-agent-skills-graduation-verdict.md`（原枢纽页 `designs/ui-agent-skills/README.md` 已于 2026-10-24 删除）。
子契约（含 `adapter-boundary-v1`、`canonical-schema`、`resolver-contract`、`hard-gates`、`verification-receipt`、`fixture-manifest`、`skill-capability-manifest` 等）详见 `skills/ui/zj-ui-core/contracts/`；完整实例见知识图谱。

### ADR（已接受的不易逆转决策，authority: historical）
ADR 是历史权威，**不取代**现行架构或规则，也不拥有 `authority-id`。
- [0001](zj-adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md) — 哪些技能必须要求 `/zj-repo-init` 配置？
- [0002](zj-adr/0002-stage-skill-pair-key-decisions.md) — 一次跨仓 skill-pair 如何处理/命名/归档？
- [0003](zj-adr/0003-khazix-wave-absorb-key-decisions.md) — 整波吸收第三方技能的规则？
- [0004](zj-adr/0004-research-report-improvement-scope.md) — research-skills 重架构的范围？
- [0005](zj-adr/0005-composer-authority-and-plan-contract.md) — Composer 的权威与 Plan 契约？
- [0006](zj-adr/0006-ui-public-bucket-addition.md) — 新增 `ui` 公共桶（6+1 模型）？
- [0007](zj-adr/0007-unified-ontology-module-g-and-p.md) — zj-docs-ontology 扩展为统一本体（Module G + Module P，部署二分）？
- [0008](zj-adr/0008-ui-agent-skills-graduation-verdict.md) — ui-agent-skills 毕业裁定（CONDITIONAL_ADOPTION）与治理页退役？

### Agreement（方法论 SSOT，authority: primary）
- [agreements/open-source-capability-fit-decision-model.md](agreements/open-source-capability-fit-decision-model.md) — 开源能力契合决策模型; authority-id: `agreement.open-source-capability-fit-decision-model`

### CapabilitySpec（产品/能力边界，authority: supporting）
- [prds/codebase-docs-capability.md](prds/codebase-docs-capability.md) — 单代码库文档治理技能的能力边界；当前技能行为仍为准

## 过程材料（ProcessMaterial）
| 问题 | 位置 | 生命周期 |
| --- | --- | --- |
| 已完成会话揭示了什么？ | `docs/zj-retros/`（由 `zj-debrief` 惰性创建） | 待持久抽取、权威审计、显式确认删除 |
| 哪些跨仓工单已就绪？ | [.scratch/knowledge-compounding-slice1/](../.scratch/knowledge-compounding-slice1/) | 该 roadmap 关闭前为本地执行源 |

## 证据面（EvidenceSurface）
`research/` 与 `skills-outputs/` 曾是个人工作区的临时容器，已于 2026-10-22 治理移除，不进入持久文档生命周期。ui-agent-skills 证据包（SYNTHESIS / CROSS-RUN-TABLE 等）未长期保留，结论已纳入 ADR 0008（原决策收敛页 `docs/designs/ui-agent-skills/README.md` 已于 2026-10-24 删除；更早的 `DECISIONS-RISKS.md` 已于 2026-10-23 随规范层清理删除）。

## 惰性目录（Lazy categories）
仅在仓库有对应有界问题的文档时才创建：当前空目录为 `methods/`、`testing/`、`benchmarks/`、`references/`。创建时须在此声明生命周期、有界问题与权威边界。新架构页遵循 `zj-docs-architecture` 视图契约。

## 关联速查（推理用）
- `Skill —belongsTo→ SkillBucket —installedTo→ Platform`
- `ArchitectureView —routesTo→ Design/ADR/CapabilitySpec`（只路由不重述）
- `Design —references→ ADR`（ADR 为史据，非现行权威）
- `Contract —validatedBy→ Validator`；`Pipeline —uses→ Validator`；`CapabilitySpec —constrains→ Pipeline`
- `DocMap —docMapBinds(authority-id)→ DocPage`（每 id 恰绑一页，否则 `MAP_AUTHORITY_CONFLICT`）

完整关联与实例由 [`ontology/extract.py`](ontology/extract.py) 从活树生成，由 [`ontology/validate.py`](ontology/validate.py) 校验（一次覆盖 Module G + Module P）。
