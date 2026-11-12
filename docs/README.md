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

> **保鲜提示**：架构视图的桶清单由 `ontology/validate.py` 自动核对活树 `skills/`；桶计数以 `ta-zagentic-overview.md` 为唯一真相源，其余页面只链接、不复述。

### Design（设计权威，authority: primary）
- [designs/zj-cross-stage-skills.md](designs/zj-cross-stage-skills.md) — 跨阶段检查点模型; authority-id: `design.cross-stage-checkpoints`
- [designs/zj-skill-frontmatter-schema.md](designs/zj-skill-frontmatter-schema.md) — 技能 frontmatter schema; authority-id: `design.skill-frontmatter-schema`
- [designs/zj-wayfinder-roadmap-dual-mode.md](designs/zj-wayfinder-roadmap-dual-mode.md) — wayfinder/roadmap carrier seam; authority-id: `design.wayfinder-roadmap-carrier-seam`
- [designs/zj-roadmap-concurrency-model.md](designs/zj-roadmap-concurrency-model.md) — roadmap 并发模型; authority-id: `design.roadmap-concurrency-model`
- [designs/zj-roadmap-execution-graph.md](designs/zj-roadmap-execution-graph.md) — roadmap 执行图; authority-id: `design.roadmap-execution-graph`
- [designs/zj-roadmap-reconciliation.md](designs/zj-roadmap-reconciliation.md) — roadmap reconciliation 与原子 ChangeSet 层（设计决策/替代方案/不变式/记号决策）; authority-id: `design.roadmap-reconciliation`
- [designs/zj-discuss/product.md](designs/zj-discuss/product.md) — zj-discuss 产品模型; authority-id: `design.zj-discuss-product`
- [designs/zj-discuss/architecture.md](designs/zj-discuss/architecture.md) — zj-discuss 架构; authority-id: `design.zj-discuss-architecture`
- [designs/zj-discuss/design.md](designs/zj-discuss/design.md) — zj-discuss 设计; authority-id: `design.zj-discuss-spec`
- [designs/zj-composer-plan-product-form.md](designs/zj-composer-plan-product-form.md) — composer plan/product form; authority-id: `design.composer-plan-product-form`
- [designs/zj-skill-runtime-closure.md](designs/zj-skill-runtime-closure.md) — skill 运行期闭包自包含（源仓 docs 不得运行时依赖、SSOT 不迁单 skill）; authority-id: `design.skill-runtime-closure`
- [designs/zj-docs-convention-distillation-playbook.md](designs/zj-docs-convention-distillation-playbook.md) — 跨仓文档规范蒸馏 playbook（不建 skill 的判决 + 五段法）; authority-id: `design.docs-convention-distillation`
- [designs/zj-roadmap-visual-review-product.md](designs/zj-roadmap-visual-review-product.md) — roadmap Human 视图产品设计方案（四场景锚定 + 同源多投影）; authority-id: `design.roadmap-visual-review-product`
- [designs/zj-roadmap-visual-review-technical.md](designs/zj-roadmap-visual-review-technical.md) — roadmap Human 视图技术设计方案（由确定性脚本从机器可读 SoT 生成）; authority-id: `design.roadmap-visual-review-technical`

### Contract（ui-agent-skills 子系统机器可读契约/清单/账本等）
机器可读契约：`skills/ui/zj-ui-core/contracts/`（随 skill 安装，closure 合规）。
决策收敛（毕业裁定 CONDITIONAL_ADOPTION）：ADR 0008 — `zj-adr/0008-ui-agent-skills-graduation-verdict.md`。
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
- [0009](zj-adr/0009-ui-agent-skills-discussion-retirement.md) — 退役 `discussions/ui-agent-skills-complete-solution/` 讨论记录，将其风险矩阵与毕业闸门沉淀为 `zj-ui-core` 契约（guarantee-boundary / graduation-gates），使 skill 与 discussions/ 解耦（supersede 0008 Decision 3）
- [0010](zj-adr/0010-local-file-persistence-convention.md) — 会本地落盘的技能统一用相对路径 + 隔离目录（升华 #169）？
- [0011](zj-adr/0011-docs-governance-quality-contract-and-rejected-defaults.md) — 文档质量契约落在治理层而非运行时、被拒默认值显式记录？
- [0012](zj-adr/0012-scene-anchored-cross-project-alignment.md) — 跨项目对齐单位为何从节点语义等价改为固定场景集（场景锚定）？

