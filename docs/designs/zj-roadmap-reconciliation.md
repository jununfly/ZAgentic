---
doc-kind: design
authority: primary
authority-id: design.roadmap-reconciliation
---

# Roadmap reconciliation 与原子 ChangeSet 设计（zj-roadmap-driven）

> 本页从已关闭的过程计划（2026-11-10 关闭，关联 #233 / #234 / #235 / #236；原计划按
> ADR 0010 在 close-out 后清理、语义沉淀为本页）抽取其**持久设计语义**而来。
> 过程 close-out 记录（评审记录、issue 映射、带日期的指标与实现证据、回放/回滚步骤）
> 不在此页复述——它们属于产生它们的 commit / PR / ADR。本页只答一件事：
> reconciliation 与 ChangeSet 这一层**为什么这样设计、替代方案与代价、当前不变式**。
> 使用层（命令、参数、receipt 形状）见技能侧
> `skills/codebase-docs/zj-roadmap-driven/references/roadmap-data-model.md`，
> 本页不重复那些事实（一处事实一个家）。

## Context

`zj-roadmap-driven` 长期用有序树承载长期工作：`parent` + 有序 `children` 同时表达
工作身份、分解、显示位置、执行顺序、依赖与完成聚合。执行期涌现的发现从 Trace 层
直接写入新的 plan Node，**没有 Roadmap 级 reconciliation**。由此反复出现：重复/
重叠工作、依赖变化与拓扑变化游离在 Human 视野之外、拓扑改动破坏原子性。

诊断（非猜测）：反复失败的根因不是「树」本身，而是把工作身份、分解、显示位置、
执行顺序、依赖、完成聚合**六个概念压在同一个 Node/children 结构里**。把树换成裸 DAG
能提升表达力，但本身不能防止语义重复。

约束（与设计无关、保持不变）：Roadmap Scope Gate 在任何项目编辑或拓扑改动前强制；
Human 授权仍是拓扑变更接受的硬要求（自报 actor 标志不是认证）；所有持久引用用
不可变 `uid`，显示 id 只是便利地址；Markdown 仍是派生、不可导入的视图；两 carrier
（单文件 JSON / SQLite）必须暴露相同语义结果与稳定 `E_*` 错误；运行时 skill 闭包与
ADR 0010 相对路径持久化规则保持完好。

## Decision

**revise（修订既有方向，而非推翻）**：保留树作为 Human 主大纲，但**停止把有序树位置
当作工作身份或执行顺序**。先引入 reconciliation 接缝与原子 ChangeSet，再考虑完整的
canonical work-graph 迁移。也就是说，分两步走——先把「识别/去重/原子提交」做扎实，
等真实语料验证再动 Placement/分解事实的分离。

## Options

1. **保留有序树并加更多 Edge 类型。** 迁移成本小，但身份、重叠、直接 promote、部分
   拓扑突变仍悬而未决。→ 判定：不足，拒绝。
2. **用裸 DAG 替换树。** 调度与共享更灵活，但 Human 定向差，且对语义去重无内建防护。
   → 判定：不作为默认视图，并推迟为内部表示选择，拒绝。
3. **用自动模型辅助语义去重。** 对候选排序有用，但错误合并会摧毁工作与溯源。
   → 判定：拒绝作为权威；将来最多作为可选「候选产出 Adapter」。
4. **立即采用不可变事件溯源 + 修订 DAG。** 审计与冲突语义强，但迁移/存储成本高，且与
   当前「SQLite 优先于自研事件流」的选择不一致。→ 判定：推迟。
5. **选定混合方案（采用）**：先加深层 Reconciliation Module 与原子 ChangeSet；等语料
   验证证明需要时，再把 WorkItem 身份从大纲 Placement 中分离。

`precedes` 不进入初始词汇表。只有当 fixture 证明存在 `priority` 与 `blocks` 都无法
表达、又不破坏 `impact` 语义的强制非因果序列时，才引入它。

## Trade-offs

- 收益：重复/重叠工作在 Human 读原始 DAG 之前就被审查并原子提交；身份、分解、依赖、
  优先级、显示被拆成独立概念；拓扑/Edge 变更作为一次原子 ChangeSet 落地。
- 代价：reconciliation 增加 Roadmap 级候选匹配与图校验；Human 多一道「review 结果 +
  变更投影」的步骤（调用方看结果而非手搓低级 CRUD）；拓扑突变被刻意做重——必须 preview
  加接受，因为静默结构编辑难以恢复。
