---
doc-kind: design
authority: primary
authority-id: design.docs-ontology-skill
---

# zj-docs-ontology 设计文档（与实现对齐）

> 本页描述 `skills/codebase-docs/zj-docs-ontology/` **实际实现的设计**，按四层职责骨架组织：
> **健康检查 → 治理 → 生成知识图谱 → 遵照 Ontology 设计**。所有断言对应
> `scripts/docs_governance.py`、`scripts/validate_ontology_model.py`、`scripts/check_gate.py`
> 与 `references/*.json` 的真实行为。它**不是**操作指南；调用步骤见 skill 自身 `SKILL.md`（后者亦以
> L1–L4 同名列出，可双向导航）。

## 1. 四层：既是分层架构，也是 Human 治理流程

skill 治理「一个代码库的文档系统」。四层有**两种读法**：静态看是**分层架构**（§1.1），动态看是触发
词「做下文档治理」时推荐的**闭环流程**（§1.2）。二者**共享同一批概念，但分属两个进程**：L1–L3 由
`docs_governance.py` 一次 `--proposal`/`--validate` 产出，L4 由**独立的** `validate_ontology_model.py`
产出——**没有任何单条命令端到端跑完四层**。流程每一步本质是「调用对应层的只读检测 → 产出治理建议 →
Human 确认执行」，跨进程衔接由 Human/Agent 完成，工具不自动跑完整环、不自动回灌。

### 1.1 架构视图（数据依赖）

后层在实现上**复用前层的产物**，不是并列分类，而是有数据依赖的流水线：

```
L1 健康检查  ──观察──►  L2 治理  ──产出受治 map──►  L3 知识图谱  ──覆盖集──►  L4 Ontology 设计
(读只读诊断)        (生命周期/绑定/账本)        (map 的图派生视图)      (实体模型拆解/重组校验)
```

| 层 | 职责 | 实现入口 | 关键产物 | 归属 |
|---|---|---|---|---|
| **L1 健康检查** | 文档系统当前是否自洽（发现 vs 现实） | `discover()` / `map_links()`（链接半） / `scan_unmapped_pages()` / `duplicate_fact_scan()` / `scan_page_vocabulary()` | `read_paths`、链接清单、各类 signal/ERROR | Module G |
| **L2 治理** | 绑定 / 生命周期 / 退役 / 改名 / 执行账本，全部 Human 确认门控 | `map_links()` 绑定半 / `scan_retirement()` / `head_roster()`+`detect_pending_moves()`+`scan_head_disappearance()` / `emit_checklist()`+`inspect_checklist()` | `retirement`、`pending_moves`、`checklist`、`mutations:[]` | Module G |
| **L3 生成知识图谱** | 把 map 当图节点声明面，派生机器可读快照（**map 的只读投影，非可推理 KG/TBox**） | `map_graph()` / `graph_snapshot()` / `dangling_edges()` / `orphan_pages()` | `graph_snapshot`（nodes/edges/constraints） | Module G |
| **L4 遵照 Ontology 设计** | 文档系统 → entity/attribute/relation/rule，拆解/重组校验 | `validate_ontology_model.py`（`import docs_governance` 复用 L3 `map_graph`、L1 `discover`） | 模型实例 + per-page receipt + coverage | Module D |

实现上的依赖分两种，**只有第一种是代码级可核验的**：

- **import 级（唯一真实调用依赖）**：`validate_ontology_model.py:34` 通过 `sys.path` 反向复用
  `docs_governance` 的 `discover()`（`validate_ontology_model.py:219`）与 `map_graph()`（`:222`）——
  L4 的「每个 map 覆盖页须有 receipt」覆盖不变式直接消费 L3 解析出的节点集。方向是 **L4→L3/L1**，
  **不是** L1→L2→L3→L4 正向流水；`docs_governance.py` 从不 import 模型校验器。
- **概念级（共享同一 map 源，非调用依赖）**：L1 `map_links()` 与 L3 `map_graph()` 各自独立解析**同一份
  map 文件**、彼此不调用——「L3 建立在 L2 受治后的 map 上」只是「读同一个声明面」，不是 import 链。

三个脚本互不导入架构 skill。

### 1.2 流程视图（「做下文档治理」的闭环）

