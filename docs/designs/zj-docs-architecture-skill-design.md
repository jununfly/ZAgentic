---
doc-kind: design
authority: primary
authority-id: design.docs-architecture-skill
---

# zj-docs-architecture 设计文档（定义驱动 · 设计领先于实现）

> **本文是「目标设计」，不是现状描述。** 权威基准是下方「定义（已锁定）」一节；其余各节从该定义
> 推导出 skill **应当如何工作**。当前 `validate_architecture_docs.py` 的实现**只是迁移基线**，集中在
> §9，那里是全文唯一带 `文件:行号` 现码锚点的地方。
>
> **标注约定**（每条断言必带其一，避免把设计当既成）：
> - `[现状]` 现有代码已实现，附 `validate_architecture_docs.py:NN` 锚点（仅出现在 §9 与「复用」处）。
> - `[目标]` 由定义推导、尚未落地，**无代码锚点**，引到定义节或契约文件而非源码行号。
> - `[新增]` 全新工件/能力（concept-map、formatter(A)、三面差分）。
> - `[未决]` 已识别但本轮不定的设计缺口。
>
> 它**不是**操作指南；调用步骤与工作流见 skill 自身 `SKILL.md`。

## 定义（已锁定 · target，未落地）

> 本节是**目标定义**，非现状。它锁定于一次设计讨论，作为后续"如何落地"的唯一裁判基准。

**本质**：zj-docs-architecture 是**架构三面一致性的求解器**。它由"拥有一个模型"来定义，而非由"校验一批文件"来定义——这是它区别于通用 doc-linter 的本质，也是它区别于 `zj-docs-ontology` 的本质。

**三面模型**（每个概念恰落三态之一）：

```
   A 代码（现实） ──formatter(A)──► B architecture-concept-map（权威对象/身份）
                                          │  判定重心：C ↔ B（方向性差分）
                                   C 架构内容文档（人写，住在 ontology 的 repo doc-map）
```

- **权威对象 B = `architecture-concept-map`**：带**专用命名前缀**、由 **formatter 纯从代码 A 派生**、对代码**封闭**（凡不在代码者不入 B）。它**本身是一篇文档**，但**不是索引**。① A↔B 由构造平凡真——故全部可判定内容收敛到 **C↔B**。
- **裁决 = 方向性差分，只报不裁因由**：
  | 概念状态 | 报告 | 是否债 |
  |---|---|---|
  | B∩C 同步 | 无偏 | — |
  | B \ C（文档落后于代码） | 「欠文档」 | 恒为债 |
  | C \ B（代码落后于文档） | 「文档跑在代码前 · 成因未定」 | **不判**——成因可能是 Human 先改文档再动代码，也可能是其它原因致债，**从 B/C 差分本身不可判定** |
  → 故 C \ B 一律**呈报方向、永不自动豁免**；把"补代码 / 改文档 / 留作 roadmap"的定性**外派**给 roadmap/grilling。守「发事实、不裁决」（`SKILL.md:48-50`）。target 文档不属本 skill 管辖。
- **机格式工件豁免**：B 因 formatter 由构造自洽，**排除在 ③ 人写文档规范校验外**（否则用 formatter 校验 formatter 的输出 = 循环）。③ 只作用于 C 中人写内容文档。

**文档三分类（按所有权，互斥）**：索引文档（repo doc-map，owner=ontology）｜架构内容文档（C，architecture 管内容）｜架构模型文档（B，architecture own）。

**边界（own / not-own）**：own 模型（B）及其对 A、C 的一致性判定；**不 own 索引**（文档的存在/归类/生命周期归 ontology）；不定义领域术语（domain-modeling）；不裁不可逆决策（ADR/grilling）；**不裁 C\B 的成因**。

**派生不变式**：① B 不可手改（手改即成第二声明源，真相在 formatter(A)）；② B 概念词汇可由现 `architecture-contract.md:85-104` 八条 maintenance-triggers 播种。

