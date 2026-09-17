# Roadmap 执行图（trace layer，P5）

`doc-kind: design`
`authority: primary`
`authority-id: design.roadmap-execution-graph`

> Bounded question: 执行期涌现的发现与上下文需求，zj-roadmap-driven 如何记录与供给而不膨胀 Human 视图、不污染地图？
> 上游 spec：`docs/plans/zj-roadmap-dag-concurrency.md` §8（方向与边界）；本篇细化 spec：`docs/plans/zj-roadmap-execution-graph.md`（均已抽取至 designs 后于 2026-09-16 从仓库删除，原稿见 git 历史 `929b4ab^`）。本文只提炼权威结论与决策理由。

## 要治的病

依赖图（P1）能表达「该做什么」，表达不了「我们如何走到这里、为什么现在这样」。执行期涌现的材料（新问题、待定分叉、深井节点、跨子树新关联）今天只有三个去处：塞 `notes`（丢结构）、塞 `decisions`（不可跨节点共享）、或 `add` 成节点（图膨胀）。三者都不对。解法不是「加更多图」，而是**从同一 carrier 派生不同投影**（case 2 的膨胀靠投影解，不是靠更多图）。

## 核心模型：两层，不是一张图

| | plan layer（现有） | trace layer（P5 新增） |
| --- | --- | --- |
| 节点 | roadmap node（一件待做的事） | turn / finding / doubt / attempt / artifact（一次已发生的事） |
| 边语义 | 调度依赖（`blocks` 等） | 上下文继承与因果（`mainline` / `reference` / `derives-from` / `prompted-by`） |
| 产出者 | Human 与 planner | Agent 日常执行中自动追加 |
| 稳定性 | 要稳定、要人审、要能被 `ready` 遍历 | 天生快速增殖，允许噪音 |
| md 默认可见 | 是 | **否** |

**判别式（唯一口径）**：这条信息需要被调度吗？需要 → plan layer；只需解释「怎么走到这里」或供下一步上下文 → trace layer。含糊时按 trace（便宜且可逆）。

**硬判据（本 feature 能否成立的前提）**：**trace 可自由增殖，但 md 行数不允许随之增长。** 任何「把 trace 露出给人」的提议都以此判，默认不加。case 2 的症状是「越记录越迷路」，而 P5 恰恰引入一张快速增殖的图——这条判据防止 P5 自我否定。

## 三条已定输入约束（实施时不得重新论证）

1. **trace 与 plan 共享同一 carrier 与边表**：节点多必填字段 `layer: plan|trace`，边**不加列**（层级由两端节点推出）；uid 规则、`E_CYCLE`、迁移路径、adapter 契约、事件日志全部共用。理由：跨图层 `derives-from` 参照完整性必须在一处维护，两个 carrier 各自完整却无法互验正是 `remove-decision` 那类缺陷。代价：所有遍历谓词带 `layer == 'plan'`，防线是 `layer` 必填 + 每遍历命令一条「trace 存在时输出不变」负向用例。**此约束与 carrier 选型无关**——JSON 上同文件同集合，SQLite 上同表。
2. **`promote` 默认产出 proposal**：`promote <trace> --under <node>` 默认只写 `promotion.state="proposed"` 并挂 open question；Human `promote --accept` 后才落正式节点并自动写 `derives-from` 边。拒绝「默认生效 + 事后 reject」——Agent 一次误判就永久改图，正是 case 2 要消的不确定性。连带：`max_children` 只计**已 accepted** 子节点，proposal 不占额度。
3. **存量 `node.decisions` 不迁移进 trace layer**：`decisions` 是结论摘要、trace 是过程明细，并存不是重复。若迁移，md 渲染会失去唯一 decisions 来源而 trace 又不进 md，等于让 Human 净失视野。连带：`promote` 不回写 `decisions`；`context --include decisions` 仍读 `node.decisions`；迁移器不做 `decisions → trace` 批量转换。

## 共享 carrier 的归口（L1/L2/L3）

- **L1 遍历入口收敛**：散落裸遍历收成少数命名入口（如 `iter_nodes(layer='plan')` / `node_ids(layer=...)`），语义契约（默认值、排序、返回）写在共享位置，不允许各解释一套——同一语义两套实现是本仓库翻过的车。
- **L2 默认值 `plan`（fail-safe）**：任何遍历入口 `layer` 默认 `plan`，看 trace 必须显式传 `layer='trace'`。方向反转——宁可「看不见」（命令返回空，当场暴露），不可「泄进来」（静默且叠加头号风险）。
- **L2 字段过滤**：trace 与 plan 节点同处 `nodes`（single-file 的 dict、SQLite 的表），靠 `layer` 字段区分——`iter_nodes` 按层过滤，漏写过滤会让 trace 泄进 plan 视图。这是实现手段非语义约束：single-file 内存过滤、SQLite 列过滤，二者实现同一条语义契约。**两 carrier 机制不同会漂移，防线是同一套负向用例两 carrier 各跑一遍。**
- **硬前提（2.4）**：trace 节点不进任何 plan 节点的 `children`、不设 `parent`；trace 父子只用边表达。它天然不参与 `_sync_parent_status` 派生。

## trace 节点 schema（最小集）