一次「做下文档治理」由 Human/Agent 按四层顺序串起：**①②③ 来自一次 `docs_governance.py --validate`
报告，④ 来自独立进程 `validate_ontology_model.py`**——`--validate` 永不含 `CONTENT_UNCOVERED`/
`ANCHOR_RECEIPT_DRIFT`/`ONTOLOGY_*`。脚本侧永远是只读检测 + 发提议（`mutations: []`）；
enrich / refresh / 建页 / 删页都是 **Human 确认后才执行的写动作**（用 `git mv`、改写、tombstone）。
④ 检出的不符由 Human 再发起新一轮 ①② 治理建议（**跨进程人工串联，工具不自动回灌**），故这是环、不是一次性直线：

```
      ┌─── 回灌：Human 据 ④ 结果再发起 ①②（非工具自动，④ 是另一进程） ───┐
            ▼                                                                        │
① 健康检查 ──► ② 治理建议 ──► ③ 维护知识图谱 ──► ④ 是否符合 Ontology 设计 ──► ⑤ 治理建议
  (L1)          (L2)            (L3)                 (L4)                      (L2)
detect        propose+confirm  enrich/refresh/      conformance-check        propose+confirm
              腐化/过期→删除    create 长期文档       覆盖缺口/漂移/孤立节点
```

| 步 | 层 | 工具产出（只读；注明发源进程） | Human 确认后的执行动作 |
|---|---|---|---|
| ① 健康检查 | L1 | 链接断 `MAP_LINK_BROKEN`、未映射 `UNMAPPED_PAGE`、重复事实 `FACT_NO_SINGLE_HOME`、平行本体嫌疑 `PARALLEL_ONTOLOGY_SUSPECTED`、词汇越界 `PRESET_VOCABULARY_VIOLATION` | 修链接 / 登记 / 重分类（**不删**） |
| ② 治理建议 | L2 | `proposed_actions`、退役 `deletion-candidate`、改名对账 `RENAME_AWAITING_CONFIRMATION`/`UNDECLARED_RETIREMENT` | 改名 / 退役 / **删除已排空候选**（见红线） |
| ③ 维护知识图谱 | L3 | `graph_snapshot`、悬空边 `MAP_RELATION_DANGLING`、孤立节点 `ORPHAN_PAGE` | enrich/refresh 已有长期页 / 建新的 / 声明边；**腐化页→转②退役** |
| ④ 是否符合 Ontology 设计 | L4（**`validate_ontology_model.py`，非 `--validate`**） | 覆盖缺口 `CONTENT_UNCOVERED`、锚点漂移 `ANCHOR_RECEIPT_DRIFT`、结构 ERROR `ONTOLOGY_*` | 补 receipt / 修模型 / 回 ⑤ |
| ⑤ 治理建议（闭环） | L2 | ④ 的不符转成的 register/enrich/retire 提议 | 同 ②，再回 ① 复核 |

**删除红线（贯穿②③，对齐实现）**：「腐化 / 过期」是**语义判断**，工具从不据 signal 删页——
`UNMAPPED_PAGE`、`ORPHAN_PAGE`、`CONTENT_UNCOVERED` 的 remedy 都明令「register / 声明边 / 补 receipt，
绝不据此删页」。删除只能走 L2 的生命周期：声明 `retired-to:` 退役 → 入站 `RETIRE_DRAIN_INCOMPLETE`
排空 → `deletion-candidate`（入站为 0 且目标存在）→ Human 确认才删。即**腐化页先在 ②③ 被判为退役
候选，排空后进入删除**；③ 里发现的腐化长期文档是「转回 ② 的退役流程」，而非在 ③ 直接删。

### 1.3 贯穿两种读法的设计不变式

1. **工具发事实，不做裁决**——`ERROR` 只用于「声明与现实不符」的机械故障；凡「证据不外在
   执行 Agent」的自证一律 `signal`（exit 0），由消费方决定是否升级为门禁。
2. **运行期闭包（Ruling 1）**——运行时只读自身安装目录内的 sibling 文件，绝不依赖 CWD、目标仓根
   或源仓 `docs/`。
3. **单一声明源**——同一事实只允许一个 declaration source（词汇、Step 5 witness、graph snapshot、
   required 字段契约各只有一个真相源）。

### 1.4 三轴正交定位（设计坐标，非实现新增）

一个文档/知识系统的形态可在三条**正交轴**上定位；本 skill 在每条轴的取值都由**已有实现**决定，
共同解释「为何它是轻量受控档、既不滑向开放抽取也不升格形式本体」（是 §12「取舍」的上位框架）：