**与现状关系**：当前实现（见 §9）只覆盖 C 的**内部自洽③**（doc-kind/naming/小节/source-map/authority 形状）。① 一致性、② 债务发现、B 本体、`formatter(A)`、读代码能力**均尚未实现**。

## 1. 设计总览：三面、数据流与 skill 边界

`[目标]` 整个 skill 围绕三面（A/B/C）的求解组织，而非围绕"一个校验器"：

```
        ┌───────────────────────── zj-docs-architecture 的管辖 ─────────────────────────┐
代码 A ──│ formatter(A) ──► concept-map B ──┐                                            │
(仓内源) │        [新增]                     ├─► C↔B 方向性差分 ──► 一致性① + 债务②(signal) │
        │                                  │                                            │
文档 C ──│ 人写架构内容文档（住在 ontology map）──► ③ 内容规范校验(shape, 含 ERROR)         │
        └──────────────────────────────────┴────────────────────────────────────────────┘
                       ↑ 仅消费、不拥有：repo doc-map（ontology 的索引）
```

三条边界的硬约束 `[目标]`：

1. **不 own 索引**：本 skill 不创建/不改 repo doc-map，只从中识别"哪些是架构内容文档"（识别机制见 §7）；此处"消费" = **只读投影取数**（找 map 路径 + 按 map role 声明取切片作开页清单），**不含对 map 的结构判定**（链完整性/覆盖率/去重/kind 归类），后者归 ontology（详见 §7、§9）。
2. **A→B 单向**：B 只能由 `formatter(A)` 生成；任何进入 B 的概念必须在代码 A 可定位；A 不反向读 B 内容做语义裁决。
3. **判定收敛 C↔B**：因 A↔B 平凡真，本 skill 的实质工作全部是"人写 C 是否如实外化 B"。

> **两 map 之辨** `[目标]`：本 skill 同时面对两张 map——**repo doc-map**（owner=ontology，本 skill 只读投影消费，`docs_governance.py:657-660` 永不开页）与 **concept-map B**（owner=本 skill，`tacm-`，`formatter(A)` 派生，见 §2）。二者不可混同：消费前者是为定位要开页的人写内容文档 C，拥有后者是为外化代码 A 的概念模型。

## 2. 权威工件：architecture-concept-map（B） `[新增]`

B 是本 skill 的身份——**本 skill 自有**的 map 工件，区别于 §7 消费的 repo doc-map（owner=ontology，仅作定位 C 切片的只读投影输入，不被本 skill 拥有或结构校验）。其设计契约（全部 `[目标]`）：

- **命名**：专用前缀令牌定为 `tacm-`（architecture concept-map），**归入 `ta` 命名家族**（以 `ta` 为根，即 `ta/ba/pa` 同族）；`tacm` 作为完整令牌仍区别于纯内容前缀 `ta-/ba-/pa-`，保持"专用标识模型工件"的语义。`tacm-` 前缀族作为 **skill 私有扩展**，进 `SKILL.md` Shared Conventions `extensions`，**不进** 共享核心；authority-id 前缀**不**另立私有常量（切片判据是 map role 声明，见 §7）。
- **生成**：`formatter(A)` 确定性产出 → 幂等、可重生成；故 B 是"提交供评审的派生物"，**真相在 formatter(A)**。
- **不可手改不变式**：任何对 B 的人工编辑破坏幂等、把它变成第二声明源；CI 应以"重跑 formatter 比对"取代"评审 B 内容"。
- **对代码封闭（closed-world over code）**：B 只含代码可定位的概念；"文档里有、代码里没有"的概念**绝不进 B**（这正是 C\B 差分能成立的前提）。
- **schema 草图**（JSON，`[目标]`）：
  - `nodes`：concept（id、名称、类型 ∈ 八 maintenance-triggers 播种的概念词表、代码锚点 file:line 或符号定位符）。
  - `edges`：concept→concept 分解/组合关系（**节点是概念**，区别于 ontology L3 图"节点是文档"）。一条 `--part-of` 可列多个有效父（多条边，closed-world set 去重排序）；分解图须为 **DAG**——环由 `--consistency` 报 `CONCEPT_CYCLE`（signal，纯 B 结构自洽、不需 C，区别 `CONSIST_*` 的 B↔C，但随本命令 map 触发）；**跨 owner 成边有意不校验**（组合可合法跨归属，报之即裁决、违反「发事实不裁决」）。
  - **（PR-A 修正 D2）B 只含 `nodes`/`edges`，不落 `index`**：`concept→文档` 反向映射由 `--consistency` 的 anchor join 现求（formatter(A) 读不到文档，无法产 index）；join 以 C 页 `## Source map` 命中的代码文件匹配 `node.anchor`。**B ≠ repo doc-map**（B=概念图；repo doc-map=文档索引）。
