# zj-roadmap-driven: 执行图（Execution Graph，P5）

> 状态：问题 / 边界 / 已定输入约束 / schema 与迁移已定（#44、#45）。命令契约（#46）与写权限 + 测试策略（#47）待补。
> 上游：`docs/plans/zj-roadmap-dag-concurrency.md` §8（方向与边界已在那篇达成共识，本篇不复制其正文，只引用结论）
> Ticket：#44（骨架）→ #45（schema 与迁移）→ #46（命令契约）→ #47（写权限与测试）
> 建议 triage label：`ready-for-agent`

## 为什么另起一篇

并发 spec 已经有 62 条 user story，继续往里堆会把"执行图"这个独立 feature 淹没在一篇以并发为主题的文档里，且 §8 已达成的共识会被反复重读与重述。本篇只承载执行图；与并发 spec 重叠处一律**引用章节号 + 结论**，不复制论证过程——两份文档对同一规则各说一套是必须避免的缺陷，所以本篇不重述，只指向权威。

## Problem

### case 1（规划期就已知"这里有未知"）——**已部分落地**

`mode: explore|exploit` 是既有字段，但它只有一个标记、没有牙齿：规划人面对一段未知时，要么先把 placeholder 硬写成看起来确定的节点（规划失真），要么不写（图上出现空白，靠记忆维持）。

**已落地（PR #34，2026-09-10）**：`explore` 节点的结构预算 `budget: {max_children, max_rounds}` 与 `exploit` 节点的 `exit_criteria`。四条口径已钉死（见上游 §8.5）：开工 = 转入 `in_progress`、改小预算不追溯、`exit_criteria` 只存不判、触顶只返 `E_BUDGET_EXCEEDED`（退出码 3）。

**仍属 P5**：explore 的产出要能落成子节点，即 `promote` 通道。它依赖 trace layer 与 proposal 语义，因此归本篇（命令契约见 #46）。另有一条遗留：触顶时挂 open question 是 Story 35 / P2 的能力，case 1 切片里刻意没做。

### case 2（执行期涌现的东西无处安放，图膨胀到人看不懂）——**本篇要治的**

从首节点出发后，Loop 不断产出路线性材料：新问题、待定的分叉、"这个深井节点比预想的深得多"、跨子树的新关联依赖。今天它们只有三个去处：

1. 塞进 `notes` —— 丢失结构、不可查询；
2. 塞进 `decisions` —— 节点内嵌数组，不能跨节点共享，也不能被别的节点引用；
3. 直接 `add` 成 roadmap 节点 —— 把一次零散发现升格为正式任务，图迅速膨胀。

三者都不对。前两个让信息沉没，第三个让地图被过程污染。于是 Human 与 Agent 一起陷入"图越大，越不知道自己在哪、下一步该干什么"。

### 共同结构

上游两条 problem（9 / 10）指向同一件事：**本技能的整图模型是静态的**——它假设路线在执行开始前已被规划完备，执行只是把它走完。真实情况是路线一边走一边长。

依赖图（P1）能表达"该做什么"，但表达不了"我们是如何走到这里、为什么现在是这样"。执行图补的是后一半。

## Goals

- 让执行过程中涌现的材料有**结构性**的去处：有 kind、有 provenance、可被引用、可被追溯，而不是沉进 `notes` 或污染地图。
- 让 `context` 的供给从"树形"变成"沿边"——Agent 拿到与当前步相关的一组边，而不是整棵树。
- 让"这个 roadmap 节点为什么存在"可机械回答（回溯 `derives-from` 链）。
- 让"我现在在哪、有哪些未闭合分支"可机械回答。
- **不增加 Human 的认知负担**：新增的一层不进 md、不进 `ready`、不进关键路径。

## Non-goals

- **trace 的可视化**（canvas / HTML / Mermaid 全景图）。它最容易消耗工作量、最容易被砍，且对"导航与上下文供给"这个目标不是必需——`context` / `why` / `whereami` 已覆盖导航诉求。
- **多设备 trace 合并**。本轮只要求 trace 节点诞生时带 `device_id` / `agent_id` / `session_ref` provenance（provenance 事后补不回来，合并可以后来做），合并本身属于 P4。
- **trace 进 md**。这是硬边界而非默认值，理由见下一条判据。
- 重新设计依赖图、租约、carrier——那些属于上游 spec。