| 轴 | 两端 | 本 skill 取值 | 实现锚点 |
|---|---|---|---|
| **知识何时被综合** | 查询时 ↔ 治理时 | 治理时（人发起 pass 时离线综合），无查询期计算 | `report()` 仅在 `--proposal`/`--validate` 跑 |
| **表示严格度** | 开放抽取 ↔ 形式本体 | 轻量受控：17 `doc-kind` + 5 `authority` 闭集 + 四段式 schema | `scan_page_vocabulary()`、`ontology-meta-schema.json`（边界见 §5） |
| **谁为结论签字** | 无责任人 ↔ 具名+溯源 | 具名确认 + 哈希账本 + 显式退役链 | `confirmation_id=sha256(...)`、`retired-to:`→drain→deletion-candidate |

三轴取值把本 skill 钉在「**轻量本体约束 + 责任链**」一档：开放抽取（无签字、语义漂移）与形式本体
（建模成本、越 §11 能力边界）两端都不取。

## 2. L1 · 健康检查（read-only 观察）

### 2.1 发现 doc-map（`discover()`，优先级固定）

```
读 AGENTS.md / CLAUDE.md / README.md 里的 `docs-map:` 指针 (POINTER_RE)
  ├ 去重后恰 1 个 → map_origin=explicit-pointer
  ├ >1 个 → MAP_AMBIGUOUS（返回 None，绝不猜）
  └ 0 个 → docs/README.md 存在? default
            → docs/**/*-map.md 候选：1 个 candidate / >1 个 MAP_AMBIGUOUS / 0 个 greenfield
```

`MAP_POINTER_BROKEN`：显式指针指向的 md 不存在。greenfield 时 `has_error()` 直接返回 `False`
（全新仓没有可失败的 map）。

### 2.2 链接完整性（`map_links()` 的观察半）

map 文本按「行首 `- `」切 entry 块，对每块用 `LINK_RE` 找 markdown 链接（`[label]` 紧跟圆括号目标）；目标不存在 →
`MAP_LINK_BROKEN`（`MAP_` 前缀 = ERROR）。绑定检测（同 `authority-id` → 多页）属 L2，见 §3.1。

### 2.3 覆盖完整性（`scan_unmapped_pages()`，2026-11-20 基线 pre-flight）

提案清单是磁盘派生的，但其余检查全部 map-anchored——于是 `docs/<长生命周期分类>/` 下无 map 入口的
长生命周期页对它们全都不可见，validate 仍可能 exit 0。本检查 diff「preset 长生命周期目录磁盘文件」
与「现有 map link targets」补上这个洞：命中 → `UNMAPPED_PAGE`（signal——登记/重分类/退役，
**绝不据此删页**；只 markdown 页、只 map 覆盖，过程材料/证据面豁免，目标自定义分类是 Human 判断）。

### 2.4 一事实一家粗筛（`duplicate_fact_scan()`，issue #275 Fix 5）

两个**纯 signal** 表面，都是「声明缺失」类（L7，永不升级为 ERROR、不改 exit），且都是命名了
重复事实与所在页的**粗筛**、绝不给相似度百分比：

- `FACT_NO_SINGLE_HOME`：map 覆盖页间出现同一 normalized heading（`normalize_heading` 大小写/
  标点无关、`\w` 保留 CJK），且簇内无任何页声明 `authority: primary`。**ADR 模板标题豁免**
  （否则任意两-ADR 仓都会永久报冲突）。
- `PARALLEL_ONTOLOGY_SUSPECTED`：`docs/` 下 map 未覆盖、有 git 活动证据（untracked/modified）的页，
  标题与被覆盖标题池重叠（整标题相等或 ≥2 共享词）。无 git 仓则跳过；map 自身豁免。
  读取严格有界：只读覆盖页 + 活动候选；过程材料/证据面永不开。

### 2.5 封闭词汇合规（`scan_page_vocabulary()`，Ruling 1 case 2b）

读所有 living 页（跳过 map、证据面、过程面）front matter：`doc-kind`/`authority` 越出共享核心闭集、
`doc-kind` 无 preset `kinds` 行、或 `primary` 页声明 `authority-id` 数 ≠ 1 →
`PRESET_VOCABULARY_VIOLATION`（**ERROR**，声明与现实不符）。而「目标仓合法省略某些 preset 长生命
周期分类」是 `PRESET_DIVERGENCE`（signal，`scan_preset_divergence()`，绝不自动修）。