- **概念词汇播种** `[目标]`：初版概念类型直接复用 `architecture-contract.md:85-104` 的八条 maintenance-triggers（Extension seam / Durable owner / Cross-process contract / Effect policy / Replay boundary / Lifecycle rule / Accepted ADR / Source-map target）——它们本就是"值得从代码抽出建模的东西"。**D1 已落地（PR-B）**：`--format-concepts` 扫代码 `@concept: <kind> <id>` 标记产 B（closed-world、`docs/` 排除）。**edges/owner 已落地（PR-B 续 / §10 收尾）**：`--part-of=<id>[,<id>]` 抽 concept→concept 边（端点非节点则 closed-world 丢弃），`--owner=<authority-id>` 存为 `node.owner`——它是代码声明的归属意图（A 面事实），**不是 D2 禁止的文档反向 index**，故不违反 D2。属性须按 `--anchor/--owner/--part-of` 固定顺序书写。

## 3. 内容文档 C 与技术规范校验（③，复用现机制）

③（架构文档符合技术标准/规范）是**唯一已大部分落地**的一面，作为三面求解的一个子检查保留。其机制 `[现状→目标复用]`：

- **五类互补视图 + 各自必写小节** `[现状]`：`VIEW_HEADINGS`（overview/layers/subsystem/flow/cross-cutting）`validate_architecture_docs.py:65-71`，共有小节 `:64`，过程小节黑名单 `:72`。`[目标]` 这套 shape 契约继续作为 C 的人写文档规范。
- **命名稳定性** `[现状]`：`naming_diagnostics` `:195-225`，规则来自内联 `naming-syntax-core`，附 `ta-/ba-/pa-` 前缀族 `:75`。`[目标]` 不变。
- **authority 声明 + source-map + ADR status** `[现状]`：`:337/:355-384`。`[目标]` 仅作用于"在架构切片内"的人写文档（切片判定见 §7）。
- **值域单一源、缺源 fail-loud** `[现状]`：`_load_inline_conventions :36-47`，缺块 `raise`。`[目标]` 这一"不硬编码兜底"原则继续成立，并延伸到 B 的概念词表（同样声明为私有扩展而非散落硬编码；authority-id 前缀不再作切片判据，见 §7）。

> B（机格式工件）**不受本节任何 shape 校验约束**（避免 formatter 校验 formatter 的循环，见定义）。

## 4. 三面一致性求解（①②，新增能力，signal-only） `[新增]`

这是定义带来的、当前**完全不存在**的能力。

- **输入**：B（§2）+ 架构切片内的人写文档 C（§3 已识别其 authority-id 与 kind）。
- **算法 = 逐概念方向性差分** `[目标]`，按定义只分三态：

  | 态 | 判据 | 产出码族 | 严重度 |
  |---|---|---|---|
  | B∩C | 概念在 B、且某 C 文档外化它 | — | — |
  | B \ C | 概念在 B、无任何 C 外化 | `CONSIST_UNDOC`（欠文档） | **signal** |
  | C \ B | C 声称某概念、B（即代码）无 | `CONSIST_ORPHAN_DOC_CLAIM`（文档跑在代码前，成因未定） | **signal** |