## 核心模型（结论，论证见上游 §8.1）

两层，不是一张图：

| | plan layer（现有） | trace layer（P5 新增） |
|---|---|---|
| 节点是什么 | roadmap node（一件待做的事） | turn / finding / doubt / attempt / artifact（一次已经发生的事） |
| 边的语义 | 调度依赖（`blocks` 等） | 上下文继承与因果（`mainline` / `reference` / `derives-from` / `prompted-by`） |
| 谁产出 | Human 与 planner | Agent 在日常执行中自动追加 |
| 稳定性 | 要稳定、要人审、要能被 `ready` 遍历 | 天生快速增殖，允许噪音 |
| md 默认可见 | 是 | **否** |

**判别式（唯一口径）**：这条信息需要被调度吗？需要 → plan layer；不需要、只用于解释"怎么走到这里"或给下一步供上下文 → trace layer。含糊时按 trace 处理，因为它便宜且可逆。

**硬判据**：**trace 可以自由增殖，但 md 的行数不允许随之增长。** 这是判断任何"把 trace 内容露出给人看"的提议的唯一标准，也是本 feature 不自我否定的前提——case 2 的症状是"越记录越迷路"，而 P5 恰恰引入了一张天生快速增殖的图。

## 已定输入约束（三条，实施时不得重新论证）

### 1. trace 与 plan 共享同一 carrier 与边表

节点集合多一个**必填**字段 `layer: plan|trace`；边集合**不加列**——边的层级由两端节点的 `layer` 推出。uid 规则、`E_CYCLE`、迁移路径、carrier adapter 契约、事件日志全部共用。

理由：跨图层 `derives-from` 边的参照完整性必须在一处维护。两个 carrier 各自保证自身完整、却无法互相校验，正是 `remove-decision` 在两个 carrier 上语义漂移的同一类缺陷。

**代价必须显式承担**：所有遍历谓词都要带 `layer == 'plan'`——`ready`、`critical-path`、`impact`、`tree`、md 渲染。共享把"忘记过滤"的后果从"跨 carrier 同步时才发现"变成"当场把 trace 泄进调度与视图"。防线只有两条：`layer` 必填，且每个遍历命令各有一条"trace 存在时输出不变"的负向用例。过滤条件的**归口方式**由 #45 定（判据：如果实施时开始第五遍手抄同一个条件，那就是设计错了）。

**共享 carrier 与 carrier 选型无关**——这一点常被误读，单独钉死：JSON single-file / bundle 上是同一份文件里的同一个 `nodes` 集合与同一个 `edges` 集合，SQLite carrier 落地后才是同一张 `nodes` 表与同一张 `edges` 表。也就是说这条约束在 P3 之前照样生效，不因 carrier 选型变化而改变。

### 2. `promote` 默认产出 proposal

`promote <trace_uid> --under <node_uid> --label "..."` 默认只产出 proposal 并挂 open question；Human 执行 `promote --accept <trace_uid>` 后才落正式节点，并自动写 `derives-from` 边。接受多条就在同一把锁内串行，**不新增批量接受命令**。

拒绝"默认直接生效 + Human 事后 reject"：那样 Agent 的一次误判会永久改变地图，正是 case 2 要消除的不确定性；proposal 让 Human 挑着接受，日常开销并不高。

连带计数口径：`max_children` 只计**已被接受的正式子节点**，proposal 不占额度。否则一轮探索里 Agent 先提满 N 条 proposal 就把额度用光，Human 还没审就没了空间——budget 约束的是地图，不是 Agent 的嘴。

### 3. 存量 `node.decisions` 不迁移进 trace layer

`node.decisions` 是结论摘要，trace 是过程明细，二者是**摘要与明细**的关系，并存不是重复。若迁移，md 渲染会失去它今天唯一的 decisions 来源，而 trace 又明确不进 md，等于让 Human 净失去这部分视野。

三条连带约束：

- `promote` 不回写 `node.decisions`——trace 的 `body` 是过程，promote 只创建 plan 节点与 `derives-from` 边；结论要不要进摘要由 Human 用 `decide` 决定。
- `context --include decisions` 读的仍是 `node.decisions`，不是 trace；读 trace 另有 `--include trace`。
- 迁移器不做 `decisions → trace` 的批量转换，老 carrier 升级后 `decisions` 数组原样保留。