## 3. L2 · 治理（绑定 / 生命周期 / 改名 / 执行账本，Human 门控）

`report()` 的 `mutations` 永远为空——本层**只提议不写目标仓**；每个写动作都由 Human 显式确认。

### 3.1 authority↔page 1:1 绑定（`map_links()` 的绑定半）

**绑定检测放在 map 上**（契约把 binding 定义在 map），故永不打开被链页面：同一 `authority-id` 绑到
>1 页 → `MAP_AUTHORITY_CONFLICT`（`MAP_` 前缀 = ERROR）。绑定是事实，故冲突非零退出由人裁决；
页面内部 `authority`/`doc-kind` 声明合规由 `zj-docs-architecture`（page-declaration 层）负责，
**两层可对同一 id 各报一类缺陷**——刻意分离避免单点真相被两个工具争夺。

### 3.2 退役排空（`scan_retirement()`，governance-contract「Retirement」）

map 条目 `retired-to:` 声明退役，不读页 front matter 即可查三件事：目标须存在
（否则 `RETIRE_TARGET_MISSING`）、声明须命名到一页（否则 `RETIRE_DECLARATION_INCOMPLETE`）、
入站引用须在删除前**排空**。扫所有 living `.md` 收集 inbound；仍有入站 → `RETIRE_DRAIN_INCOMPLETE`
（`status: drain-in-progress`）；目标存在且入站为 0 → `deletion-candidate`。页面离开服务先退役并
tombstone（入站仍在期间），**删除是最后阶段、绝非常量**。三条 `RETIRE_*` 均 ERROR。

> **刻意设计**：退役→tombstone→排空→`deletion-candidate` 这条链，是对「撤回应做显式状态、
> 别无痕删」（僵尸口径）这一最佳实践的实现侧落点——它让「离开服务」是可审计的状态转移，而非
> 一次 git 删除，故腐化页始终先被**判为候选**、排空后才进入删除。

### 3.3 三层基线对账（issue #275 defect B）

`head_roster()` 跑 `git ls-tree -r --name-only HEAD`；无 HEAD 或 git 不可用返回 `None`
（**不做消失声明**）。据此分三态：

```
first_setup（roster 为 None/空） → baseline=not-applicable，bootstrap=preset，发 BASELINE_NOT_APPLICABLE（signal）
established HEAD                  → 检查 working tree 里消失的 tracked 路径，三层裁决：
   ① 出现在确认 proposal 的 `moves` → 豁免（Human 决定）
   ② detect_pending_moves()（git status/diff 的 git-native 重命名，未确认）
        → RENAME_AWAITING_CONFIRMATION（signal，无需 tombstone 桩）
   ③ 无重命名证据 → UNDECLARED_RETIREMENT（ERROR，fail-closed）
```

`detect_pending_moves()` 同时读 `git status --porcelain=v1 -z`（staged `git mv`）与
`git diff --name-status -M HEAD`（unstaged），按「工作树存在性」归一 from/to——字段顺序差异不会翻转
语义。map 里的 `retired-to:` 是另一合法豁免。

### 3.4 checklist witness 机制（Rulings 2+4，P0 ruling 3）

把「确认过的 proposal」变成不可伪造的执行账本：

- `emit_checklist()`（`--proposal --topic --emit-checklist`）写 `<out-base>/<topic>/`：
  `proposal.json` + `checklist.json`。**`confirmation_id = sha256(canonical(proposal_json))`**，
  由工具计算——`--confirm` 这类自证旗标被拒绝；它记录「确认的是哪份 proposal」，不保证 Human 诚实。
  步骤含固定 1–5（Step 5 `artifact` 是裸文件名 `architecture-validator.txt`，单基准）+ 每条
  `proposed_action` 一个 `action-N` 步。