- **债务② = 可测偏离的聚合视图** `[目标]`：debt = B\C 全集 + C\B 全集（后者只计数/呈报、不裁成因）。无相似度、无百分比、无"该不该存在"的裁决。
- **永不升级为 ERROR 门禁** `[目标]`：一致性/债是语义判断，按"发事实不裁决"（`SKILL.md:48-50`）一律 signal/提议，由人或 roadmap skill 决定补码/改文/defer。
- **不裁 target** `[目标]`：target（意图、未实现）文档的概念本就不在 B → 落 C\B → 作为"文档跑在代码前"呈报；本 skill **不**判它"是前瞻还是陈旧"，也不因此判失败。

（已定=是）C\B 的"成因未定"**附带** echo 页上既有 `target/implemented/inference/unknown` 标签（`architecture-contract.md:110`），作**上下文而不作豁免**：标签只帮人或 roadmap 判读成因，绝不据此自动豁免或降级该 signal。

**落地态（PR-A + PR-B + §10 收尾）**：B 的 schema / 确定性渲染 / 幂等比对（`concept_map.py`）、**B\C 差分**（`--consistency` anchor join → `CONSIST_UNDOC`）、**C\B 差分**（D5 页侧 `concepts:` 声明 id-join → `CONSIST_ORPHAN_DOC_CLAIM`，status echo 不豁免）、**owner 校验**（代码 `node.owner` 声称的归属页未在 `concepts:` 外化该概念 → `CONSIST_OWNER_MISMATCH`，与 UNDOC/ORPHAN 正交）与 **formatter(A)**（D1 `--format-concepts` 扫代码 `@concept:` 标记，closed-world、`docs/` 排除，并抽 `--part-of` 概念边与 `--owner` 归属）均已落地。三向一律 signal、绝不影响 exit；采用 join 方案 Y（B\C 用 anchor-file、C\B 用 concept-id、owner 用 authority-id↔页声明，互不干扰，不回改 PR-A）。**edges 复杂语义（§10 收尾）**：多父（一条 `--part-of` 列多个有效父）已支持、环检测 `CONCEPT_CYCLE`（signal，B 内部 DAG 自洽、不需 C，但随 `--consistency` 的 map 触发）已落地；跨 owner 成边有意不报（组合可合法跨归属）。

## 5. 严重度模型与裁决立场

`[目标]` 两层严重度，互不混淆：

- **shape 层（③，继承 `[现状]`）**：机械"声明 vs 现实不符"→ `Diagnostic.signal` 标志决定 ERROR/signal（`validate_architecture_docs.py:83-88`），`exit = any(not signal)`（`:415`）。可继续作 ERROR 门禁。
- **consistency/debt 层（①②，`[新增]`）**：**永远 signal**，绝不进 ERROR 集，绝不影响 exit 码——它是审计面，不是门禁。
- **统一不变式**：重复/歧义/漂移一律以 signal 交人，从不自动选赢家（`SKILL.md:48-50`）。

## 6. own / not-own 边界

| 维度 | own | not-own（及归属） |
|---|---|---|
| 工件 | architecture-concept-map（B）、其概念词表、formatter(A) | repo doc-map 索引（ontology，architecture 只读投影消费、不含结构门禁）；领域术语（domain-modeling）；ADR/不可逆决策（grilling） |
| 判定 | C↔B 方向性差分、③ shape | C\B 成因裁决（roadmap）；map 结构判定：链完整性/覆盖率/去重/kind 归类（ontology） |
| 键 | 消费 `authority-id`（与 ontology/绑定同键，不自造 doc 标识） | 不另立文档命名/寻址体系 |

> **同键两面** `[目标]`：页侧 `AUTHORITY_MAP_BINDING`（own，`validate_architecture_docs.py:352-354`）与 map 侧 `MAP_AUTHORITY_CONFLICT`（not-own，`docs_governance.py:683-690`）针对同一条 id↔page 绑定契约，可对同一 id 各报一条互补缺陷（`skill-conventions.json:134-146` notes）。

