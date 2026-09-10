# zj-roadmap-driven: 执行图（Execution Graph，P5）

> 状态：#44—#47 全部并入本篇，执行图 spec 完成（待实施）。实施切片见 §4.4。
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

### 输入约束 1 — trace 与 plan 共享同一 carrier 与边表

节点集合多一个**必填**字段 `layer: plan|trace`；边集合**不加列**——边的层级由两端节点的 `layer` 推出。uid 规则、`E_CYCLE`、迁移路径、carrier adapter 契约、事件日志全部共用。

理由：跨图层 `derives-from` 边的参照完整性必须在一处维护。两个 carrier 各自保证自身完整、却无法互相校验，正是 `remove-decision` 在两个 carrier 上语义漂移的同一类缺陷。

**代价必须显式承担**：所有遍历谓词都要带 `layer == 'plan'`——`ready`、`critical-path`、`impact`、`tree`、md 渲染。共享把"忘记过滤"的后果从"跨 carrier 同步时才发现"变成"当场把 trace 泄进调度与视图"。防线只有两条：`layer` 必填，且每个遍历命令各有一条"trace 存在时输出不变"的负向用例。过滤条件的**归口方式**由 #45 定（判据：如果实施时开始第五遍手抄同一个条件，那就是设计错了）。

**共享 carrier 与 carrier 选型无关**——这一点常被误读，单独钉死：JSON single-file / bundle 上是同一份文件里的同一个 `nodes` 集合与同一个 `edges` 集合，SQLite carrier 落地后才是同一张 `nodes` 表与同一张 `edges` 表。也就是说这条约束在 P3 之前照样生效，不因 carrier 选型变化而改变。

### 输入约束 2 — `promote` 默认产出 proposal

`promote <trace_uid> --under <node_uid> --label "..."` 默认只产出 proposal 并挂 open question；Human 执行 `promote --accept <trace_uid>` 后才落正式节点，并自动写 `derives-from` 边。接受多条就在同一把锁内串行，**不新增批量接受命令**。

拒绝"默认直接生效 + Human 事后 reject"：那样 Agent 的一次误判会永久改变地图，正是 case 2 要消除的不确定性；proposal 让 Human 挑着接受，日常开销并不高。

连带计数口径：`max_children` 只计**已被接受的正式子节点**，proposal 不占额度。否则一轮探索里 Agent 先提满 N 条 proposal 就把额度用光，Human 还没审就没了空间——budget 约束的是地图，不是 Agent 的嘴。

### 输入约束 3 — 存量 `node.decisions` 不迁移进 trace layer

`node.decisions` 是结论摘要，trace 是过程明细，二者是**摘要与明细**的关系，并存不是重复。若迁移，md 渲染会失去它今天唯一的 decisions 来源，而 trace 又明确不进 md，等于让 Human 净失去这部分视野。

三条连带约束：

- `promote` 不回写 `node.decisions`——trace 的 `body` 是过程，promote 只创建 plan 节点与 `derives-from` 边；结论要不要进摘要由 Human 用 `decide` 决定。
- `context --include decisions` 读的仍是 `node.decisions`，不是 trace；读 trace 另有 `--include trace`。
- 迁移器不做 `decisions → trace` 的批量转换，老 carrier 升级后 `decisions` 数组原样保留。

## §2 Schema、迁移与 `layer` 过滤契约（#45）

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
| `promotion` | object \| null | 可选。**proposal 的一等状态**，见 3.2（`state: proposed\|accepted\|rejected` + target / label / 谁在何时提议与决定） |

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

## §3 命令契约与错误码（#46）

### 3.1 三个必须先承认的现状（源码实测）

1. **`context` / `promote` / `prune` / 任何 trace 命令今天都不存在。** `roadmap_cli.py` 的 `COMMANDS` 表有 20 个条目，没有一个与 trace 相关。因此本节**全部是新增契约**，不是对现状的描述——读到这里的人不要以为"文档说的命令已经能用"。
2. **没有 open-question 设施。** 全仓 grep `open_question` / `open-question` / `proposal` / `promote` 在 Python 侧 0 命中（只有 `contextlib` 的噪音）。上游 §8.4 写的是"`promote` 默认产出 proposal **并挂 open question**"，而 open question 属 Story 35 / P2，**今天挂不上去**。
3. **`MULTI_VALUE_FLAGS` 目前只有 `exit-criteria` 一个成员。** `--include` 要注册进去，且它带一个陷阱：裸标志（`--include` 后面不跟值）会被 `_store` 存成 `["true"]`，静默变成"包含一个叫 true 的 include"。