- `inspect_checklist()`（`--validate --topic`）是 Step 5 witness 的**唯一来源**；supplied 时
  CLI `--arch-witness/--arch-fingerprint` 被忽略（两源即漂移，issue #275 defect A）。校验：
  checklist 的 `confirmation_id` 不符 → `UNCONFIRMED_MUTATION`（ERROR）；Step 5 artifact 不存在 →
  `EXEC_STEP5_ARTIFACT_MISSING`（**ERROR，无论 status**，诚实 `skipped` 也暴露）；存在但指纹不符 →
  `EXEC_STEP5_FINGERPRINT_MISMATCH`（**signal，never-gate**，是 pass 内自证）；标 `done` 却无 artifact
  → `EXEC_CHECKLIST_STEP_UNBACKED`（ERROR）；proposal/checklist 皆缺 → `CONFIRMATION_BASELINE_LOST`
  （signal，不做清单声明）。
- 裸 `--validate`（无 `--topic`）：无法核对清单，发 `EXEC_CHECKLIST_NOT_DECLARED`（signal，
  platform-layer C disclosure）——绿色不证明完整 pass 跑过，留给 CI/步进门禁升级。
- `architecture_witness()` 兼容回退：只记一个文件的 sha256，**从不 import/调用架构 skill、
  从不开/解析该 artifact**。

### 3.5 对象声明 vs pass 主题（issue #275 Fix 1a）

旧词 `scope` 曾同时指「治理对象」和「pass 主题」，导致两者都无法核对。现拆成两字段：
`object_of_governance.source` 为 `derived`（默认 `docs`，`declared_by_default:true`）或 `declared`
（`--object` 给了仓根相对目录/声明文本）；声明解析不到存在目录时仍记录（`exists:false`）——工具报
事实，不替人猜更好的对象。`pass_topic` 与命名合法性（`valid_topic()`：小写连字符、无
date/sha/version/status，否则 main `INVALID_TOPIC` exit 2）是 checklist 的键。

## 4. L3 · 生成知识图谱（map 的图派生视图，issue #275 Fix 7）

`map_graph()` 把 map 当**本体声明面**解析：entry = 图节点（`role`/`authority-id` 为节点属性），
可选 `relations:` 子句声明 typed 边。**一条 entry 的认定 = 块首行带 markdown 链接**（Q7 回归：
prose/derived 文件里的链接是提及非节点）。关系词表是**封闭集**
`RELATION_TYPES = derived-from|supersedes|supports`（起步小，防 map 沦为无人维护的装饰）。
边 target 解析 id-first（命中某 entry 的 `authority-id`）再退化为仓相对路径——解析在整遍 entry
扫描后做，因为边可指向后面条目声明的 id。

`graph_snapshot()` 派生 `{schema_version: graph-snapshot/v1, nodes, edges, constraints}`，
**仅从 map 派生、绝不第二源**，供 AI 导航消费（顺 `supersedes` 找现行权威、`derived-from` 找来源）；
Human 渲染是消费方关切。

校验分两级：未知关系类型 `MAP_RELATION_TYPE_INVALID`、悬空边 `MAP_RELATION_DANGLING`（显式声明与
现实不符，均 `MAP_` ERROR）；非 primary 且无入边的 map 条目 `ORPHAN_PAGE`（signal——补救是声明边、
不是删页；未声明 role 的条目归架构层 `PAGE_ROLE_UNDECLARED`，fail-open）。

**边界（对齐实现）**：`graph_snapshot` 是从 map 单向派生的**只读导航投影**——`docs_governance.py:797`
的约束明写 `derived-only`。它**没有 TBox、没有推理机、不做语义蕴含**：消费者只能遍历邻接关系
（顺 `supersedes` 找现行权威、`derived-from` 找来源），**不能推导新事实**。此层「生成知识图谱」一词
仅指「派生图结构」，不是可推理知识图谱——这正是「有图≠能推理」的实现侧落点。

## 5. L4 · 遵照 Ontology 设计（Module D：拆解 / 重组）

skill 拥有 **meta-schema**（`references/ontology-meta-schema.json`，元层）；每个仓库实例化**自己的
模型**（具体 entity 类型与词表是仓库关切，从不随 skill 发布）。`validate_ontology_model.py <repo> --model <path>` 校验一个实例 against meta-schema。**required 字段从 meta-schema 文件读，绝不二次
硬编码**：classes `entity`(entities)/`attribute`(attributes)/`relation`(relations)/`rule`(rules)
各自的 `collection` 与 `required`；`page_receipt` required `[path, elements]`。

方法论上，本层要求把整个文档系统当作有界对象：decompose 每页内容到 model elements → 每页写
per-page receipt（page→elements）→ recompose 长生命周期页使其声明可追溯到 model。结构 = 事实 →
ERROR；覆盖 = 导航缺口 → signal：

