# ZAgentic 统一本体（Unified Ontology — T-Box）

> 本文件是 `docs/` 文档化系统的**概念主干（T-Box）**，与机器可读镜像
> [`ontology.schema.json`](./ontology.schema.json) 一一对应，并由
> 结构索引图实例（A-Box，由 [`extract.py`](./extract.py) 生成，作为
> [`validate.py`](./validate.py) 校验用的临时派生缓存）与
> [`validate.py`](./validate.py)（推理 + 约束校验）落地。

`docs/` 不是一堆零散 Markdown，而是 ZAgentic 代码库（技能集合）的**文档化系统**。
本体的作用是把"文档在讲什么、彼此怎么连、哪些是不可破的约束"显式化，从而满足四个工程目标：

| # | 目标 | 本体如何支撑 |
| --- | --- | --- |
| 1 | 语义统一，消除歧义 | 用固定**实体类型**与**属性**定义术语（如 `SkillBucket` vs `Skill` vs `DocPage` 不再混用）；`authority-id` 统一标识权威页，消除"哪篇才是真源"的歧义。**两模块共用一份词汇，不再有"本体"命名撞车**。 |
| 2 | 支持推理与约束校验 | `relations` 给出带域/范围/基数的 typed edges；`rules` 中 `checkable` 项由 `validate.py` 一次性执行 Module G + Module P 全部约束。 |
| 3 | 让 Agent/Human 更容易懂业务 | 实体与关联即"业务词汇表 + 关系网"；从 `Skill → SkillBucket → Platform` 与 `ArchitectureView → Design → ADR` 两条主线即可读懂全貌。 |
| 4 | 可复用、可设计、增删改保持新鲜度 | 结构索引图由 [`extract.py`](./extract.py) 从**活代码树**（`skills/`、`docs/`）重新生成；改动后重跑 `validate.py` 立即暴露漂移（如文档称"5+1 桶"而活树已 6+1）。 |

---

## 0. 本体的两层结构（关键：合二为一，部署二分）

本仓库曾有"两套 ontology"的混淆：通用技能 `zj-docs-ontology` 的"文档治理分类契约"
与产品领域的"知识本体"被当成两套独立体系。**实际上它们是同一份本体的两个 concern 模块**，
现统一为**一份**本体（单一 `ontology.schema.json` + 一张图 + 一个校验器），只在**部署**上二分：