- 明确不做：用树替换图 UI、远程协调/云存储/网络服务、模型自主合并语义相似 Node、
  通用约束语言、立即用完整事件溯源替换当前 carrier。

## Consequences

选定模型（当前已落地于两 carrier）：

```text
Trace finding
  -> Reconciliation Proposal
       covered | refine | reshape | novel | dismiss | unresolved
  -> Human review
  -> atomic ChangeSet
       WorkItem changes + Placement changes + Edge changes
       + Decisions + Trace disposition
  -> canonical semantic state
       -> Human outline projection
       -> ready / blocked / critical-path / impact
```

概念分离：

| Concern | Representation |
|---|---|
| Work identity | `WorkItem(uid)` |
| Decomposition | membership/contains relation |
| Hard causal dependency | `blocks` Edge |
| Selection among ready work | `priority` |
| Human placement and order | primary/reference Placement plus outline rank |
| Execution evidence | Trace layer |
| Plan mutation | versioned atomic ChangeSet |

### 节点与完成不变式

- `uid` 不可变、永不复用。
- 可执行的 `work` Node 是原子的，没有分解子节点。
- `group`/milestone 不可直接执行；其完成由所选成员派生。
- 一个被接受的 obligation 至多一个活跃 canonical owner；歧义产生 review 问题，不自动建 Node。
- 一个 WorkItem 可通过 reference Placement 出现在多个大纲上下文中；reference 不复制
  Status、Decision 历史、lease 或完成态。
- 显示顺序无调度语义。
- `blocked`、ready 集、关键路径、impact、group 完成、显示 id 都是**派生**的，不独立存储。

### Reconciliation 接缝

对外接口刻意做小：

```text
reconcile(base_revision, trace_cut, write_scope, answers?) -> Proposal
apply(proposal_id, approved_digest, idempotency_key)       -> CommitReceipt
project(revision, outline | execution | review)            -> View
```

- `reconcile` 为去重做**全局读**，但只在其声明 scope 内**写**；proposal 含候选匹配、
  新颖性证据、预期的 WorkItem/Placement/Edge 改动、impact 与未决问题。
- `apply` 比对 base revision 与当前 revision，校验最终候选图，然后全有或全无提交；
  Markdown 刷新发生在 canonical 提交之后；刷新失败返回已提交 revision + stale-view 信号，
  重试不会重复突变。
- 实现隐藏：obligation 抽取、确定性候选匹配、重复聚类、split/merge/coalesce 语义、
  Edge 重连、环与层校验、显示 id 重映射、carrier 事务、派生查询。

### Reconciliation 处置（dispositions）

| Result | Meaning | Plan effect |
|---|---|---|
| `covered` | 现有 WorkItem 已拥有该 obligation | 仅链溯源 |
| `refine` | 现有工作需判据/范围澄清 | Patch 或显式重开 |
| `reshape` | 现有拓扑错误 | 在 ChangeSet 中 split/merge/move/supersede |
| `novel` | 无活跃 WorkItem 覆盖该 obligation | 新颖性证据后创建 |
| `dismiss` | 证据不要求调度 | 保留 Trace 与 Decision |
| `unresolved` | 身份/范围歧义 | 阻塞 apply，待 Human 回答 |

创建要求：必须列出候选并说明为何都不覆盖该 obligation；确定性身份匹配可被机械拒绝，
语义相似只产生候选。

### ChangeSet 语义

ChangeSet 有稳定 id、base revision、Scope Gate 分类、Trace 溯源、前置条件与封闭变更列表。
初始变更种类：`work.create/patch/coalesce/supersede`、`placement.put/move/reference`、
`edge.put/remove/replace`、`decision.append`、`trace.disposition`。

实现把全部变更应用到私有候选态，**校验最终态而非中间操作**，再以 compare-and-swap 对
base revision 提交。初始设计**不需要**完整不可变事件存储；当前 revision 哈希 + carrier
原生原子替换/事务已足够。

### 失败处理

- `E_IDENTITY_AMBIGUOUS`：返回候选 WorkItem 与所需 Human 问题。
- `E_OVERLAP_UNRESOLVED`：obligation 有多个未决活跃 owner。
- `E_CONFLICT`：base revision 变化；重跑 reconciliation。
- `E_APPROVAL_MISMATCH`：reviewed digest 与正应用的 proposal 不符。
- `E_CYCLE`：最终依赖/分解图违反无环。
- `E_LAYER_VIOLATION`：Trace/plan 方向或 Placement 规则被违反。
- `E_SCOPE`：提议写入逃逸出已批准子树/scope。
- `E_CHANGESET_INVALID`：最终候选违反结构不变式。
- `E_VIEW_STALE`：canonical 提交成功但 Markdown 发布需修复。
- `E_PROCESS_AUTHORITY_LEAK`：视图泄漏 process-state（authority 信封缺失）。