- `schema_version` 须 `ontology-model/v1`，否则 `ONTOLOGY_MODEL_SCHEMA_UNSUPPORTED`。
- id 跨类唯一 → `ONTOLOGY_ID_DUPLICATE`；attribute.owner / relation.from/to 须是 entity id →
  `ONTOLOGY_ATTRIBUTE_ORPHAN` / `ONTOLOGY_RELATION_ENDPOINT_MISSING`；rule.traces 须解析到存在页 →
  `ONTOLOGY_RULE_TRACE_MISSING`；receipt 字段/页/引用元素须合法 → `ONTOLOGY_PAGE_RECEIPT_BROKEN`。
- **覆盖**（消费 L3 节点集）：每个 map 覆盖页须有 receipt，缺 → `CONTENT_UNCOVERED`
  （signal——声明 receipt，不删页）。
- **锚点镜像**：页 front matter `model-elements: [...]`（`ANCHOR_RE`）若**声明**则须与 receipt 集合
  双向相等（顺序无关），否则 `ANCHOR_RECEIPT_DRIFT`（signal——receipt 是真相源，修镜像）。缺锚点被
  容忍（receipt 可先于锚点铺开）；「不静默删锚点」守卫在消费仓的根回归套件。

**这不是形式本体（对齐实现）**：本层的「ontology」是自定义 JSON 四段式（entity/attribute/relation/
rule）。`validate_ontology_model.py` 只做**闭世界的形状校验**——id 唯一、attribute owner / relation
endpoint 存在、rule trace 解析、receipt 合法（`:126`–`:216`），等价于 SHACL 式「入库必须满足」约束，
**不含 OWL/RDFS 的开放世界语义，也没有推理机**：它判「声明是否自洽」，永不推断新事实。把文档系统
建模得更快、更稳靠这套轻量 schema 即可，无需升格为形式本体（meta 与实例共用一套词表故无命名冲突）。

## 6. capability boundary（issue #275 Fix 1b，2026-11-20 经 Module D 合并修订）

`capability_boundary_block()` 声明两个**覆盖层**（governance = L1+L2+L3；ontology design = L4）与
一个**残余未覆盖类**：声明对象不是文档系统的本体（数据库 schema、运行期数据模型）——交领域专用
能力。原 `CAPABILITY_NOT_COVERED` 启发式信号被**撤回**：文档系统拆解/重组本就是此 skill 的职责，
标它「未覆盖」是假的；误定域防御改由显式 `--object` 声明承担。

## 7. 运行时闭合与配置面（贯穿四层）

`docs_governance.py` 两类词汇源**都从安装目录 sibling 读取、缺源即不发该断言（绝不硬编码回退）**：

- `shared_vocabulary()`：用 `GEN_BLOCK_RE` 从 `SKILL.md` 的 `<!-- BASE_RULES_START --> …` 生成块读
  `core.doc-kind.values` 与 `core.authority.values`（由外部 generator 从
  `docs/skill-conventions/skill-conventions.json` 生成，跨 skill 共享核心）。
- `load_preset()`：用 `__file__.parents[1]/references/canonical-preset.json` 读
  `categories.long_lived`/`process` 与 `kinds`（17 个 doc-kind 行）；缺失/损坏返回 `None` →
  `PRESET_UNAVAILABLE`（signal）且**不做任何分类声明**。

`DEFAULT_PRESET`、`DEFAULT_OUT`、`DEFAULT_META_SCHEMA`、`DEFAULT_RULES` 全由 `__file__` 相对解析；
`resolve_out_base()` 把输出区锚定到被治理**仓根**（绝不锚定 CLI 启动目录）。

## 8. `report()` 顶层产物（按层标注）

`report()` 一次产出 `proposal` dict，`--proposal`/`--validate` 共用之（`validate_links` 标志决定
是否展开只读校验扩展）。字段归属：