## 7. 与 zj-docs-ontology 的接口（切片由 map role 声明界定）

两 skill 互不 import，唯一运行期衔接是 ontology 的 `architecture_witness()` 对架构产物记 sha256（非调用）。`[目标]` 接口面：

- **共享词汇单一源**：`doc-kind`/`authority`/命名语法来自 `skill-conventions.json → BASE_RULES` 内联块（`[现状]` `:36-47`）。`concept-map` 前缀 `tacm-` 仍是**私有扩展**、不进共享源；authority-id 前缀**不再**作 architecture 的切片判据（见下方「切片判据」条与 §9 Delta）。
- **authority-id 作为共享键**：authority-id 仍是与 ontology 对账的**共享键**（`MAP_AUTHORITY_CONFLICT`、`skill-conventions.json:131-147`），但**切片入口是 map entry 的 `role` 声明**（`validate_architecture_docs.py:251`，owner=ontology），**不是** authority-id 前缀——architecture 若按 id 根自判外人，等于行使索引归类权、违反 §6「不 own 索引」。
- **消费语义（docs-map 用法收缩）** `[目标]`：architecture 自带 `discover_map`（`validate_architecture_docs.py:129-158`）**保留**，但降级为「取 map 路径 + 按 map `role` 声明取切片作开页清单」，并据此调整 map 相关码：**(a) 入口**——greenfield 对齐 ontology（`docs_governance.py:651` 返回 `"greenfield"`、`has_error` 短路 `:1457-1459`），**不报 `MAP_MISSING`**（呼应 §8 `:149`）；**(b) 让渡结构门禁**——`MAP_ARCHITECTURE_EMPTY`（让渡**已落地**，删除）→ ontology `UNMAPPED_PAGE`（`docs_governance.py:1090-1121`，signal）、`MAP_LINK_BROKEN :311`→降 signal（全局断链 ERROR 归 ontology `:676`）、对 map 文件的 `PAGE_KIND_INVALID :335-336` 人口由 role 判据自然界定（外人=未声明 role，已 fail-open 零读 `:236-237`/`:253-254`）、不再判 map 自身 kind；**(c) 保留页侧**——`AUTHORITY_MAP_BINDING :352-354` 与 `AUTHORITY_ID_MISSING/DUPLICATE :346/:350` 属 page-declaration 层法定职责（`skill-conventions.json:141-143`）。本调整经「读同一张磁盘 map + role 判据」达成，**不新增 architecture→ontology 运行期依赖**。
- **切片判据 = map role 声明（替代现 ERROR 墙）** `[目标→实为现状，取代 §9 的 `:335` 行为]`：
  - 判据不是 authority-id 前缀，而是 **map entry 是否声明 `role:`**——`validate_architecture_docs.py:251` 仅把带 role 的块收为 entry，未声明者走 `:253-254` 的 fail-open 路径；
  - `role: primary/supporting` → 进切片、按 §3 契约校验；未声明 role → `undeclared`，**零读**（`:236-237` 有界读契约）、不产 kind/prefix/binding 诊断，仅一条 `PAGE_ROLE_UNDECLARED` signal（`:291-297`）；
  - 此判据由 map（owner=ontology）决定，architecture **不自定 id 根**——否则即违反 §6「不 own 索引」；
  - **`#52` 反证**：`valid-external-layout` 的架构页 authority-id 用域命名空间 `nimbus.*`（`handbook/map.md:3-5`）且带 `role: primary`，任何 `architecture.`-前缀 id 判据都会误跳它们、违反 `test_the_layout_is_checked_not_skipped`；role 判据则正确纳入。`PAGE_KIND_INVALID` 保留但人口收窄为"map 声明为 role 条目、页 kind 却不符"的真漂移。