| 模块 | 内容 | 归属 / 部署 | 源 |
| --- | --- | --- | --- |
| **Module G（治理层）** | 文档系统自身的分类/权威/生命周期契约：`doc-kind` 词表、`authority` 层级、`DocMap` 绑定契约、`MAP_*` 机械检查 | **可移植技能** `skills/codebase-docs/zj-docs-ontology`（装到任意代码库） | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md` |
| **Module P（产品域层）** | ZAgentic 作为技能集合产品的领域模型：平台/桶/技能/管道/校验器 | **ZAgentic 本地** `docs/ontology/`（抽取与校验实现） | 本文件 |

- **模型层合一**：`ontology.schema.json` 是所有实体/属性/关联/规则的单一真相源，每个实体与规则都标了 `module`。
- **部署层二分**：Module G 的实现（`docs_governance.py` + fixtures + 测试）随技能便携；Module P 的抽取/校验实现留在 `docs/ontology/`（ZAgentic 专属）。
- **单一校验器**：`docs/ontology/validate.py` 执行 Module P 的全部原生规则，并通过组合调用可移植技能脚本（`docs_governance.py --validate`）一次性覆盖 Module G 的 `MAP_*` 检查——对使用者而言就是"一个命令、一份报告"。
- **命名消歧**：不存在"domain-graph vs ontology"的兄弟关系了。`docs/ontology/` 就是这份统一本体的家；产品域只是它的 `Module P`，治理层是它的 `Module G`。

---

## 0.5 文档治理术语表（Governance Glossary）

> 蒸馏自四源 `docs/`（chromium / deepseek-harness / semantica / openai-codex）的最佳实践，于 PR #224 落地进
> `skills/codebase-docs/zj-docs-ontology` 治理层。下表是统一本体（T-Box）现在承载的 **Module G 词汇**——
> 它们与 Module P 的产品域词（`Platform` / `SkillBucket` / `Skill` …）共用一份词汇、无命名撞车。
> 定义性真相源在技能侧 reference，不在本文件：本表只做索引与一行释义。

| 术语 | 一行释义 | 归属层 | 定义真相源 |
| --- | --- | --- | --- |
| `one-home` | 一条规则/解释在文档系统中只有一个权威位置；其它提及一律链接过去。复制是契约问题（会漂移），不是风格问题。 | G | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#one-home-per-fact` |
| `tier` | 每个 `doc-kind` 的放置描述由两半组成：`Job`（装什么）+ `Does NOT belong there`（拒绝什么）；拒绝的那半才是防漂移的关键。 | G | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#one-home-per-fact` + `kind-templates.md` |
| `kind-template` | 每个 `doc-kind` 的放置契约：`Job` / `Does NOT belong there` / `Must-write sections` / `Page form` / `Focused check`；kinds 表与词汇 1:1 对应。 | G | `skills/codebase-docs/zj-docs-ontology/references/kind-templates.md` |
| `tutorial-vs-reference` | 页面落笔前声明两种形态之一：tutorial（有序路径、单目标）或 reference（当前行为查表面、完整扁平）；混合会互相掩盖。 | G | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#page-form-tutorial-or-reference` + `kind-templates.md` 的 `Page form` 列 |
| `retirement` / `tombstone` | 页面分四阶段退役：Retire（降为 historical）→ Tombstone（留短页指新址，避免断链）→ Drain（改指 inbound 链接）→ Propose+confirm 删除；tombstone 是「留破页」与「断全部链接」之间的第三选项。 | G | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#retirement` |
| `freshness` | 页面是否仍匹配其所映射的源——**声明为 architecture 层 `SOURCE_*` 的关注点**；治理契约只管存在哪些页、各页拥有什么，不实现新鲜度度量。 | G → P 边界 | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#page-content-contract` |
| `slop` | 9 类肉眼可辨的文档腐化（duplicate-rule / history-leak / status-annotation / hand-copied-restatement / reasoning-aside / rationale-repeat / paragraph-wall / emphasis-inflation / spec-speak），配 Detect/Fix/Scope。**审计清单不是门禁**：不加诊断码、不改退出码、不被 `--validate` 运行。 | G | `skills/codebase-docs/zj-docs-ontology/references/doc-slop-checklist.md` |
| `generated-region` | 由生成器维护的块（目录列表、API surface、派生索引），在页内标记为 generated、**绝不手改**；修订回到生成器输入或标记区外的散文。 | G | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#generated-regions` |
| `budget` | （未采用）页面大小预算 / 新鲜度评分 / 孤儿评分等健康度计量——目标仓无 manifest、无统一 source-map 时间戳，分数是编造的；作为能力缺口（E16）挂起，落 `## Rejected defaults`。 | G（缺口） | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md#rejected-defaults` |

> 术语范围守界：deepseek-harness 的「反隐喻」建议（禁 `gate` / `vocabulary` / `surface`）被拒，因这三者是本仓承重词，改名会破坏所有引用它们的契约；见治理契约 `## Rejected defaults`。`budget` 未落为契约项，与 E16（缺引擎 + 触碰 portability boundary）同因，仅作能力缺口追踪。

---

## 1. 实体（Entities）