| 字段 | 来源 | 层 |
|---|---|---|
| `repository` / `mode:"read-only-proposal"` | — | 元 |
| `object_of_governance` / `pass_topic` | `resolve_object()` / `--topic` | L2 |
| `capability_boundary` | `capability_boundary_block()` | 元 |
| `map` / `map_origin` | `discover()` | L1 |
| `inventory` | `inventory()` | L1 |
| `canonical_preset` | `load_preset()` | 元 |
| `baseline` / `bootstrap` | `head_roster()` | L2 |
| `graph_snapshot` | `graph_snapshot()` | L3 |
| `map_links` | `map_links()` | L1/L2 |
| `duplicate_fact_scan` | `duplicate_fact_scan()` | L1 |
| `retirement` / `pending_moves` | `scan_retirement()` / `detect_pending_moves()` | L2 |
| `architecture_witness` / `checklist` | `inspect_checklist()` / `architecture_witness()` | L2 |
| `diagnostics` / `proposed_actions` / `mutations:[]` / `read_paths` | 各检查聚合 | 跨层 |

> 本表只列 `docs_governance.py` 的 `report()` 产物。**L4 的模型校验报告（含 `coverage`/`anchor_drift`
> 及 `CONTENT_UNCOVERED`/`ONTOLOGY_*` 诊断）由独立进程 `validate_ontology_model.py` 单独产出，不在此
> 报告内**——见 §1.2 的跨进程说明。

## 9. 退出码与门禁分层（消费侧）

- **`docs_governance.py` exit**：`has_error()`——`greenfield` 恒 `False`；否则任一诊断 `code` ∈
  显式 `ERROR_CODES`（`UNDECLARED_RETIREMENT`、`UNCONFIRMED_MUTATION`、`EXEC_STEP5_ARTIFACT_MISSING`、
  `EXEC_CHECKLIST_STEP_UNBACKED`、`PRESET_VOCABULARY_VIOLATION`）或以 `MAP_`/`RETIRE_` 前缀 → exit 1。
  前缀族是「白名单」而非前缀猜测：新增 MAP_/RETIRE_ 门禁不会因被遗忘而静默放行。`INVALID_TOPIC` → exit 2。
- **`validate_ontology_model.py` exit**：其自身 `ERROR_CODES` 命中 → 1。
- **`check_gate.py`（消费侧，issue #264 layer C）**：读 stdin 报告 + `gate-rules.json`，纯函数
  `decide()`。ERROR/error_prefixes 必拦；`escalatable_signals` 须 `--escalate CODE` 才拦；
  `never_gate_signals`（`PRESET_DIVERGENCE`、`EXEC_STEP5_FINGERPRINT_MISMATCH`）即便请求升级也**拒绝
  并报告**。`load_rules()` 还拒 `escalatable∩never-gate` 重叠。exit 0 pass / 1 fail / 2 坏输入。工具与
  门禁解耦：validator 只发事实，**每个仓库自己接线**（CI workflow 须无条件触发、解析 JSON 而非信 exit code）。

## 10. 诊断码全清单（按层 × 严重度）

| 层 | ERROR（exit 1） | signal（exit 0） |
|---|---|---|
| **L1 健康检查** | `MAP_POINTER_BROKEN` · `MAP_AMBIGUOUS` · `MAP_LINK_BROKEN` · `PRESET_VOCABULARY_VIOLATION` | `UNMAPPED_PAGE` · `FACT_NO_SINGLE_HOME` · `PARALLEL_ONTOLOGY_SUSPECTED` · `PRESET_DIVERGENCE` · `PRESET_UNAVAILABLE` |
| **L2 治理** | `MAP_AUTHORITY_CONFLICT` · `RETIRE_DECLARATION_INCOMPLETE` · `RETIRE_TARGET_MISSING` · `RETIRE_DRAIN_INCOMPLETE` · `UNDECLARED_RETIREMENT` · `UNCONFIRMED_MUTATION` · `EXEC_STEP5_ARTIFACT_MISSING` · `EXEC_CHECKLIST_STEP_UNBACKED` | `BASELINE_NOT_APPLICABLE` · `RENAME_AWAITING_CONFIRMATION` · `CONFIRMATION_BASELINE_LOST` · `EXEC_STEP5_FINGERPRINT_MISMATCH` · `EXEC_CHECKLIST_NOT_DECLARED` |
| **L3 知识图谱** | `MAP_RELATION_TYPE_INVALID` · `MAP_RELATION_DANGLING` | `ORPHAN_PAGE` |
| **L4 Ontology 设计** | `ONTOLOGY_MODEL_UNREADABLE` · `ONTOLOGY_MODEL_SCHEMA_UNSUPPORTED` · `ONTOLOGY_REQUIRED_FIELD_MISSING` · `ONTOLOGY_ID_DUPLICATE` · `ONTOLOGY_ATTRIBUTE_ORPHAN` · `ONTOLOGY_RELATION_ENDPOINT_MISSING` · `ONTOLOGY_RULE_TRACE_MISSING` · `ONTOLOGY_PAGE_RECEIPT_BROKEN` | `CONTENT_UNCOVERED` · `ANCHOR_RECEIPT_DRIFT` |

