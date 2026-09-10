# zj-roadmap-driven: 执行图（Execution Graph，P5）

> 状态：v0 骨架（问题 / 边界 / 已定输入约束）。schema 与迁移、命令契约、写权限与测试策略另见后续 ticket。
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

- **#45**：trace 节点与边的 schema、老 carrier 的迁移路径、`layer == 'plan'` 过滤的归口方式。
- **#46**：`trace add` / `promote` / `prune` / `context --include` 的参数、输出与错误码；新错误码全部并进现有那一张 `ERROR_EXIT_CODES` 表。
- **#47**：append / rewrite 权限矩阵、Testing 缝与负向用例清单、详细落地顺序与风险。

## 风险（本篇层面）

1. **P5 自己携带它要治的病。** 若 trace 允许进 md、允许被 `ready` 遍历、或不经人审就变成 roadmap 节点，"多记录一层就多看一张图"会重演 case 2。硬判据（md 行数不随 trace 增长）是唯一防线。
2. **共享 carrier 把"忘记过滤 `layer`"从远端错误变成当场泄漏**，且与"视图膨胀"这个头号风险叠加在同一个 bug 上。
3. **视图膨胀是头号风险。** 本技能的核心卖点是"Human 一眼看懂"。任何向 md 加内容的提议，先回答"这一行能让 Human 少问一句吗？"——默认答案是不加。