## Schema、迁移与 `layer` 过滤契约（#45）

### 2.1 三个必须先承认的现状（源码实测，与上游措辞有出入）

上游 §8.1.1 要求"把 `layer == 'plan'` 收进 carrier adapter 的默认查询"。实施时要先承认三件事，否则这条要求落不了地：

1. **今天没有 adapter 抽象层。** single-file 的 `Roadmap` 与 bundle 的 `BundleRoadmap` 是两个各自遍历的类，中间没有统一查询接口。上游那句话的前提不存在——**不能直接照做，得先把遍历入口收敛出来**。
2. **今天没有 `edges` 集合。** carrier 里只有 `nodes` 与 `metadata`，边属 P1。因此本节的边 schema 是**待 P1 落地后生效**的契约，不是对现状的描述。
3. **两个 carrier 的"全量遍历"机制根本不同**：single-file 是内存里遍历 `nodes` 字典；bundle 是 **glob `nodes/*.json` 目录**。bundle 侧"遍历即目录扫描"，这不是可以靠加个 `if` 抹平的差异。

第 3 条决定了归口方案必须分两个 carrier 分别设计，再用同一套负向用例把语义钉在一起（见 2.3）。

### 2.2 过滤的方向：默认只给 plan，看 trace 必须显式要求

这是本节最重要的一个决定，它把失败方向**反转**了：

| | 忘记写过滤 | 后果 | 症状 |
|---|---|---|---|
| 若默认给全部 | 漏一个谓词 | trace 泄进调度与 md | **静默**，且与"视图膨胀"这个头号风险叠加在同一个 bug 上 |
| **默认只给 plan（选定）** | 忘记显式放开 | 该看到 trace 的命令看不到 | **立刻可见**：命令返回空，第一次跑就发现 |

也就是说，宁可"看不见"，不可"泄进来"。这是一个 fail-safe 的选择：功能缺失会当场暴露，数据泄漏不会。

落地为一个共享语义契约：**任何遍历入口的 `layer` 参数默认值是 `plan`；要访问 trace 必须显式传 `layer='trace'`（或等价的 `include_trace=True`）。**

### 2.3 归口：两级，两个 carrier 各有一层物理保障

**L1 — 遍历入口收敛（两个 carrier 都要做）。** 把散落的裸遍历收成少数命名入口，例如 `iter_nodes(layer='plan')` / `node_ids(layer=...)`。每个 carrier 各自实现一次，但语义契约（默认值、排序、返回什么）写在共享位置，不允许各解释一套——同一语义两套实现是本技能已经翻过一次的车（`remove-decision` 的 carrier 语义漂移）。

判据：**全量遍历点从"散落各处"收敛到少数几个命名入口。** 实施时若在第五个地方手抄同一个过滤条件，那说明 L1 没做，不是抄得不够。

**L2 — 默认值 `plan`。** 见 2.2，由 L1 的入口统一承担，调用方不写。

**L3 — bundle 的额外一层：物理隔离。** bundle 的 trace 分片放**独立目录**（如 `traces/`，与既有的 `decisions/` 平级），`nodes/` 只放 plan 节点。理由不是整洁，是机制：

- glob 无法按字段过滤——只有把文件读进来才知道它的 `layer`。若 trace 混在 `nodes/` 里，每个 glob 都要么读出全部 trace 文件（读放大），要么在每个 glob 后面补一遍过滤（又回到手抄）。
- 独立目录让 **目录布局本身就是过滤**：漏写过滤的后果从"逻辑错误"降级为"物理上看不见"。

这不违背"共享 carrier"——仍是同一个 bundle、同一张边表、同一套 uid 规则、同一份事件日志；**物理布局是 carrier 的实现细节，不是第二份真相**。

**L3 只适用于 bundle carrier**，它是实现手段而非语义约束：single-file 用内存过滤、bundle 用目录隔离、未来的 SQLite carrier 用列过滤，三者实现同一条语义契约（默认只给 plan）。本节的 schema 与语义条款（2.2、2.4、2.6—2.9）对三种 carrier 一视同仁。

**两个 carrier 机制不同会不会漂移？** 会，这正是风险 2 担心的那类缺陷。防线沿用 PR #34 已确立的做法：**同一套负向用例在两个 carrier 上各跑一遍**，而不是只跑源目录。