### 3.2 因此：proposal 必须是 trace 节点上的一等状态（本节最关键的一条）

既然没有 open-question 设施可以挂，**proposal 就不能是"一个待办事项"，而必须是 trace 节点上的字段**：

```
promotion: {
  state: "proposed" | "accepted" | "rejected",
  target: <plan uid>,        # 提议挂到哪个 plan 节点下
  label:  "...",
  proposed_by / proposed_at,
  decided_by  / decided_at   # accept / reject 时写
}
```

- `promote`（默认）写 `state: "proposed"`，**退出码 0**——它不是失败，也不是"待重试"，它就是这一轮的预期结果。
- `promote --accept` 由 Human 执行：改 `state: "accepted"`，落正式 plan 节点，自动写 `derives-from` 边。
- `promote --reject` 记 `state: "rejected"`，**保留痕迹不物理删除**（与既有 `remove-decision` 同构：撤回是记录，不是擦除）。
- **P2 的 open-question 设施未来从同一状态读出**，不另建一张待办表——否则会出现"proposal 说已接受、open question 还挂着"的第二类双真相。

连带：§2 的 `max_children` 只计 **已 accepted** 的正式子节点（输入约束 2），`proposed` / `rejected` 都不占额度。

### 3.3 命令契约

命名：`trace <action>`（一个 `COMMANDS` 条目，内部按 positional 分派 add / list / get / prune），而不是 `trace-add` / `trace-get` 各占一条。理由：trace 是一个命令家族，且上游 §8 的写法就是 `trace add`。若实施时更想要与 `remove-decision` 一致的连字符风格，`trace-add` 是纯机械重命名，无语义差别——**这条不值得重新论证**。

| 命令 | 参数 | 行为 | 写在哪层 | 锁 |
|---|---|---|---|---|
| `trace add <path> --kind <enum> --body "…"` | `--under <plan uid>`（写 `prompted-by`）、`--from <trace uid>`（写 mainline/reference 边） | 追加 trace 节点，provenance 诞生即写，**无需审批**；不进 `children`（2.4） | trace | 整图锁 |
| `promote <path> <trace_uid> --under <plan uid> --label "…"` | — | 默认写 `promotion.state="proposed"` | trace（写 promotion 字段） | 整图锁 |
| `promote <path> <trace_uid> --accept` | — | Human 动作：落 plan 节点 + `derives-from` 边 | **plan** | 整图锁 |
| `promote <path> <trace_uid> --reject [--reason "…"]` | — | 记 rejected，保留痕迹 | trace | 整图锁 |
| `prune <path> <trace_uid>` | `--edge <edge_id>` | **删边而不是删节点**（借 thoughtDAG：删一条边即改变上下文）。不带 `--edge` 时默认删该节点的 mainline 入边——从上下文移除，节点仍在 | 边 | 整图锁 |
| `context <path> <node_uid> --include …` | `decisions` / `trace` / `children`，可重复 | edge-driven 上下文；默认 `layer='plan'`（2.2）；`--include decisions` 读的是 `node.decisions`（输入约束 3） | 只读 | 读锁（若实现无读锁则无） |

参数解析的两条约束：

- `--include` 注册进 `MULTI_VALUE_FLAGS`；**值为 `true`（被当成裸标志）时直接报错**，不要静默接受。
- 所有输出走 stdout 的 JSON，与既有命令一致；失败输出到 stderr 且**必须包含 `E_*` code 字符串**——Agent 按 code 分支，不按文案匹配（这条沿用 `RoadmapError` 已有的口号）。

### 3.4 错误码与退出码：两个维度，不要一对一

最容易写歪的地方是把每个 `E_*` 都配一个退出码。两者用途不同：