语义不确定性是 proposal 状态，不是异常。既有的可重试锁与预算退出码含义不变。

### 兼容与迁移

1. 加只读 `reconcile` preview，其余命令不变。
2. 把 `promote` 提议路由经 reconciliation；语料验证期保留直接接受背后的兼容 Adapter。
3. 加 ChangeSet preview/apply 并把拓扑变更命令路由经它。
4. 引入 typed `group`/`work` Node 并出迁移报告；保留所有 `uid`。
5. 把既有 `parent`/`children` 转为 primary Placements/分解事实；旧 child 顺序只作大纲
   提示，绝不从中推断依赖。
6. 仅在双 carrier 等价 + 真实语料回放闸门通过后，才禁用直接拓扑突变。

源 carrier 在迁移期保持可恢复。**不允许 dual-write**——那会造出两个竞争的事实源。

### 所有权边界

- reconciliation 策略、ChangeSet 校验、派生调度：Roadmap core Module owner。
- JSON/SQLite 持久化原语：carrier Adapter owner。
- CLI 参数翻译与面向 Human 的错误：CLI Adapter owner。
- Markdown 布局与 reference 记号：projection owner。
- 歧义身份/范围的决策：Human decision owner。

## 参考 Placement 记号决策（S4-2, #236）

最终 Markdown 记号：**`↪ reference (same WorkItem, not a copy): <label>`**。

三选一评审（A/B/C），选 C 的理由：显示 id 来自 WorkItem，故 reference 行也以 `1-1`
开头——B 会产生自引用 `1-1. Shared work [reference to 1-1]`，且尾随标记落在 200+
字符的长标题之后；显示 id 明确不是持久引用。A 被拒是因为「same WorkItem / not a copy」
只能推断、不能从文本读出。C 把标记前置、用文字把身份说清，且去掉 `↪` 字形后仍能正确
阅读。该字符串在 renderer、tests、CLI reference、data model、SKILL.md、ZJ-CONTEXT.md
中以**同一字符串**落地。

已知限制（记为此决策的风险，不默认判通过）：

| ID | 限制 | 范围 |
|---|---|---|
| R1 | primary 与 reference 行显示同一 `1-1.`，因显示 id 来自 WorkItem 而非 Placement | 全部变体；显示 id 投影层，超出 #236 范围 |
| R2 | `tree --anchor` 把完成的 reference 折叠进 `... 1-4 已完成（折叠 1 项）▸`，折叠摘要无 `reference` 文本 | 渲染层后续 |
| R3 | radial `render` 视图树只显示 reference 行，primary 行出现在 `### 下一步可开工` 且无标记 | 现有 focus-radial 设计 |
| R6 | Status/Decision/lease/调度的唯一性结构性保证，但视图文本从未显式声明 | A/B；C 部分缓解 |

R2、R3 是渲染层后续，不在本决策修复范围内；R1、R6 是显示 id 投影与视图文本的已知限制。

## 跨切面原则

- **性能**：reconciliation 增加 Roadmap 级候选匹配与图校验；首版用基于 `uid`、归一化
  obligation key、溯源、活跃 Status、Edge 邻域的确定性索引；可选模型辅助排序不在关键路径。
  R5 节点 p95 容量闸门为初始容量门槛。
- **简洁与可达性**：Human 继续读有界树；新增复杂度集中在 Reconciliation Module 之后；
  reference Placement 必须有文本标签，不得仅用颜色表意；Markdown 视图在纯文本与
  屏幕阅读器导航下仍可用；拓扑突变被**刻意做重**（需 preview + 接受），因为静默结构编辑
  难以恢复。
- **安全与隐私**：设计不引入网络访问、凭据或远程持久化；Trace 体与 Decision 可能含敏感
  本地上下文，仍受既有 carrier 访问与留存规则约束；若将来提议模型辅助匹配，它是新信任
  边界——需显式数据处理评审、opt-in、溯源，且模型只能**排序候选**、绝不提交合并；
  Human 批准证据是审计元数据，不是认证。