- **derived-only 对齐**：B 是 A 的派生投影，与 ontology `graph_snapshot` 的 `derived-only`（`docs_governance.py:797`）同纪律；二者是不同节点类型的两张图（B=概念图；ontology=文档图，边 ∈ `derived-from|supersedes|supports` `:27`），不竞争。
- **衔接方向不变** `[目标]`：两 skill 唯一运行期衔接仍是 ontology→architecture 的 `architecture_witness()` sha256 见证（`docs_governance.py:1217/:1307`）；上文「消费语义 (b)」的让渡只改变 architecture **是否自行报告** map 结构码，不引入对 ontology 产物的读取，故"互不 import"成立。

## 8. 运行模式：投影 / 独立目录 `[目标]`

- **投影模式**（在仓内，默认）：消费 repo doc-map，按 §7 role 判据取架构切片；可做 authority-id 相关 shape 检查。
- **独立目录模式**（指定目录、无 doc-map）：仅 ③ shape + 若提供则做 C↔B；**无 map 即无 authority-id↔page 绑定真相**，故**不产出任何 `AUTHORITY_MAP_BINDING`/id-1:1 类诊断**。
- （已定）两态诊断精确差集 = `AUTHORITY_MAP_BINDING`/id-1:1 这一族：投影态产出、独立目录态不产出（承 :148）；其余 ③ shape 及（若提供 B）C↔B 差分在两态一致。此差集同时是 §9 greenfield `MAP_MISSING` 的收口依据。

## 9. 迁移基线：现状实现 → 目标

> 本节唯一描述**已存在的代码**，所有 `文件:行号` 对 `validate_architecture_docs.py` 成立、可 grep。它是被本文定义逐步取代的起点，非规范。

现状是单进程只读校验器，流水线：`main(:393)` → `validate(:269)` → `discover_map(:129)`（显式指针→docs/README.md→`*-map.md` 候选，`:132-157`）→ `map_entries(:228)`（按行首 `- ` 切块、读 `role:`/`authority-id:`，`:242-252`）→ 逐 entry 主循环 `:308-384` → `exit(:415)`。现状施加的 shape 检查：`MAP_LINK_BROKEN:311`、`kind:319/335`、`authority:337`、`naming:339`、`primary authority-id 缺失/撞车/map 绑定:343-354`、`小节契约:355-363`、`source-map/ADR:365-384`；role/supporting/undeclared 语义 `:324-333`、`:253`；严重度 `signal` 标志 `:83-88`（默认 False→ERROR，`:88`）。**现状还自报的 map 结构码**（§7「消费语义 (b)」让渡 / 本节 Delta 降级对象；`MAP_ARCHITECTURE_EMPTY` 已于阶段 2 让渡删除、不再自报）：`MAP_LINK_BROKEN:311`（ERROR·与 ontology `:676` 双报）、`SIGNAL_MAP_DUPLICATE_LINK:388`（signal）、`MAP_KINDS:57`/`is_navigation:321` 对 map 自身的 kind 门禁与豁免链 `:339/:355`。

**Delta（现状 → 目标）**：