- **错误码（`E_*`）**：细粒度，给 Agent 在代码里分支用。
- **退出码**：粗粒度，给 shell / 编排用，只区分**重试语义**。现有四个：0 成功、1 通用失败、2 锁超时（可重试）、3 预算触顶（Agent 该收手）。

**规则：新错误码默认映射退出码 1。只有新增"需要不同重试语义"的类别才开新退出码。** 这条是为了防止退出码膨胀——退出码一旦按 `E_*` 一对一扩张，Agent 就要维护一张和错误码等长的表，而它真正需要的只是"要不要重试"。

新增错误码（全部并进 `roadmap.py` 的 `ERROR_EXIT_CODES`，每个一个 `RoadmapError` 子类，**不另起一套机制**——PR #34 已定）：

| code | 触发 | exit |
|---|---|---|
| `E_TRACE_NOT_FOUND` | 引用不存在的 trace uid | 1 |
| `E_INVALID_KIND` | `trace add` 的 kind 不在枚举 | 1 |
| `E_INVALID_LAYER` | 对 plan 节点用 trace 命令，或反向 | 1 |
| `E_LAYER_VIOLATION` | 试图把 trace 写进 `children` / 设 `parent`（2.4 的硬前提） | 1 |
| `E_PROMOTE_TARGET_INVALID` | `--under` 的目标不存在，或不是 plan 节点 | 1 |
| `E_REFERENCED` | 删除被引用者：已被 `promote --accept` 引用的 trace、或被 `compressed_from` 引用的节点 | 1 |
| `E_CYCLE` | 复用 P1 的环检测，不另起一套 | 1 |

### 3.5 幂等与并发

- 写操作仍在整图锁内（现有 `roadmap_file_lock` + `ExitStack`），锁超时沿用退出码 2。
- 幂等表（都是退出码 0，不报错）：
  - 重复 `promote`（同 target 同 label）→ 返回既有 proposal，不新增。
  - 对已 `accepted` 再 `--accept` → 不写第二个节点、不写第二条边。
  - 重复 `--reject` → 不新增痕迹条目。
- 接受多条 proposal：**在同一把锁内串行执行同一条命令多次**，不新增批量命令（输入约束 2）。

### 3.6 负向用例（#46，每条都要能"抽掉实现就红"）

- `trace add` 之后，所有 plan 遍历命令输出**字节不变**（2.9 的延续）。
- `promote`（默认）之后：md 输出字节不变、plan 节点数不变。
- `promote --accept` 之后：plan 节点 +1、`derives-from` 边 +1、md 输出**变化**（这次变化是预期的）。
- 删除被 `promote --accept` 引用的 trace → `E_REFERENCED`；删除被 `compressed_from` 引用的 trace → `E_REFERENCED`。
- 任何把 trace 塞进 `children` 的写入路径 → `E_LAYER_VIOLATION`。
- `context` 不带 `--include trace` 时，输出不含任何 trace 内容（字节级）。
- 每个新错误码一条用例，**断言 code 字符串而不是错误信息文案**。
- `--include` 裸用（值为 `true`）→ 报错，不静默接受。

以上每一项在两个 carrier 上各跑一遍。

## §4 写权限分层、Testing 与落地顺序（#47）

### 4.1 权限的载体：今天没有运行时身份（源码实测）

全仓 grep `actor` / `role` / `--as` / `approved` 在 Python 侧**没有任何身份概念**（0 命中，只有锁那边的 `PermissionError` 噪音）。现有约束全部是**文档级**的，写在 `SKILL.md`：

- 第 16 / 78 行：Agent 必须通过 CLI，**禁止直接编辑 carrier 与 md 的路线图 section**。
- 第 59 行：**禁止并行执行同一 JSON 的写类命令**。
- 第 85 行：迁移必须显式 `migrate --to bundle`，不自动。

也就是说，**不要假装有一条运行时权限系统在兜底**。可选的三种机制按强度递增：