实体按其归属模块与性质分列。完整字段表见 [`ontology.schema.json`](./ontology.schema.json#entities)。

### Module P — 产品域实体（code-domain，ZAgentic 本地）
| 实体 | 定义 | 示例实例 | 源位置 |
| --- | --- | --- | --- |
| `Platform` | ZAgentic 技能发布的 Agent 平台 | `claude` / `codex` / `workbuddy` | `docs/architecture/ta-zagentic-overview.md` |
| `SkillBucket` | 公共或个人技能分组目录 | `engineering` / `ui` / `personal` | `skills/<bucket>/`、`personal/` |
| `Skill` | 单个技能（SKILL.md + 辅助） | `zj-guide`、`zj-tdd` | `skills/<bucket>/<skill>/SKILL.md` <!-- # docs-ref-allow: `<bucket>`/`<skill>` 为通配占位符，非具体路径 --> |
| `Pipeline` | 安装/校验/治理流程 | install-and-validate、docs-governance | `docs/architecture/ta-zagentic-pipelines.md` |
| `Validator` | 检查脚本 | `validate-zagentic-plugin.py`、`docs/ontology/validate.py` | `scripts/` |

### Module G — 文档制品实体（doc-artifact，随治理技能可移植）
| 实体 | 定义 | 示例实例 | 源位置 |
| --- | --- | --- | --- |
| `DocMap` | 文档地图本身（`docs/README.md`）；把 `authority-id` 绑定到各页，自身为索引不持有 primary id | `docs/README.md` | `docs/README.md` |
| `DocPage` | docs/ 下任意文档（doc-map 除外），按 `doc-kind` 分角色 | 任意 md | `docs/**` |
| `ArchitectureView` | 架构手册中回答单一有界问题的主视图（authority: primary） | `ta-zagentic-layers` | `docs/architecture/ta-*.md` |
| `Design` | 设计权威页（规范/契约/决策） | `zj-roadmap-concurrency-model` | `docs/designs/*.md` |
| `ADR` | 已接受的不易逆转决策（历史权威） | `0001`…`0007` | `docs/zj-adr/` |
| `Agreement` | 方法论单一事实源（SSOT） | `open-source-capability-fit` | `docs/agreements/` |
| `CapabilitySpec` | 产品/能力边界规格 | `codebase-docs-capability` | `docs/prds/` |
| `Contract` | ui-agent-skills 内机器可读契约/清单/账本等 | `adapter-boundary-v1` | `skills/ui/zj-ui-core/contracts/` |
| `EvidenceSurface` | 临时证据面（已被治理移除） | `research/`、`skills-outputs/` | `docs/README.md` |

---

## 2. 属性（Attributes）

属性是实体的结构化字段。关键消歧属性：

- **`SkillBucket.kind`** ∈ {`public`, `personal`} —— 决定是否被插件发现/根 README 注册。
- **`Skill.bucket`** —— 强制且唯一（`belongsTo` 基数 exactly-one），杜绝"技能归属不清"。
- **`DocPage.doc_kind`** ∈ {`method`, `prd`, `architecture-map`, `architecture-overview`, `architecture-layers`, `architecture-flow`, `architecture-subsystem`, `architecture-cross-cutting`, `agreement`, `design`, `testing`, `benchmark`, `reference`, `adr`, `plan`, `retro`, `fixture-documentation`, `doc-map`} —— 固定文档语义角色。
- **`DocPage.authority`** ∈ {`primary`, `supporting`, `historical`, `process`, `external`} —— 文档权威层级。
- **`DocPage.authority_id`** —— 仅 primary 页（架构视图/设计/协议）拥有；全局唯一，是推理与校验的稳定锚点；`DocMap` 与 `ADR` 不拥有。
- **`ADR.status`** ∈ {`accepted`, `proposed`, `superseded`}。
- **`Contract.immutable`** —— 黄金夹具不可变，删即炸 CI。

---

## 3. 关联（Relations）

关联是带**域（domain）/范围（range）/基数（cardinality）**的类型化边，是推理的基础。每条都标了归属模块。

| 关联 | 模块 | 域 → 范围 | 基数 | 含义 |
| --- | --- | --- | --- | --- |
| `docMapBinds` | G | `DocMap` → `DocPage` | exactly-one-per-id | 地图把每个 authority-id 绑到恰好一页（**同一 id 绑多页 = `MAP_AUTHORITY_CONFLICT` 机械失败**） |
| `classifies` | G | `DocPage` → `string` | exactly-one | 文档由 doc_kind 分类 |
| `routesTo` | G | `ArchitectureView` → `DocPage` | many | 视图路由不重述 |
| `references` | G | `Design` → `ADR` | many | 设计引用 ADR 为史据 |
| `governs` | G | `Design` → `SkillBucket` | many | 设计约束桶行为 |
| `conformsTo` | G | `Skill` → `Contract` | many | ui 技能符合契约 |
| `constrains` | G | `CapabilitySpec` → `Pipeline` | many | 能力规格约束流程 |
| `supersedes` | G | `ADR` → `ADR` | many | ADR 间取代；**绝不指向现行架构** |
| `belongsTo` | P | `Skill` → `SkillBucket` | exactly-one | 技能必须且只能属于一个桶 |
| `installedTo` | P | `SkillBucket` → `Platform` | many | 公共桶安装到各平台 |
| `discoveredBy` | P | `Skill` → `Platform` | many | 平台递归扫描发现 |
| `validatedBy` | P | `Contract` → `Validator` | many | 契约被校验 |
| `uses` | P | `Pipeline` → `Validator` | many | 流程使用校验器 |

**推理示例**（由 `validate.py` 支持）：
- 从 `Skill.bucket` + `SkillBucket.installedTo` 可推出"某技能最终落到哪些平台目录"——无需逐篇文档查。
- 从 `ArchitectureView.routesTo` + `Design.references` 可推出"某架构决策背后的全部 ADR 链"，辅助影响面分析。
- 从 `DocMap.docMapBinds` 可机械推出"哪些 authority-id 被地图绑到了多页"，即治理契约的 `MAP_AUTHORITY_CONFLICT`。

---

## 4. 规则（Rules）

规则是不可破的约束/原则。**Module P（产品域）规则由 `validate.py` 原生执行**，下表完整列出；**Module G（治理层）规则由可移植技能 `zj-docs-ontology` 单一拥有**（见 `governance-contract.md`），本仓库通过 `validate.py` 组合调用复用，不在此重述其定义——避免双头漂移，`ontology.schema.json` 也只保留 P 规则 + 一条 G 引用。

### Module P — 产品域规则（本仓库原生执行）

| 规则 ID | 陈述 | 可校验 | 源 |
| --- | --- | --- | --- |
| `rule.one-owner-per-rule` | 一条持久规则恰有一个所有者文档；他页只链接不重述 | ✅ | architecture/README |
| `rule.bucket-reorg-is-adr-bearing` | 增删/重组桶必须有对应 ADR | ✅ | overview |
| `rule.personal-tree-excluded` | personal/ 排除出插件发现/根 README/桶索引 | ✅ | overview |
| `rule.every-skill-discoverable` | 公共技能须满足 frontmatter-schema 且已注册 | ✅ | skill-frontmatter-schema |
| `rule.no-dangling-reference` | 关联端点必解析到存在的实例 | ✅ | ontology |
| `rule.bucket-inventory-consistent` | 文档桶清单须与真实 skills/ 树一致（保鲜核心） | ✅ | overview vs skills/ |

---

## 5. 如何使用（工作流）

```bash
# 1) 从活代码树重新生成结构索引图（graph.json，仅作本地/临时派生缓存，gitignored）
python3 docs/ontology/extract.py > docs/ontology/graph.json

# 2) 推理 + 约束校验（一次覆盖 Module G + Module P；CI / pre-commit 钩子）
python3 docs/ontology/validate.py docs/ontology/graph.json
```

- **新增技能**：放进 `skills/<bucket>/<name>/`，重跑 extract→validate；若缺 frontmatter 或桶未注册，`rule.every-skill-discoverable` 会报红。
- **新增文档**：frontmatter 声明 `doc-kind`/`authority`/`authority-id`；doc-map 除外。若为主视图则 `rule.stable-authority-id` 强制。
- **改桶结构**：`rule.bucket-reorg-is-adr-bearing` 要求先有 ADR；否则 `rule.bucket-inventory-consistent` 抓出文档与活树不一致。
- **改 doc-map**：务必遵守 `rule.G1-docmap-binding`——每个 `authority-id` 用独立 bullet 绑定到恰好一页，不要把 id 放在含多个链接的块里（否则 `MAP_AUTHORITY_CONFLICT`）。
- **人工评审项**（契约/夹具）由 reviewer 依据 `docs/zj-adr/0008-ui-agent-skills-graduation-verdict.md`（原决策收敛页 `docs/designs/ui-agent-skills/README.md` 已删除，2026-10-24，结论迁入该 ADR）与 `golden-fixtures-spec` 核对，不进自动校验。

> 设计原则：**结构索引图是派生事实，活代码树是真相源**。本体（本文件）只在术语/约束本身演进时才改；日常增删改只动代码树 + 重跑两脚本，即可保持文档系统高新鲜度。Module G 的治理逻辑由可移植技能 `zj-docs-ontology` 单一拥有，本仓库通过组合调用复用，不重复实现（治理契约明确容忍技能间不跨目录 import 的"私有副本"模式）。