### 2.4 一条硬前提：trace 节点不进 `children`、不设 `parent`

除了全量遍历，还有一类更隐蔽的遍历：**沿 `children` 数组的递归**（`get_tree`、`_sync_parent_status`、`get_path`、`get_siblings`、`_collect_subtree`）。它们不算"全量遍历"，因此容易被漏掉，而一旦 trace 混进 `children`，后果和忘记过滤一样严重。

因此钉死：**trace 节点不进任何 plan 节点的 `children` 数组，也不设 `parent` 字段。** trace 的父子与延续关系只用边（`mainline` / `reference`）表达。连带的好处：trace 天然不参与 `_sync_parent_status` 的状态派生——它本来也没有 roadmap 意义上的 `status`。

### 2.5 遍历点清单（源码实测，归口时要逐个点名）

| carrier | 全量遍历点 | 现状机制 | 归口后入口 |
|---|---|---|---|
| single-file | 收集全部 decisions | 遍历 `nodes` 字典 | `iter_nodes(layer='plan')` |
| single-file | 找当前施工点（`get_current_focus`） | 遍历 `nodes` 字典筛 `in_progress` 叶子 | 同上 |
| single-file | `validate` 全量校验 | 遍历 `nodes` 字典 | 同上 |
| single-file | `stats` 统计 | 遍历 `nodes` 字典（含 max_depth） | 同上 |
| bundle | `rebuild_indexes` | glob `nodes/*.json` | glob `nodes/`（目录即过滤） |
| bundle | `stats`（含 max_depth） | glob `nodes/*.json` | 同上 |
| bundle | `get_decisions`（无 id） | glob `nodes/*.json` | 同上 |
| bundle | `validate` | glob `nodes/*.json` | 同上 |
| bundle | 焦点刷新（`_refresh_focus`） | 候选集 | 同上 |

沿 `children` 递归的那一类不在表内——它们由 2.4 那条硬前提兜住，不需要逐个改。

未来 P1/P5 新增的 `ready` / `critical-path` / `impact` / `context` 同样受此约束，且**每个都要有一条"trace 存在时输出字节不变"的负向用例**。

### 2.6 节点 schema

共享字段（两个 layer 都用）：`layer`（**必填**，`plan` / `trace`）、`uid`、`created_at`。

trace 节点：

| 字段 | 类型 | 说明 |
|---|---|---|
| `kind` | enum | `turn` / `finding` / `doubt` / `attempt` / `artifact` |
| `body` | string | 内容 |
| `agent_id` / `device_id` / `session_ref` | string | provenance，**诞生即写**（事后补不回来） |
| `compressed_from` | list[uid] | 可选。把一条长链压成 higher conclusion（thoughtDAG 的 merge nodes） |

trace 节点**没有** `parent` / `children` / `status`（见 2.4），也没有 `decisions`。

plan 节点沿用现有字段（`id` / `label` / `status` / `mode` / `parent` / `children` / `decisions` / `notes`，以及 case 1 新增的 `budget` / `exit_criteria` / `rounds`），只多一个 `layer: 'plan'`。

uid 规则与 plan 共用同一个命名空间（P0），trace 与 plan 的 uid 不重叠。

### 2.7 边 schema（随 P1 落地，此处只定契约）

| 类型 | 语义 | 跨层 | 允许成环 |
|---|---|---|---|
| `mainline` | 第一条入边，决定延续关系 | 否 | 否 |
| `reference` | 并入上下文，不改变 mainline 归属 | 可 | 是 |
| `derives-from` | trace → plan，追溯一个节点为什么存在 | 是 | 否 |
| `prompted-by` | plan → trace，记录这次探索由谁触发 | 是 | 否 |

边集合**不加 `layer` 列**——层级由两端节点推出。跨层边 `derives-from` / `prompted-by` 必须单向且不成环，复用 P1 的 `E_CYCLE`，不另起一套环检测。

### 2.8 迁移

- 老 carrier 升级后，**所有既有节点写 `layer: 'plan'`**（默认值），`decisions` 数组原样保留。
- **不做 `decisions → trace` 的批量转换**（输入约束 3）。
- 迁移**必须显式命令触发**，不自动（上游 Out of Scope 已定）。
- bundle 侧：新建空的 `traces/` 目录，`nodes/` 内容不动。
- 迁移后 `edges` 为空集合（边随 P1 引入），不是"迁移时凭空造边"。