> `MAP_`/`RETIRE_` 前缀自动判 ERROR，故 L1/L2/L3 的 MAP_/RETIRE_ 码不依赖显式 `ERROR_CODES` 集合。
> `PRESET_VOCABULARY_VIOLATION` 是显式 ERROR；`PRESET_DIVERGENCE`/`PRESET_UNAVAILABLE` 是 signal。

## 11. 可移植性边界

skill 自带全部四层（`SKILL.md`、`references/`、`scripts/`），装到任意目标仓不变运行。它拥有
meta-schema（L4 元层——**自定义 JSON schema，非 OWL/RDF 形式本体**）与跨页词汇，但**具体模型实例**
（如 platform/bucket/skill/pipeline 等实体类型
及实例）是消费仓的，从不随 skill 发布；meta 与实例共用一套词表故无命名冲突。词汇/preset 的
「不硬编码、缺源即不声明」原则共同保证：portable，且在源仓（ZAgentic）外不泄漏任何源仓专有路径
（与 `zj-skill-runtime-closure` 闭包约定一致）。

## 12. 关键设计取舍（为何如此实现）

- **数据依赖单向、流程闭环**：代码级唯一真实依赖是 L4 `import` 复用 L3 `map_graph`、L1 `discover`；
  L1–L3 共享**同一份 map 源**而非各存一份真相，杜绝「第二个声明源」。流程上 ④（`validate_ontology_model.py`）
  的不符由 Human 再发起 ①②（`docs_governance.py`），跨进程人工串联成持续闭环——工具本身不自动跑完整环。
- **map 而非 page 作为绑定真相源**（L2）：`MAP_AUTHORITY_CONFLICT` 在 map 上检测，validator 不必打开
  被链页；page 内部声明合规是另一层（`zj-docs-architecture`）。
- **`confirmation_id` 由工具哈希**（L2）：拒绝「我确认了」式自证旗标；执行账本的信任根是 proposal
  内容的确定性哈希。
- **signal 默认放行 + 消费侧升级**（贯穿）：把「证据不外在执行者」的判断留给有上下文的 CI/步进门禁，
  工具永不越权裁定语义对错；never-gate 表防止自证类 signal 被误升级成虚假绿灯。
- **关系词表封闭、快照单源**（L3）：防 map 退化为不可靠装饰，防 graph 出现第二声明源。
- **required 字段读自 meta-schema**（L4）：契约只有一处定义，杜绝校验器与模式漂移。
- **ADR/模板标题豁免**（L1）：粗筛 signal 必须对模板复用免疫，否则任何真实仓都会被永久噪声淹没。

## 13. 有意不实现的边界（known gaps，勿静默加）

以下两项能力**在本 skill 边界内可论证、但刻意不落地**，记录以防未来误加（守不变式 1「工具发事实
不做裁决」与 §11 可移植边界）：

1. **`graph_snapshot` 边不携带 PROV-O 式责任属性**（谁在何时确认了某条 `supersedes`）。当前边只有
   `{from, type, to, via}`（`docs_governance.py:784–791`）；「谁确认」由 L2 的 `confirmation_id` 账本
   在 **pass 层**承担，不渗进每份图快照——否则快照就成了第二声明源，违反 §4 的 `derived-only` 约束。
2. **`rule.traces` 不叠加生效/失效时间做双时态**。traces 只是 repo 相对页路径（见 meta-schema
   `rule.traces`），校验器只判「trace 是否解析到存在的页」（`ONTOLOGY_RULE_TRACE_MISSING`），不记录
   「该规则何时为真」。原因：本 skill **无周期复审引擎**，且明确「not a publisher / no automatic
   closeout」；时效与 decay 属消费方或专门知识系统的职责，引入会把治理工具推向它拒绝的运行期裁决。

> 若要实现任一缺口，须先扩 `SKILL.md` 能力声明并重开 issue，**不得在校验器里静默加字段**。