| 机制 | 强度 | 本轮 |
|---|---|---|
| **命令边界**：Agent 允许调用的命令集合由 `SKILL.md` 列出，plan 的晋升命令不在其中 | 弱（靠自觉），但**今天就有**，与现有约束同级 | ✅ 采用 |
| **状态机强制**：把权限落进数据——plan 节点的新增只能经由 `promotion.state` 从 `proposed` 走到 `accepted`（3.2），且必须写 `decided_by` | 中（可验证：没有 proposal 的节点无法凭空出现） | ✅ 采用 |
| **显式 actor 参数**（`--actor agent\|human`） | 强，但今天**没有任何身份来源**（无登录、无 token、无 OPN session 绑定），加了只是自报，等于没有 | ❌ 本轮不做 |

本轮取 **1 + 2**，并把它们写进 `SKILL.md` 与契约文档**两处且表述一致**（两份文档对同一规则各说一套是评审必抓缺陷）。待未来有了身份来源再升级到 3——那时是加参数，不是推翻设计。

### 4.2 权限矩阵

关键澄清：**Agent 今天在 plan layer 是有写权限的**（`SKILL.md` 第 59 行明确 Agent 会调用 `add` / `update` / `delete` / `decide` / `render`）。所以不能一刀切说"plan = Human only"——那与现状矛盾。真正的判据是：

> **是否改变地图的拓扑。** 更新状态、记 decision、渲染 = **施工**（Agent 可做）；新增 / 删除 / 移动节点与跨层晋升 = **改图**（需 Human）。

这正是 thoughtDAG 原则 4 的改写落点：不是"禁止 Agent 写图"，而是**按写操作的性质分层**。

| 层 | 动作 | Agent | Human | 依据 |
|---|---|---|---|---|
| trace | `trace add` / `prune`（删边） | ✅ 自主 | ✅ | 过程记录，Agent 拥有 |
| trace→plan | `promote`（默认 proposal） | ✅ | ✅ | 提案不是落地，不占 `max_children` 额度 |
| trace→plan | `promote --accept` / `--reject` | ❌ | ✅ | **落正式 plan 节点 = 改图** |
| plan | `add` / `update` / `delete` / `decide` / `render` / `migrate` | ✅（按 Human 给定的图施工） | ✅ | `SKILL.md` 59 |
| plan | 直接编辑 carrier 或 md section | ❌ | 也不建议 | `SKILL.md` 16 / 58 / 78 |
| 并发 | 同一 carrier 的写命令并行执行 | ❌ | ❌ | `SKILL.md` 59 |

口诀：**Agent 拥有它的过程记录，Human 拥有地图。**

### 4.3 Testing：缝、规则与用例清单

**缝的选择**：以 **CLI 契约**为主缝（subprocess 调用，断言退出码 + stdout JSON + stderr 的 `E_*` code），carrier API 为辅。理由：CLI 是 Agent 与 Human 唯一的入口，也是唯一有稳定输出契约的地方；只测 carrier API 会漏掉参数解析与退出码映射——PR #34 的 `--exit-criteria` 多值、以及 3.1 提到的裸标志陷阱都只存在于这一层。

现有测试分布：`tests/`（`test_budget.py` 15 项、`test_lock_contention.py` 19 项、`verify_real_plan_corpus.py`）+ 根目录（`test_roadmap.py`、`test_roadmap_bundle.py`、`test_storage_advisor.py`）。trace 相关新增进 `tests/test_trace.py`。

**四条规则**（都是本仓库已经付过学费的）：

1. **两个 carrier 各跑一遍**——PR #34 确立：源目录绿不等于副本绿，同一语义两套实现正是 `remove-decision` 那类漂移。
2. **负向用例断言 `E_*` code 字符串，不断言错误文案**（3.3）。
3. **红绿双向**：每条新约束都要有"抽掉实现会红"的证明，不能只有正向断言（PR #27 / #28 / #34 三次实践）。
4. **字节级不变断言**用于"trace 不泄进视图"这类命题——只有字节级比较能抓住"多了一行结构相同的内容"。

**用例清单**（合并 2.9 与 3.6，并补本节新增）：