### Agreement（方法论 SSOT，authority: primary）
- [agreements/open-source-capability-fit-decision-model.md](agreements/open-source-capability-fit-decision-model.md) — 开源能力契合决策模型; authority-id: `agreement.open-source-capability-fit-decision-model`
- [agreements/product-project-graphical-cross-comparison-model.md](agreements/product-project-graphical-cross-comparison-model.md) — 产品项目图式横比模型（以固定场景集对齐多项目结构差异）; authority-id: `agreement.product-project-graphical-cross-comparison-model`

### CapabilitySpec（产品/能力边界，authority: supporting）
- [prds/codebase-docs-capability.md](prds/codebase-docs-capability.md) — 单代码库文档治理技能的能力边界；当前技能行为仍为准

## 过程材料（ProcessMaterial）
| 问题 | 位置 | 生命周期 |
| --- | --- | --- |
| 已完成会话揭示了什么？ | `docs/zj-retros/`（由 `zj-debrief` 惰性创建） | 待持久抽取、权威审计、显式确认删除 |
| 哪些跨仓工单已就绪？ | `.scratch/knowledge-compounding-slice1/`（已退役，见 `6c5781b`） | 该 roadmap 关闭前为本地执行源 |
| 活跃执行计划的生命周期？ | 按 ADR 0010，`docs/plans/` 下页面为临时过程材料，持久文档不引用；由治理 pass 逐项审阅 | 关联 issue 全部关闭并完成抽取后才进入退役 |

## 证据面（EvidenceSurface）
`skills-outputs/` 是 skill 运行产出的临时证据缓存，按 ADR 0010 永不入库（gitignored）；现行输出落在 gitignored 的 `tmp/skills-outputs/`。

三个不可变 golden 夹具归各自 skill 所有：`controlled-quality-v1` → `skills/research/zj-research/tests/golden/`、`code-research-quality-v1` → `skills/research/zj-code-research/tests/golden/`、`multi-device-agent-context` → `skills/research/zj-tech-research-report/tests/golden/`。它们由 `research-compiler-contract.yml` 与契约测试钉死，须永不静默删除。ui-agent-skills 证据包的结论已纳入 ADR 0008。

## 惰性目录（Lazy categories）
仅在仓库有对应有界问题的文档时才创建：当前空目录为 `methods/`、`testing/`、`benchmarks/`、`references/`。创建时须在此声明生命周期、有界问题与权威边界。新架构页遵循 `zj-docs-architecture` 视图契约。

## 关联速查（推理用）
- `Skill —belongsTo→ SkillBucket —installedTo→ Platform`
- `ArchitectureView —routesTo→ Design/ADR/CapabilitySpec`（只路由不重述）
- `Design —references→ ADR`（ADR 为史据，非现行权威）
- `Contract —validatedBy→ Validator`；`Pipeline —uses→ Validator`；`CapabilitySpec —constrains→ Pipeline`
- `DocMap —docMapBinds(authority-id)→ DocPage`（每 id 恰绑一页，否则 `MAP_AUTHORITY_CONFLICT`）

完整关联与实例由 [`ontology/extract.py`](ontology/extract.py) 从活树生成，由 [`ontology/validate.py`](ontology/validate.py) 校验（一次覆盖 Module G + Module P）。

## 审计例外（doc-slop）

页面健康度审计的命中是提议项，不是待删清单。以下三类命中经 2026-11-08 治理 pass
裁定为合法例外，内容不得静默改写；回归守卫见 `tests/test_docs_residual_slop.py`。
`doc-slop-checklist` 仍是审计清单，不因本登记变成运行时门禁。

| 命中类别 | 对象 | 理由 |
| --- | --- | --- |
| spec-speak | agreement 的规范性模态句（`docs/agreements/` 内的「不得 / 必须 / 一律」） | 规范性契约：模态词承载权责与后果，降级为建议语气会改变 primary SSOT 语义 |
| status-annotation | ADR 历史台账（`docs/zj-adr/` 内的 ✅ 迁移记录） | 史据：记录当时落地项，是 ADR 的证据价值，不是实现进度标注 |
| status-annotation | PRD 验收清单（`docs/prds/` 内的 `- [ ]`） | 验收标准：未勾选项是可复核的接受条件，不是待办进度 |