共享字段：`layer`（必填）、`uid`、`created_at`。trace 专属：`kind`（`turn`/`finding`/`doubt`/`attempt`/`artifact`）、`body`、provenance `agent_id`/`device_id`/`session_ref`（**诞生即写，事后补不回来**）、可选 `compressed_from: [uid]`（压长链成 higher conclusion）、`promotion` 对象（proposal 一等状态）。**trace 无 `parent`/`children`/`status`/`decisions`**。plan 节点沿用现有字段，只多 `layer:'plan'`。

provenance 的本轮范围：trace 节点诞生即带 device/agent/session，但**多设备合并属 P4，不在本轮**——provenance 先落地是因为事后补不回来，合并可后来做。

## 边 schema（随 P1 落地）

`mainline`（第一条入边定延续，否成环）/ `reference`（并入上下文，可成环）/ `derives-from`（trace→plan，跨层，否成环）/ `prompted-by`（plan→trace，跨层，否成环）。跨层边单向且不成环，复用 P1 的 `E_CYCLE`。

## 命令契约（#46）

`trace <action>` 一个 COMMANDS 条目内部按 positional 分派（add/list/get/prune），与上游 `trace add` 写法一致。`trace add` 无需审批（provenance 诞生即写）；`promote` 默认 proposal；`prune <trace> --edge <id>` 删边而非删节点（借 thoughtDAG：删一条边即改变上下文）；`context <node> --include …` edge-driven，默认 `layer='plan'`。所有失败输出到 stderr 且必须含 `E_*` code。

新增错误码（全进 `ERROR_EXIT_CODES`，每码一个 `RoadmapError` 子类，不另起机制）：`E_TRACE_NOT_FOUND` / `E_INVALID_KIND` / `E_INVALID_LAYER` / `E_LAYER_VIOLATION`（塞 trace 进 children）/ `E_PROMOTE_TARGET_INVALID` / `E_REFERENCED`（删被引用者）/ `E_CYCLE`（复用）。**新错误码默认退出码 1**，只有新增「需不同重试语义」的类别才开新退出码。

## 写权限分层（#47，thoughtDAG 原则 4 的改写落点）

**今天没有运行时身份**（无登录 / token / OPN session 绑定），不要假装有权限系统兜底。本轮取「命令边界（SKILL.md 列出 Agent 可调用命令）+ 状态机强制（plan 节点新增只能经 `promotion.state` 从 proposed→accepted 且写 `decided_by`）」，**不引入 `--actor` 自报身份**（自报不是权限）。

判据：**是否改变地图拓扑**。更新状态 / 记 decision / 渲染 = 施工（Agent 可做）；新增 / 删除 / 移动节点与跨层晋升 = 改图（需 Human）。

| 层 | 动作 | Agent | Human |
| --- | --- | --- | --- |
| trace | `trace add` / `prune`（删边） | ✅ 自主 | ✅ |
| trace→plan | `promote`（默认 proposal） | ✅ | ✅ |
| trace→plan | `promote --accept` / `--reject` | ❌ | ✅（落正式节点 = 改图） |
| plan | `add`/`update`/`delete`/`decide`/`render`/`migrate` | ✅（按给定图施工） | ✅ |
| 并发 | 同 carrier 写命令并行 | ❌ | ❌ |

口诀：**Agent 拥有它的过程记录，Human 拥有地图。** 命令边界那条（Agent 不调 `promote --accept`）今天无法自动化测试，只能靠文档约束 + code review——不要为可测而提前引入 `--actor`。

## 方法来源与一处改写

方法论借自 `chenxiachan/thoughtdag`（多轮会话建模为以边为上下文的可编辑无环图），借方法不借画布 UI。三条照搬：边即上下文（edge-driven `context`）、数据无环循环由人迭代构成（复用 `E_CYCLE`，闭环表现为新增节点）、first edge in 定 mainline（确定性布局/角色继承）。**第四条必须改写**：thoughtDAG「No autonomous agent redraws your graph」与「Agent 不点名也能取活」正面冲突，改写解是**按写权限分层而非按参与者一刀切**。若被说服改成完全禁写，则 P2 租约 / P3 并发整套失去意义——那应是另一个更保守的技能。

## 落地切片（S1—S4，顺序不可换）

S1 `layer` 字段 + 迁移 + L1/L2 归口 → S2 `trace add` + provenance → S3 `promote`/`--accept`/`--reject` + `promotion` 状态机 → S4 `prune` + edge-driven `context --include`。S2 依赖 S1 的 layer，S3 依赖 S2 的 trace 节点与 S1 的边基础设施（P1），S4 依赖 S3 之后的 `derives-from`。

**完成判据（三条缺一即没做完）**：① md 行数不随 trace 增长（硬判据）；② Agent 能不被点名自主记录（trace add 无需审批、provenance 自动带上）；③ Human 能挑着接受（promote 出 proposal，accept 后节点进图且可被 `derives-from` 回溯）。

## 风险

1. **P5 自己携带它要治的病** —— trace 进 md / 被 `ready` 遍历 / 不经人审变节点，会重演 case 2；硬判据是唯一防线。
2. **共享 carrier 把「忘过滤 layer」从远端错误变当场泄漏**，且与视图膨胀头号风险叠加同一 bug。
3. **视图膨胀头号风险** —— 任何向 md 加内容的提议先答「少问一句吗」，默认不加。
4. **命令面膨胀** —— 新命令必须能被 Agent 机械调用（JSON 输出 + 稳定 `E_*` code），否则不值得进 CLI。