**最硬的一条验收**：迁移完成后 `validate` 通过，且 **md 输出与迁移前字节一致**。迁移是加字段，不是改视图——Human 不应该看到任何变化。

### 2.9 负向用例（每个都要能"抽掉实现就红"）

- 每个遍历点：写入一批 trace 后，该命令的输出与写入前**字节一致**。
- 迁移：md 输出字节不变；`decisions` 条目数不变。
- 参照完整性：删除一个已被 `promote` 引用的 trace 节点必须失败（同表校验，不是跨 carrier 约定）。
- bundle：往 `traces/` 里放内容后，`stats` / `validate` / `rebuild_indexes` 的数字与之前一致。
- 硬前提：任何把 trace 节点塞进 `children` 的写入路径必须被拒绝（否则 2.4 形同虚设）。

以上每一项在两个 carrier 上各跑一遍。

## 方法来源与一处改写

方法论借自 [`chenxiachan/thoughtdag`](https://github.com/chenxiachan/thoughtdag)（把多轮会话建模为以边为上下文的可编辑无环图，"The graph is acyclic. You are the loop."），借的是方法而不是它的画布 UI 与多 Harness 会话导入——本技能只有 CLI 与 carrier。

三条照搬：**边即上下文**（落地为 edge-driven `context`）、**数据无环、循环由人的迭代构成**（复用 `E_CYCLE`，Loop 的闭环表现为新增节点而不是环）、**first edge in 决定 mainline**（给布局与角色继承一个确定性答案）。

**第四条必须改写**：thoughtDAG 主张 "No autonomous agent redraws your graph"，它与"Agent 不点名也能取活"正面冲突。全盘接受等于放弃本技能的核心价值，完全无视则会得到"Agent 悄悄改规划"。本 spec 的解法是**按写权限分层，而不是按参与者一刀切**：append 与 rewrite 分开授权（矩阵见 #47）。口诀：**Agent 拥有它的过程记录，Human 拥有地图。**

若实施时被说服改成完全禁写，则上游的 P2 租约、P3 并发整套对象都会失去意义——那应该是一个单独的、更保守的技能，而不是本 roadmap 的演化。

## 前置依赖与落地顺序

**P0 → P1 → P3 → P5。**

- **P0（不可变 uid）**：trace 节点与跨图层边都以 uid 为参照。在位置型 id 上建第二张图，等于重犯"并发先于 uid"的本末倒置——id 复用会让边挂到错误的节点上，这类 bug 静默且难查。
- **P1（依赖层与 `E_CYCLE`）**：`derives-from` / `prompted-by` 必须复用同一套环检测与边基础设施，不能另起一套。
- **P3（SQLite carrier）**：trace 天生快速增殖。JSON carrier 每次写是整图重写，trace 的写入量会把这个成本放大到不可接受；P3 落地后才是单行写入。

case 1 的 budget / exit_criteria 是唯一例外：它不依赖任何 P5 新结构，所以已经先行落地（PR #34）。

## 本篇未覆盖（后续 ticket）

#45（schema、迁移与 `layer` 过滤契约）已并入上文 §2。

- **#46**：`trace add` / `promote` / `prune` / `context --include` 的参数、输出与错误码；新错误码全部并进现有那一张 `ERROR_EXIT_CODES` 表。
- **#47**：append / rewrite 权限矩阵、Testing 缝与负向用例清单、详细落地顺序与风险。

## 风险（本篇层面）

1. **P5 自己携带它要治的病。** 若 trace 允许进 md、允许被 `ready` 遍历、或不经人审就变成 roadmap 节点，"多记录一层就多看一张图"会重演 case 2。硬判据（md 行数不随 trace 增长）是唯一防线。
2. **共享 carrier 把"忘记过滤 `layer`"从远端错误变成当场泄漏**，且与"视图膨胀"这个头号风险叠加在同一个 bug 上。
3. **视图膨胀是头号风险。** 本技能的核心卖点是"Human 一眼看懂"。任何向 md 加内容的提议，先回答"这一行能让 Human 少问一句吗？"——默认答案是不加。