- 每个遍历命令：写入一批 trace 后输出与写入前**字节一致**。
- 迁移：md 输出字节不变；`decisions` 条目数不变。
- 参照完整性：删除已被 `promote --accept` 引用的 trace → `E_REFERENCED`；删除被 `compressed_from` 引用的节点 → `E_REFERENCED`。
- `promote --accept` 后：`decisions` 条目数不变（输入约束 3）、plan 节点 +1、`derives-from` 边 +1、md 输出**变化**（这次是预期）。
- 硬前提：任何把 trace 塞进 `children` 的写入路径 → `E_LAYER_VIOLATION`。
- `context` 不带 `--include trace` 时输出不含任何 trace 内容（字节级）。
- 幂等：重复 propose / accept / reject 均退出 0 且节点数不变。
- 每个新错误码一条用例，断言 code。
- `--include` 裸用（值为 `true`）→ 报错，不静默接受。
- 真实仓库 corpus（`verify_real_plan_corpus.py`）纳入：升级与新增 trace 后仍通过，确保**不误报**。

**一条诚实的声明**：命令边界那条（Agent 不调用 `promote --accept`）**今天无法自动化测试**——没有身份概念就没有可断言的对象。它只能靠文档约束 + code review，与现有"禁止直接编辑 carrier"同级。**不要为了让它可测就提前引入 `--actor`**：自报身份不是权限。

### 4.4 落地顺序（切片，每片可单独合并）

大序仍是 **P0 → P1 → P3 → P5**（"为什么不能提前"见下一节）。P5 内部再切四片，每片都能独立合并、独立测试：

| 片 | 内容 | 验收 |
|---|---|---|
| **S1** | `layer` 字段 + 迁移 + L1/L2 归口（2.3） | 迁移后 md 输出字节不变；所有遍历命令有"trace 存在时输出不变"的负向用例 |
| **S2** | `trace add` + provenance（3.3） | trace 可自由追加；plan 侧输出字节不变；trace 不进 `children` |
| **S3** | `promote` / `--accept` / `--reject` + `promotion` 状态机（3.2） | proposal 不落节点；accept 后才落；`max_children` 只计 accepted |
| **S4** | `prune` + edge-driven `context --include`（3.3） | 删边即改变上下文；`--include trace` 才可见 trace |

顺序不可换：S2 依赖 S1 的 `layer`，S3 依赖 S2 的 trace 节点与 S1 的边基础设施（P1），S4 依赖 S3 之后的 `derives-from` 才有东西可沿边取。

### 4.5 P5 的完成判据（Definition of Done）

一次通过三条才算完成，缺一条就是没做完：

1. **md 的行数不随 trace 增长**——硬判据，唯一判据。
2. **Agent 能在不被点名的情况下自主记录**执行过程（`trace add` 无需审批，provenance 自动带上）。
3. **Human 能挑着接受**：`promote` 产出 proposal，Human `--accept` 后节点才进地图，且能被 `derives-from` 回溯到来源。

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

**P5 内部的详细切片见 §4.4**（S1 schema 与归口 → S2 trace add → S3 promote → S4 prune/context），本节只解释为什么大序不能提前。

## 本篇未覆盖（后续 ticket）

#45（schema、迁移与 `layer` 过滤契约）已并入上文 §2。
#46（命令契约与错误码）已并入上文 §3。
#47（写权限分层、Testing 与落地顺序）已并入上文 §4。

执行图 spec 至此结构完整，剩余工作是实施（按 §4.4 的 S1—S4 切片）。

## 风险（本篇层面）

1. **P5 自己携带它要治的病。** 若 trace 允许进 md、允许被 `ready` 遍历、或不经人审就变成 roadmap 节点，"多记录一层就多看一张图"会重演 case 2。硬判据（md 行数不随 trace 增长）是唯一防线。
2. **共享 carrier 把"忘记过滤 `layer`"从远端错误变成当场泄漏**，且与"视图膨胀"这个头号风险叠加在同一个 bug 上。
3. **视图膨胀是头号风险。** 本技能的核心卖点是"Human 一眼看懂"。任何向 md 加内容的提议，先回答"这一行能让 Human 少问一句吗？"——默认答案是不加。
4. **命令面膨胀。** 本节新增 4 个命令（`trace` / `promote` / `prune` / `context`），这是 Human 的长期认知负担。判据：新命令必须能被 **Agent 机械调用**（JSON 输出 + 稳定 `E_*` code），否则不值得进 CLI——给 Agent 用的命令和给 Human 看的视图是两件事，别把后者塞进前者。