| 现状机制 | 目标处置 |
|---|---|
| ③ shape 全套（kind/naming/section/authority/source/ADR） | **保留**（§3），人口收窄到架构切片 |
| `:335` PAGE_KIND_INVALID 对任意 primary 触发 | **改造**：加 §7 role 判据前置（现状 `map_entries:251`）；`:335` 仅余 id-claim-vs-kind 漂移；**对 map 文件自身不再判 kind 门禁** |
| 无 concept-map / 不读代码 | **新增**：`formatter(A)` + B + closed-world（§2/§4） |
| 无一致性/债务检测 | **新增**：C↔B 方向差分，**signal-only**（§4） |
| 隐含"map 只含架构页" + §7 旧稿 id 前缀投影切片 | **替换→删除**：切片改由 map role 声明界定（§7「切片判据」）；id 前缀判据反证于 #52（nimbus.* 架构页）、且等于 architecture 行使索引归类权，违反不-own-索引 |
| greenfield 仍 `MAP_MISSING` ERROR（`:157`，与 ontology `:651/:1458` 不对称） | **收口**：无 doc-map 场景归入 §8 独立目录态，按已定差集不产出 map 绑定类诊断，从而消除该 ERROR 不对称（详见 §7「消费语义 (a)」） |
| `MAP_ARCHITECTURE_EMPTY:302`（迁移前；map 无架构链，ERROR） | **让渡（已落地，已删除）**：交 ontology `UNMAPPED_PAGE`（`docs_governance.py:1090-1121`，signal-only）；architecture 单跑不再报覆盖度，**ERROR→signal 降级（已接受）** |
| `MAP_LINK_BROKEN:311`（切片断链，ERROR，与 ontology `:676` 双报） | **降级**：改为 signal（开页局部后果；`:312` 零读跳过不变）；全局断链 ERROR 归 ontology |
| `SIGNAL_MAP_DUPLICATE_LINK:388`（重复链，signal） | **保留**：维持 signal，与 ontology 去重对账，不 own 索引去重 |
| `discover_map:129-158` 与 ontology `:620-651` 重复；greenfield 报 `MAP_MISSING:157` | **保留但降级**（Q1=①）：自带 discover 仅作只读投影取数，greenfield 对齐 `:651/:1457-1459`；不引入 architecture→ontology 依赖 |

## 10. 有意不实现与未决

- **不裁 C\B 成因**（定义）：本 skill 永不判"文档跑在代码前"是前瞻还是债。
- **不 own 索引、不改 doc-map**：索引真相唯一在 ontology。
- **target 文档不在管辖**：前瞻/路线属 roadmap/grilling。
- **shape 之外不做语义门禁**：①② 永远 signal（§5）。
- **不报跨 owner 成边**：分解/组合可合法跨归属，edges 不绑定 owner，报之即裁决（§2/§4）。
- `[未决]`：八 maintenance-triggers 之外是否需扩概念词表；`--part-of` 边的进一步语义（边 kind 分类、加权、跨图合并）。
- **已定**：B 前缀令牌 = `tacm-`，归入 `ta` 家族（§2）；C\B echo `target/implemented/inference/unknown` 标签作上下文、不作豁免（§4）；两态诊断精确差集 = `AUTHORITY_MAP_BINDING`/id-1:1 族，独立目录态不产出（§8）；greenfield `MAP_MISSING` 经 §8 独立目录态收口、不再作 ERROR（§9）；**切片判据 = map role 声明**——architecture 不预设 authority-id 根，域命名空间（如 `nimbus.`）归 map/ontology 持有（§7，#52 反证 id 前缀判据）；`undeclared` 与切片判据统一：未声明 role 者即 fail-open、零读（`:253-254`/`:236-237`）；**`MAP_ARCHITECTURE_EMPTY` 让渡 ontology `UNMAPPED_PAGE` 已落地**（ERROR→signal 降级；覆盖度仅在 ontology `--validate` 态报警，架构页须落 `docs/architecture/` 才被扫）；`tacm-` 已写入 SKILL.md `extensions`（`page-prefix:tacm-`，阶段3）；**D1 formatter(A)**（代码 `@concept:` → `--format-concepts`，closed-world）与 **D5 页侧 `concepts:` 声明**（C\B → `CONSIST_ORPHAN_DOC_CLAIM`，signal）已落地（PR-B）；**formatter `edges`（`--part-of` 概念边，closed-world）与 owner（`node.owner` → `CONSIST_OWNER_MISMATCH`）已落地**（PR-B 续 / §10 收尾，三向仍全 signal、不卡 exit）；**edges 复杂语义已落地**——多父（`--part-of` 多有效父）、环检测 `CONCEPT_CYCLE`（signal，B 内部 DAG 自洽）已实现，跨 owner 成边有意不报（见 §2/§4）。

> 落地顺序与逐文件改动（含 fixture/测试、`SKILL.md`、`skill-conventions.json`、`:335` 等三头对齐）属"如何把定义落到代码"，另立执行 plan，不在本设计文档范围。
