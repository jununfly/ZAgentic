# zj-roadmap-driven: DAG 依赖、节点租约与并发执行

> Spec 生成时间：2026-09-09 · 来源会话：zj-roadmap-driven 深度评审（性能 / token / 巧思 / 选型 + AI & Human readiness + Loop/Graph/DAG 多 Agent）
> 目标技能：`zj-roadmap-driven`（源技能在 `skills/codebase-docs/zj-roadmap-driven/`，另有已安装副本；本轮的 P0–P4 修正已在 PR #27 / #28 中于源目录落地并通过 PR 合并）
> 建议 triage label：`ready-for-agent`

## Problem Statement

`zj-roadmap-driven` 现在是一台"单人手写账本"：它假设只有一个 Agent 在写、只有一棵树在长、只有 Human 在点名派活。这个假设在单会话里成立，一旦进入多 Agent（同设备并行、agent + subagent、跨设备）就会四处漏：

1. **并发写不安全——但失败模式不是"后写覆盖前写"。** 整条写命令（`load → 修改 → 整图 save`）跑在整图 mkdir 互斥锁内（`roadmap_cli.py:391`），读-改-写在物理上不会交错，父状态也是每次派生而非快照。所以不存在"两个 writer 各写一半"的窗口，"lost update"这个名字是错的。真实失败是：**拿不到锁的进程直接崩溃退出 1**，那次写入从未落盘——不是被覆盖，是根本没发生。根因在锁的异常分类，已在 PR #27 / #28 修复，归因细节见本节末尾的「归因修正」。
2. **只有树，没有依赖。** 父子关系之外无法表达"1-2-3 依赖 1-4-1"这类跨子树依赖。`blocked` 是 `status` 枚举里可以被 `add` / `update` 人工设置的值，但没有任何代码推导它——既无人设置也无推导，实际是一个永不出现的值。
3. **Agent 不会自己取活。** 没有就绪集概念，Human 不点名就没有下一步；多 Agent 场景下等于人为串行。
4. **Token 经济性差。** 所有输出一律 `indent=2` 全量 JSON，没有字段投影、没有紧凑格式、没有 quiet；一个决策要跑两次进程（`decide` + `render`）；`tree` 在单文件模式默认深度 10，一次误用就能灌进几千 token。
5. **节点 id 会复用。** 子节点序号取"最后一个 child + 1"，删掉尾部子节点后新节点拿回旧 id，租约、历史、外部引用（ticket / ADR / 设备间同步）全部会串号。
6. **Human 的视野在多 Agent 下反而变差。** md 视图里没有 owner、没有待决问题队列、没有阻塞链、没有关键路径——Agent 一多，人先瞎。
7. **错误码只登记了一个（PR #34 之后的状态）。** 机制已经存在：`RoadmapError` 带 `code` 与 `exit_code`，`ERROR_EXIT_CODES` 做"码 → 退出码"映射，失败输出形如 `Error: E_BUDGET_EXCEEDED: …`——码在行首，Agent 按码分支，不用匹配文案。缺口是**表里目前只有两个条目**：基类 `E_ROADMAP`（→1）与 `E_BUDGET_EXCEEDED`（→3）。P0 的其余码——`E_NODE_NOT_FOUND` / `E_INVALID_STATUS` / `E_CYCLE` / `E_LOCKED` / `E_CONFLICT` / `E_SCOPE` / `E_STORAGE`——尚未补进 `ERROR_EXIT_CODES`，这些失败路径现在都落到基类的 `E_ROADMAP` + 退出码 1，Agent 能程序化区分的只有"预算触顶"一种。退出码现状见 Implementation Decisions §2。
8. **只有耗尽终止，没有收敛终止（PR #34 之后的状态）。** 原文三小句逐句核对，两句已经不成立：`explore` 的 budget 已落地且**会判定**（`check_child_budget` / `count_round_start`，触顶报 `E_BUDGET_EXCEEDED`、退出码 3）；`exploit` 的 exit criteria **字段已落地，但只存不判**——自然语言判不了，PR #34 把它定成 "stored and returned, never evaluated" 是刻意的，不是缺口。剩下"Loop 没有终止条件"成立，但更精确的说法是：**今天唯一的停止方式是耗尽终止（budget 撞上限），没有收敛终止（探够了就停）**。收敛要判"这一轮有没有产出新东西"，而 roadmap 今天不承载过程记录——`rounds` 只是计数，没有"这轮发生了什么"的载体——所以判据随 **P5 的 trace layer** 落地（见 `docs/plans/zj-roadmap-execution-graph.md`），不在本 spec 实现。**不要在 P5 之前拿不存在的证据造近似判据**：那会把"暂时没东西可做"误判成"已经收敛"，比没有判据更糟。
9. **规划期就已知"这里有未知"，但没有表达它的地方（case 1）。** `mode: explore|exploit` 是实现了的字段（`roadmap.py:32`、CLI `add --mode`），可它只是一个标记：没有 budget（探索到什么程度就该收），没有 exit_criteria（什么算探索完了），也没有"探索产出 → 落成子节点"的机制。于是规划人在规划期面对一段未知时，要么先假装已知、把 placeholder 硬写成看起来确定的节点（规划失真），要么不写（图上出现一段空白，只能靠记忆与口播维持）。Human 说得出"这块还得 explore"，系统接不住这句话。
10. **执行期涌现的东西无处安放，图会膨胀到人看不懂（case 2）。** 从首节点出发后，Loop 会不断产出路线性材料：新问题、待定的分叉、"这个深井节点比预想的大得多"、跨子树的新关联依赖。这些东西目前只有三个去处——塞进 `notes`（丢失结构、无法查询）、塞进 `decisions`（节点内嵌数组，无法跨节点共享、无法被别的节点引用）、或者直接 `add` 成 roadmap 节点（把零散发现升格为正式任务，图迅速膨胀）。三者都不对，于是 Human 与 Agent 陷入"图越大越不知道自己在哪、下一步该干什么"的细节困境。

#### 归因修正：Problem #1 不是 lost update（2026-09-10 证实）

写作时把它归因为"两个 Agent 各自基于旧快照计算父状态，后写覆盖前写——经典 lost update"。PR #27 的探针推翻了这个说法，PR #28 修完后重跑确认。

**为什么 lost update 物理上不可能**：整条写命令在整图锁内串行，读-改-写不交错；父状态由 `_sync_parent_status()` 派生，不是快照。

**真实的失败是崩溃，不是覆盖**：`os.mkdir` 被运行时 shim 包装后，目录已存在时会抛 `PermissionError` 且 `errno is None`（不是标准 `FileExistsError`）。旧代码只捕获 `FileExistsError`，等待重试循环从未执行，进程**在碰到 carrier 之前就以 exit 1 死掉**。

| 版本 | 25 writer 并发完成兄弟节点 | 子节点完成数 | 父状态 | 不变式违反 |
|---|---|---|---|---|
| PR #27 之前（只认 `FileExistsError`） | 2 × exit 0，23 × **exit 1** | 2/25 | `in_progress` | 23/25 |
| PR #28 之后（按 errno / 消息 / `errno is None` 分类） | 25 × exit 0 | 25/25 | `completed` | 0/25 |

回归防线是 `tests/test_lock_contention.py`（8 writer × 2 轮 + 串行控制例）：它断言"**没有 writer 因为拿不到锁而 exit 1**"以及"父状态与子节点一致、无残留锁目录"。锁分类一旦退回只认 `FileExistsError`，这些用例必须变红。

**这个修正的直接后果**：P2（租约）与 P3（SQLite）**不能再用"解决 lost update"当动机**——那个动机已经不成立。P3 剩下的四条正当性见 Implementation Decisions §5。

> 上述第 9、10 条来自同一件事：**本 spec 到目前为止的整图模型是静态的**——它假设路线在执行开始前已被规划完备，执行只是把它走完。真实情况是路线一边走一边长。P1 的 DAG 表达"该做什么"，没有表达"我们是如何走到这里、为什么现在是这样"。

## Solution

保留"树 = Human 主视图、carrier = 事实源、md = 只读派生视图"这条核心不变式，在其上按阶段叠加能力（P0 → P5）：

- **P0 稳定性与经济性**：不可变节点 uid、`context` / `next` 命令、输出投影与紧凑格式、稳定错误码。低风险纯增量，且是后续所有并发的地基（uid 不稳定就去搞租约，租约会挂到复用 id 上）。
- **P1 依赖层（DAG）**：在树之外加一层正交边（`blocks` / `informs` / `supersedes` / `derives-from`），`blocked` 由边推导，提供 `ready` / `critical-path` / `impact` 查询。**树仍然是人类主视图，边默认不进 md**。
- **P2 并发租约**：节点级 lease（claim / heartbeat / steal / release）+ 作用域令牌 + `--if-rev` 乐观并发，把排他单位从"整图"降到"节点"。
- **P3 carrier 演进**：新增 SQLite carrier（stdlib `sqlite3`，零新依赖）作为第三种 Roadmap carrier，用递归 CTE 算 DAG 就绪集与关键路径、用事务承载跨多行的原子更新；bundle 保留为可 diff 的导出形态。**P3 不是为了修 lost update**——那个失败模式已在锁层修掉（Problem #1 的归因修正），它剩下的四条正当性见 Implementation Decisions §5。
- **P4 跨设备**：事件流升格为事实源 + HLC 字段级合并 + OPN/git 同步，各设备物化本地视图。
- **P5 执行图（Execution Graph）**：把 Human-Agent Loop 本身建模为第二张 DAG（trace layer），处理 Problem 8 / 9 / 10。它不是把依赖图重画一遍，而是补上依赖图不承载的另一半信息：这张图是怎么变成现在这样的——每个 roadmap 节点为什么存在、过程中发现了什么、`context` 该沿哪些边给 Agent 供上下文。**树仍然是人类主视图，依赖图默认折叠，trace 图默认完全不进 md。**

同时给 Human 侧补三块：owner 列、待决问题（open question）队列、关键路径；并给 md 定三条护栏，防止视图膨胀毁掉"一眼看懂"这个卖点。

**为什么 P5 是第二张图而不是扩现有 DAG**：plan layer 要稳定（Human 主视图、要被 `ready` 遍历、要人审），trace layer 天生快速增殖且由机器产出。合成一张图会让 `ready` 查询穿过机器噪音、让 md 视图失控（直接撞 Further Notes 风险 1），并让"随口一轮对话"这种日常动作变成修改规划。两张图在存储上合一（§8.1.1），共用 uid 规则与 `E_CYCLE` 约束，概念边界再用跨图层边表达，成本远低于强行合一。

## User Stories

### 基础：正确性与身份（P0）

1. As an Agent，I want every roadmap node to carry an immutable `uid` that never changes even if sibling nodes are deleted，so that leases, history and external references cannot silently point at a recycled id。
2. As an Agent，I want the human-facing display id (`1-1-2`) to stay positional and readable，so that Human can keep saying "开始 1-3-1" without knowing about uids。
3. As an Agent，I want every command to accept either a display id or a uid，so that I never have to guess which one a previous step recorded。
4. As an Agent，I want a stable machine-readable error code (`E_NODE_NOT_FOUND` / `E_INVALID_STATUS` / `E_CYCLE` / `E_LOCKED` / `E_CONFLICT` / `E_SCOPE` / `E_BUDGET_EXCEEDED`)，so that I can branch on failure without string-matching stderr。
5. As an Agent，I want a distinct process exit code per error class，so that a wrapper script can tell "retry later" from "never retry"。
6. As an Agent，I want `--format json|jsonl|brief` on every read command，so that I can choose the cheapest representation for my context budget。
7. As an Agent，I want `--fields id,status,label` projection，so that I stop paying tokens for fields I will not read。
8. As an Agent，I want `--quiet` to suppress success chatter and emit only the requested payload，so that a batch of ten mutations costs ten small outputs instead of ten paragraphs。
9. As an Agent，I want a single `context` command that returns focus node + path + siblings + that node's decisions + the top-N ready nodes，so that I replace four round trips with one。
10. As an Agent，I want `decide --render` to record a decision and refresh the md view in one lock，so that a decision costs one process start instead of two。
11. As a skill maintainer，I want existing default output to stay unchanged，so that already-installed skills and user muscle memory do not break。
12. As a Human，I want the md section to keep rendering from the same carrier exactly as today，so that P0 is invisible to me。

### 依赖与就绪（P1）

13. As a Human，I want to say "1-4-1 必须等 1-2-3 做完"，so that cross-subtree dependencies stop living only in my head。
14. As an Agent，I want an `edge add <from> <to> --type blocks` command，so that I can record a hard dependency between any two nodes。
15. As an Agent，I want the CLI to reject a `blocks` edge that would create a cycle with `E_CYCLE`，so that the graph can never become unschedulable。
16. As an Agent，I want `informs` and `derives-from` edges to be allowed to form cycles，so that context and provenance links are not artificially constrained。
17. As an Agent，I want `supersedes` to mark the superseded node archived rather than deleted，so that history survives a scope change。
18. As an Agent，I want `blocked` status to be **derived at read time from unfinished `blocks` in-edges and never persisted to the carrier**，so that there is exactly one source of truth (the edges) and no stale value to reconcile。
19. As an Agent，I want `blocked_reason`（the edge ids blocking a node）to be computed on that same read，so that I can explain a stall instead of just reporting it。
20. As an Agent，I want a `ready` command returning the topological ready set (pending, no unfinished `blocks`, no active lease)，so that I can pick work without Human pointing at a node。
21. As an Agent，I want `critical-path` to return the longest unfinished chain，so that I can tell Human what actually blocks completion。
22. As an Agent，I want `impact <node>` to return the downstream affected set，so that I can warn before a change ripples。
23. As a Human，I want the md view to show a short "阻塞链" list when something is blocked，so that I see why progress stopped without opening the JSON。
24. As an Agent，I want ready-set computation to be O(1) incremental (a `pending_deps` counter decremented on predecessor completion)，so that a 5,000-node roadmap stays fast。**推迟到 P3**——见下方「推迟说明：Story 24」。

#### 推迟说明：Story 24（`pending_deps` 计数器）→ P3

**决议（2026-09-11）：不在 P1 实现，推迟到 P3。**

**张力**：Story 18 把 `blocked` 定成纯派生、永不落盘，理由写得不含糊——落盘就得维护一份"重算触发点"清单（加边、删边、前驱完成、`delete`、`supersedes`、carrier 迁移…），漏一个就是静默陈旧。而 Story 24 要的 `pending_deps` 恰恰是**在前驱完成时递减的落盘计数器**，那份清单一条不少，漏起来一模一样。Further Notes 风险 5 已经把这层关系点破了：`blocked` 一旦落盘，就会与计数器、派生父状态构成三个真相源。

换句话说，这两条 Story 不能无条件下共存：要么承认"重算触发点清单"这笔代价是可以接受的（那就该回到 Story 18 重新论证），要么承认今天做的是过早优化。本决议取后者。

**为什么是过早优化**：5000 节点按 `blocks` 边算一次就绪集是 O(V+E)，毫秒级；roadmap 的写命令今天就要 load 整图，多这一趟读不改变数量级。真到 5000 节点时瓶颈是"每次读都 load 整图 JSON"——那正是 P3（SQLite carrier）四条正当性之一（Implementation Decisions §5 第 3 条），与本 Story 是同一件事，不该重复立项。

**未来若真要做，落点是 P3 的 carrier**：用递归 CTE 一次查询算出就绪集，而不是在今天的派生层加一台需要同步的缓存。计数器是 carrier 的实现细节，不该上升到 Roadmap 的数据模型。

**未改动**：Story 18 的"纯派生、永不落盘"语义保持不变；本次不实现任何计数器。

### 并发与所有权（P2）

25. As an Agent，I want `claim <node> --agent <id> --ttl <sec>` to take a node lease，so that two agents never execute the same node。
26. As an Agent，I want `heartbeat` to extend my lease，so that a long step is not stolen from me mid-flight。**（P2 硬前置，不是可选增强）** 默认 TTL 已定为 300s，没有心跳则任何超过 5 分钟的步骤都会在途中被回收；`claim` 与 `heartbeat` 必须同一批次交付。
27. As an Agent，I want an expired lease to be stealable，so that a crashed agent does not permanently wedge a node。
28. As an Agent，I want a fencing token on every lease，so that a zombie agent that wakes up after its lease was stolen cannot write dirty state。
29. As a parent Agent，I want to pass `--as-agent <id> --scope <node>` to a subagent，so that the subagent physically cannot write outside its assigned subtree。
30. As a subagent，I want an out-of-scope write to fail with `E_SCOPE` naming the allowed scope，so that I can correct my call instead of silently corrupting the map。
31. As an Agent，I want `--if-rev <sha>` optimistic concurrency，so that a concurrent write is reported as `E_CONFLICT` with the current revision instead of clobbering someone else's work。
32. As an Agent，I want field-level ownership (status/notes belong to the lease holder, label/scope to the planner, decisions append-only)，so that most concurrent edits never conflict at all。
33. As an Agent，I want a failed node to record `attempts` / `last_error` / `retry_backoff`，so that retries are bounded and inspectable。
34. As an Agent，I want a node that fails N times to become `blocked` and raise an open question，so that a stuck loop escalates to Human instead of spinning。
35. As a Human，I want an open question queue in the md view，so that I know exactly which decisions are waiting on me。
36. As a Human，I want an owner column in the md view，so that I can see which agent/device holds which node。
37. As an Agent，I want `exploit` nodes to carry `exit_criteria` and `explore` nodes to carry `budget`，so that "done" and "stop exploring" are checkable rather than vibe-based。

### Carrier 与跨设备（P3 / P4）

38. As a skill maintainer，I want a third Roadmap carrier backed by SQLite，so that I get transactions, indexes and recursive DAG queries without adding a dependency。
39. As a Human，I want `recommend-storage` to keep being a read-only advisory，so that no command silently migrates my fact source。
40. As a Human，I want to migrate between carriers only through an explicit command，so that I always know which artifact is the fact source。
41. As a cross-device Agent，I want the event log to be the canonical fact source，so that two devices can work offline and converge later。
42. As a cross-device Agent，I want field-level last-writer-wins ordered by HLC，so that a merge is deterministic and explainable。
43. As a Human，I want each device to keep a materialized local view，so that reads stay fast regardless of peer availability。

### 执行图与导航（P5）

49. As an Agent，I want to record a turn / finding / doubt as a **trace node** that is deliberately not a roadmap node，so that discoveries stop being forced into `notes`（结构丢失）or `decisions`（无法跨节点共享）。
50. As an Agent，I want a trace node to be promotable into a real roadmap node with a `derives-from` edge pointing back，so that an emerged task keeps its provenance and Human can ask "这个节点哪来的"。
51. As a Human，I want trace nodes to never appear in md by default，so that recording freely does not cost me my one-screen plan view。
52. As an Agent，I want `context <node>` to be **driven by that node's in-edges** rather than by tree position，so that what lands in my prompt is chosen by relevance instead of by adjacency。
53. As an Agent，I want a node with several in-edges to have a determinate **mainline**（first edge in）while the others contribute context，so that display order, step ordering and role inheritance are reproducible instead of being recomputed geometrically。
54. As an Agent，I want `why <node>` to return the causal chain that produced this node，so that I can answer "我们为什么会在这里" without replaying the whole transcript。
55. As a Human，I want `whereami` to return current focus + mainline path to root + open branches，so that coming back after a day costs one command instead of a re-read。
56. As an Agent，I want an `explore` node to carry a `budget` **in structural units**（max children / max rounds，不是 token 预算）and an `exploit` node to carry `exit_criteria`，so that "还存在未知" is expressible at planning time and mechanically checkable at execution time（Problem 9）。
57. As an Agent，I want explore output to become the node's children through `promote`，so that the map grows from evidence rather than from guesswork。
58. As a Human，I want Agents to be able to **append** freely but never to **rewrite** my plan without me，so that autonomy does not quietly become plan drift。
59. As an Agent，I want my promotions to be reviewable proposals rather than silent mutations of the plan，so that Human can batch-accept what I found while still owning the map。
60. As a cross-device Agent，I want trace nodes to carry device / agent / session provenance from birth，so that when P4 lands the merge has something deterministic to merge on。
61. As a skill maintainer，I want trace nodes and plan nodes to live in the same carrier and the same edge table with a `layer` field，so that cross-layer `derives-from` edges have their referential integrity enforced in exactly one place（§8.1.1）。
62. As a skill maintainer，I want every traversal predicate（`ready` / `critical-path` / `impact` / `tree` / md render）to filter `layer == 'plan'` by construction，so that sharing one table cannot leak trace noise into scheduling or the human view（Further Notes 风险 8）。

### 视图与护栏（贯穿）

44. As a Human，I want the md main view to stay tree + top-3 ready + open questions，so that it still fits on one screen。
45. As a Human，I want the dependency graph to appear only in a collapsed section or a separate `--deps` output，so that I am not forced to read a DAG to see progress。
46. As a Human，I want every new field to be excluded from md by default，so that the view grows only by explicit decision。
47. As a Human，I want a `<!-- HUMAN_NOTES -->` protected region that survives `render`，so that my annotations are not erased by the next write。
48. As a skill maintainer，I want the two carriers to agree on `remove-decision` semantics (retract-and-keep, not physical delete)，so that one command does not mean two things。

## Implementation Decisions

### 1. 节点身份：显示 id 与 uid 分离（P0，先于一切并发改动）

- 每个节点新增不可变 `uid`（ULID 或等价的时序唯一串），一经生成永不变更、永不复用。
- 显示 id 维持现有位置路径（`1-1-2`），Human 说"开始 1-3-1"的交互方式不变。
- 子节点序号计数器改为**单调递增**（挂在当前节点上），删除尾部子节点不再回收序号——这是最低成本的防复用补丁，即使还没引入 uid 也应先做。
- 所有跨系统引用（ticket、ADR、租约、事件、同步对端）一律用 uid；显示 id 只用于人机对话与 md 渲染。
- 迁移：读取旧 carrier 时为存量节点补 uid；无 uid 的老 roadmap 视为 v1，写入时升级为 v2 schema。

### 2. CLI 契约：错误码、输出格式、批量（P0）

- 稳定错误码 + 退出码映射：`E_NODE_NOT_FOUND`、`E_INVALID_STATUS`、`E_CYCLE`、`E_LOCKED`、`E_CONFLICT`、`E_SCOPE`、`E_STORAGE`、`E_BUDGET_EXCEEDED`。**机制已落地**（PR #34）：`roadmap.py` 有 `RoadmapError` 基类、`ERROR_EXIT_CODES` 表与 `exit_code_for`，P0 的其余码补进**同一张表**，不另起机制。

  当前实际（`ERROR_EXIT_CODES` 的内容，2026-09-11 核对）：

  | 退出码 | 含义 | 从哪来 |
  | --- | --- | --- |
  | 0 | 成功 | — |
  | 1 | 通用失败 | 基类 `E_ROADMAP`；未登记的码走 `exit_code_for` 的兜底；所有非 `RoadmapError` 异常（`BundleError` / `FileNotFoundError` / `ValueError` / JSON 解析失败）也是 1 |
  | 2 | 锁超时 | `RoadmapLockTimeout`，**在 CLI 里硬编码**（`sys.exit(2)`）——它继承 `TimeoutError` 而非 `RoadmapError`，没有 `code`，`exit_code_for` 只会给它 1，所以它进不了这张表 |
  | 3 | `E_BUDGET_EXCEEDED` | case 1（§8.5），P0 错误码表里登记的第一个码 |

  表里现在只有 `E_ROADMAP` 与 `E_BUDGET_EXCEEDED` 两条。补其余七个码时，每个码要同时配一条断言退出码的用例（Testing §错误码）——只加码不锁退出码，等于把今天 Problem #7 的缺口再复制一遍。
- 新增 `--format json|jsonl|brief`、`--fields`、`--quiet`，**默认值保持现状**，避免破坏已安装技能与既有文档。
- 新增 `context` 命令：一次返回 focus + path + siblings + focus decisions + top-N ready（默认 N=3），这是 token 性价比最高的一条。
- 新增 `next`（等价于 `ready --limit 1 --brief`）与 `ready`。
- `decide --render` / `update --render` 合并写入与渲染，共用同一把锁。

### 3. 依赖层：树保留给 Human，边服务于调度（P1）

边类型与语义：

| 类型 | 语义 | 参与阻塞 | 允许成环 |
| --- | --- | --- | --- |
| `blocks` | 硬依赖，前驱完成才就绪 | 是 | 否（拒绝并报 `E_CYCLE`） |
| `informs` | 软依赖，提供上下文 | 否 | 是 |
| `supersedes` | 取代另一节点，后继标 archived | 否 | 否 |
| `derives-from` | 来源追溯（ADR、grilling 结论） | 否 | 是 |

- `blocked` / `blocked_reason` 改为**纯派生（读取时计算，永不落盘）**：唯一权威是 `blocks` 边。读命令与 md 渲染在返回时计算二者，carrier 的 `status` 字段不写入 `blocked`。
  - 连带：`--status blocked` 从 `add` / `update` 的可设枚举中移除，人工设置返回 `E_INVALID_STATUS`。否则"人设 blocked"与"派生 blocked"会互相矛盾，等于又造一个真相源。
  - 与既有范式一致：父状态已由 `_sync_parent_status()` 派生，本决策不引入第二种状态来源。
  - 放弃落盘的理由：落盘必须维护一份"重算触发点"清单（加边、删边、前驱完成、`delete`、`supersedes`、carrier 迁移…），漏一个就是静默陈旧——与 `remove-decision` 在两个 carrier 上的语义漂移属同一类缺陷，本仓库已经犯过一次。
  - 代价可接受：没有计数器时，就绪判定与 `blocked` 都按 `blocks` 边实时算一遍，成本 O(V+E)；而 roadmap 的写命令今天就要 load 整图，这条读路径不改变数量级。真需要优化时落点应是 P3 的 carrier（递归 CTE 一次算出就绪集），而不是在派生层加一台要同步的 cache——见「推迟说明：Story 24」（User Stories 节）。
  - 跨设备（P4）若需要离线展示"上次已知 blocked"，落**本地物化视图**，不进共享事实源。
- 就绪判定：`status == pending` 且**没有未完成的 `blocks` 前驱**且无有效租约。判定按边实时计算（O(V+E)），不依赖任何计数器——见「推迟说明：Story 24」（User Stories 节）。
- 与既有技能链的接缝保持不变：`zj-to-tickets` 导出的 blocking edges 映射为 `blocks` 边，`informs` 留给 wayfinder 的上下文关系。

### 4. 并发：节点租约取代整图锁（P2）

租约记录（概念形态，不是最终 schema）：

```json
{
  "node_uid": "01J...",
  "agent_id": "agent-7",
  "device_id": "win-rog",
  "fencing_token": 41,
  "claimed_at": "2026-09-09T01:00:00Z",
  "heartbeat_at": "2026-09-09T01:05:00Z",
  "expires_at": "2026-09-09T01:10:00Z"
}
```

（样例按已决策参数：TTL 300s，01:05 的心跳把 `expires_at` 从 01:05 推到 01:10。）

- `claim` / `heartbeat` / `release` / `steal`；**默认 TTL 300s + 心跳周期 60s（已决策 2026-09-10，zj）**；**已过期**租约可被 `steal`，并递增 fencing token 使旧持有者后续写入失败。
  - **TTL 与心跳是一组参数，必须成对实现**：TTL 300s 单独存在会在 5 分钟后回收仍在正常执行的节点。心跳周期 60s（TTL 的 1/5，可容忍 4 次连续心跳丢失），续约动作幂等：`expires_at = now + TTL`。
  - `steal` 的作用域限定为"租约已过期（`now > expires_at`）"。**TTL 未到期时 Agent 侧永不抢占（已决策 2026-09-10，zj）**；唯一例外是 Human 显式 `release --force`，且必须写入事件日志。
  - fencing token 与 `steal` 是两件事：token 用于让**已过期或被回收**的旧持有者写入失败（防僵尸写），无论是否支持提前抢占都需要它，不是 steal 的附属品。
- 作用域令牌：`--as-agent <id> --scope <node_uid>`，越界写返回 `E_SCOPE`；subagent 默认无 scope（只读）。
- 乐观并发：`--if-rev <sha>`（沿用 bundle 已有的 canonical sha256 基础设施），冲突返回 `E_CONFLICT` + 当前 rev，由 Agent 重读重试。
- 字段级所有权：status / notes 归租约持有者，label / scope 归 planner，decisions 只追加不覆盖。
- 失败语义：`attempts` 递增、`last_error` 记录、`retry_backoff` 退避；超过阈值转 `blocked` 并挂 open question。

### 5. Carrier 演进：SQLite 优先于"自研事件流"（P3）

- 新增第三种 Roadmap carrier（SQLite），与 single-file JSON、Roadmap bundle 并列，由同一套 adapter 契约承载。
- 选择理由：`sqlite3` 属标准库，**零新依赖**；WAL 支持多读一写；递归 CTE 天然表达 DAG 就绪集、关键路径、影响集；history / decisions / edges / leases 各归一表。
- **但"用事务解决 lost update"不再是理由**——那个失败模式已由 PR #27 / #28 在锁层修掉。SQLite 剩下的正当性只有四条，实施与评审时不要拿已不成立的理由来论证它：
  1. **长事务**：一次写涉及多个对象（父状态派生 + 边 + 事件日志）时，JSON carrier 只能整图重写；SQLite 可以在一个事务里改多行并保持原子。
  2. **跨设备（P4 的前提）**：字段级 HLC 合并需要按行、按字段的读写粒度，整图反序列化做不到。
  3. **5000 节点读放大**：`tree` / `impact` 今天要 load 整图再过滤，规模上去后每次读都是全量。
  4. **DAG 递归查询**：就绪集、关键路径、影响集本质是递归遍历；递归 CTE 一次查询完成，应用层要自己写递归并维护 visited 集合。
- 决策：先做 SQLite，而不是先把事件流升格为主事实源。事件流是 P4 跨设备的前提，但在单设备阶段它只会增加读放大而没有收益。
- `recommend-storage` 扩展一个 `consider-sqlite` 建议值；**仍然不自动迁移**，迁移只走显式命令。
- bundle 保留为"纯文本可 diff"的导出/归档形态，不作为并发主力。

### 6. 视图护栏（贯穿，防止卖点自我毁灭）

1. md 主视图永远是：树 + 就绪前 3 个 + 待决问题；依赖图只在折叠区或 `--deps` 输出中出现。
2. 任何新增字段默认不进 md，只进 carrier。
3. 每加一个视图元素先回答："这一行能让 Human 少问一句吗？"
4. 新增 `<!-- HUMAN_NOTES -->` 保护区，render 时原样保留。

### 7. 术语与既有约定

- 新概念命名为 **Node lease**（节点租约），**不叫 Work Item**——`ZJ-CONTEXT.md` 中 Work Item 已专属于激活协调平面，且明确"避免与 roadmap Node 混用"。
- 按 ADR 0002 Rule 3，合并前先更新 `ZJ-CONTEXT.md`：新增 Node lease、Ready set、Blocking edge、Open question 等术语条目。
- `zj-wayfinder` / `zj-to-tickets` 的对外契约不变：wayfinder 规划 → to-tickets 导出带阻塞边的票 → roadmap 落成节点与边。

### 8. 执行图：第二张 DAG 与上下文供给（P5）

> **本篇只登记方向与边界。** 执行图已另起独立 spec：`docs/plans/zj-roadmap-execution-graph.md`（骨架 #44 → schema #45 → 命令 #46 → 权限与测试 #47）。本节是那篇的上游与权威，本节之外不再重复论证；那篇除引用本节结论外不重述本节正文。

问题 9 / 10 的共同结构是：**路线在执行开始前并不完备，它是 Loop 的沉淀物**。借鉴 `chenxiachan/thoughtDAG` 的思路处理它，但只移植三原则、改写第四条。

#### 8.1 分层：plan layer 与 trace layer 是两张图，不是一张

| | plan layer（现有） | trace layer（P5 新增） |
|---|---|---|
| 节点是什么 | roadmap node（一件待做的事） | turn / finding / doubt / decision / attempt / artifact（一次已经发生的事） |
| 边的语义 | 调度依赖（`blocks` 等） | 上下文继承与因果（`mainline` / `reference` / `derives-from` / `prompted-by`） |
| 谁产出 | Human 与 planner | Agent 在日常执行中自动追加 |
| 稳定性 | 要稳定、要人审、要能被 `ready` 遍历 | 天生快速增殖，允许噪音 |
| md 默认可见 | 是 | **否**（仅当被 plan node 引用时才以摘要出现） |

**判别式（唯一口径）**：这条信息需要被调度吗？需要 → plan layer；不需要，只用于解释"怎么走到这里"或给下一步供上下文 → trace layer。含糊时按 trace 处理，因为它便宜且可逆。

**为什么不合图**：合图会让 `ready` 遍历机器噪音、让每句随口的对话都变成对规划的修改，并撞上 Further Notes 风险 1（视图膨胀是头号风险）。**两张图在概念上分离，在存储上合一**（详见 §8.1.1）：同一 carrier、同一张节点表、同一张边表，只靠 `layer` 字段区分；连接两张图的仍是跨图层边（trace → plan 的 `derives-from`、plan → trace 的 `prompted-by`）。

#### 8.1.1 共享 carrier 与边表（已决策 2026-09-10，zj）

- **共享什么**：uid 生成与不可变规则、`E_CYCLE` 约束、迁移路径、carrier adapter 契约、事件日志。节点集合多一列 / 字段 `layer: plan|trace`；边集合不加列——边的层级由两端节点的 `layer` 推出。
- **"表"这个词在 P3 之前也成立**：JSON single-file / bundle carrier 上是同一份文件里的同一个 `nodes` 集合与同一个 `edges` 集合，SQLite carrier 落地后是同一张 `nodes` 表与同一张 `edges` 表。共享决策与 carrier 选型无关，先落在 JSON 上照样生效。
- **为什么共享而不是独立表 / 独立 carrier**：跨图层 `derives-from` 边的参照完整性必须在一处维护。两个 carrier 各自保证自身完整性、却无法保证跨 carrier 引用有效，正是 `remove-decision` 在 bundle 与 single-file 上语义漂移的同一类缺陷（Further Notes 风险 2）。
- **代价（必须显式承担，不是附带条款）**：所有遍历谓词都要带 `layer == 'plan'`——`ready`、`critical-path`、`impact`、`tree`、md 渲染。共享表把"忘记过滤"的后果从"跨 carrier 同步时才发现"变成"当场把 trace 泄进调度与视图"。因此 `layer` 是节点必填字段（§8.3），且 Testing 对每个遍历命令各有一条"trace 存在时输出不变"的负向用例（Further Notes 风险 8）。

#### 8.2 从 thoughtDAG 移植：三条照搬，一条必须改写

| thoughtDAG 原则 | 处置 |
|---|---|
| **Wires are the context** — 边决定下一步看到什么，而不是装饰或路由 | 照搬。直接落地为 Story 52：`context` 从 tree-shaped 升级为 edge-driven |
| **The graph is acyclic. You are the loop.** — 数据无环，循环由人的反复迭代构成，不在图内建环 | 照搬。复用现有 `E_CYCLE`；Human-Agent Loop 的"闭环"表现为新增节点，不表现为环 |
| **first edge in 决定 mainline** — 多父节点挂在它被续接的那个父节点下 | 照搬（Story 53）。给布局、步骤顺序与角色继承一个确定性答案，避免每次几何重算产生不同结果 |
| **No autonomous agent redraws your graph** | **不能直接移植，必须改写**——见下 |

**冲突点**：这条与 Story 20（Agent 不点名也能取活）正面矛盾。全盘接受它等于放弃 roadmap-driven 的核心价值；完全无视它则会得到"Agent 悄悄改规划"。本 spec 的改写版本是**按写权限分层，而不是按参与者一刀切**：

- **追加（append）**：Agent 在 trace layer 完全自主；在 plan layer 只能产出 **proposal**——`promote` 的默认行为就是 proposal，不需要 `--propose` 标志（已决策 2026-09-10，zj），由 Human `promote --accept` 后才成为正式节点（Story 58 / 59、§8.4）。
- **改写（rewrite）**：改已有 roadmap 节点的语义、`delete`、`supersedes`、再加依赖边——保留给 Human。Agent 遇到"这条路线不成立"只能记 trace + 挂 open question，不能自己改图。

一句话：**Agent 拥有它的过程记录，Human 拥有地图。**

#### 8.3 trace layer 的最小 schema

**不存在第二张表**：plan 节点与 trace 节点写入同一 carrier 的同一张节点表，`layer: plan|trace` 是必填字段（§8.1.1）。差异只有 `layer` 与 `kind`，uid 规则、`E_CYCLE`、迁移路径完全共用；边表同样共用，边的层级由两端节点推出。

节点 kind（trace）：`turn`（一次 Human-Agent 往来）/ `finding`（发现）/ `doubt`（待定分叉）/ `attempt`（一次尝试与其结果）/ `artifact`（产出物指针）。plan 节点的 `kind` 沿用现有语义（可空）。
共同字段：`layer`、`kind`、`uid`、`body`、`created_at`、`agent_id`、`device_id`、`session_ref`、（可选）`compressed_from: [uid]`——用于把一条长链压成 higher conclusion，对应 thoughtDAG 的 "merge nodes into a higher conclusion"。

边：

| 类型 | 语义 | 跨层 | 允许成环 |
|---|---|---|---|
| `mainline` | 第一条入边，决定 mainline parent 与延续关系 | 否（trace 内或 plan 子树内） | 否 |
| `reference` | 并入上下文，不改变 mainline 归属 | 可 | 是 |
| `derives-from` | trace → plan，追溯一个 roadmap 节点为什么存在 | **是** | 否 |
| `prompted-by` | plan → trace，记录这次探索是被哪个节点触发的 | **是** | 否 |

`derives-from` / `prompted-by` 是连接两张图的全部接缝，二者都必须是单向且不成环的，否则 loop 会渗进数据结构。

**存量 `node.decisions` 不迁移进 trace layer（已决策 2026-09-10，zj）**：`node.decisions` 继续作为"该节点的结论摘要"服务于 md 与 Human，trace layer 承载完整过程。二者是**摘要与明细**的关系，并存不是重复。若迁移，md 渲染会失去它今天唯一的 decisions 来源，而 trace 又明确不进 md，等于让 Human 净失去这部分视野。连带三条约束：

- `promote` 不回写 `node.decisions`——trace 的 `body` 是过程，promote 只创建 plan 节点与 `derives-from` 边；结论要不要进摘要由 Human 决定（`decide` 命令）。
- `context --include decisions` 读的仍是 `node.decisions`，不是 trace；读 trace 另有 `--include trace`。
- 迁移器不做 `decisions → trace` 的批量转换，老 carrier 升级后 `decisions` 数组原样保留。

#### 8.4 命令（最小集）

- `trace add <kind> --parent <uid> [--body ...] [--session-ref ...]`：Agent 可写（append 权限）。
- `promote <trace_uid> --under <node_uid> --label "..."`：trace → plan。**默认产出 proposal 并挂 open question（已决策 2026-09-10，zj，取保守方案）**；`--accept` 由 Human 执行后才落正式节点，并自动写 `derives-from` 边。接受动作统一走 `promote --accept <trace_uid>`（要接受多条就在同一把锁内串行执行，不新增批量命令）。不采用"默认直接生效 + Human 事后 reject"：那样 Agent 的一次误判会永久改变地图，正是 case 2 要消除的不确定性；而 proposal 让 Human 挑着接受，日常开销并不高。
- `context <node>`：**替换** Story 9 的 tree-shaped 实现，改为沿 in-edges 收集——默认只带 mainline + 显式 `reference`，可通过 `--include deps|trace|decisions` 增量加宽。这是"给 Agent 更少无关上下文"这一目标的落地，也直接决定 token 成本。
- `why <node>`：回溯 `derives-from` 链，返回"为什么存在"。
- `whereami`：focus + mainline path to root + 未闭合分支数。
- `prune <edge_uid>`：删除一条 `reference` 边即把该路径移出上下文，节点保留在图上但不再参与 `context`。对应 thoughtDAG 的 "delete one edge, get a different answer"，也是 case 2 里"发现走偏后不用删历史就能回到干净上下文"的手段。

#### 8.5 case 1：让"这里有未知"在规划期可写

P5 之前先补一个比它更基础、成本更低的洞——Problem 9 其实不需要新图，只需要给既有 `mode` 字段长出牙齿：

- `explore` 节点新增 `budget`，**单位是结构单位而不是 token 预算（已决策 2026-09-10，zj）**：

  ```json
  { "max_children": 3, "max_rounds": 2 }
  ```

  两者都是结构量，任一触顶即拒绝再派生子节点并挂 open question，返回 `E_BUDGET_EXCEEDED`。`max_children` 限制这条探索最多长出几个子节点，`max_rounds` 限制它最多被重访几轮；可只给一个，缺失的子项视为不限。
  不用 token 当单位的理由：token 不可跨模型比较，也无法在 planning 期预估，而结构单位既能写进规划、又能在执行期机械校验（子节点数与轮次都是 carrier 里已有的计数）。控制 token 成本另有 §2 的 `--fields` / `--format` 与 §8.4 的 edge-driven `context`，不该由 `budget` 承担。
- `exploit` 节点新增 `exit_criteria`（可检查的完成判据），用于 Story 37 的"done 不是 vibe-based"。
- explore 的产出经 `promote` 落成子节点，而不是规划人凭空预判。**case 1 不豁免 §8.4 的 proposal 规则**：探索产出同样是 proposal，Human `--accept` 后才成为子节点。
  - 连带一个必须明确的计数口径：`max_children` 只计**已被接受的正式子节点**，proposal 不占额度。否则一轮探索里 Agent 先提了 3 条 proposal 就把额度用光，Human 还没审就没了空间——budget 约束的是地图，不是 Agent 的嘴。

注意这不是造新概念：`mode` 字段、`add --mode` CLI 参数、`[X+]`/`[Y+]` 渲染图标均已存在（`roadmap.py:32-37`、`roadmap_cli.py:139`），缺的只是 budget / exit_criteria 与 promote 通道。因此 **case 1 应先于 P5 落地，且不依赖 P5 的任何新结构**。

**状态：§8.5 的 budget / exit_criteria 部分已落地**（PR #34，2026-09-10）。实施时把四条口径钉死，否则"文档声称"与"CLI 实际行为"会各说一套：

| 口径 | 实现约定 |
|---|---|
| 什么是"开工" | 任何进入 `in_progress` 的转换（`pending` / `completed` → `in_progress`）；第一次写 `rounds: 1`。`init` 出来的根节点已经是 `in_progress`，按**已开工一轮**计——否则 `max_rounds: 1` 会被解释成"还能再开工一次" |
| 改小预算是否追溯 | **不追溯**。已有 3 个子节点时设 `max_children: 2` 是允许的，只约束之后的新增 |
| `exit_criteria` 谁判定 | CLI **只存不判**。它无法判定自然语言，且未满足的判据不阻断 `update --status completed`。"done 不是 vibe-based" 靠 Human/Agent 对照这份清单，不靠机器假装能读懂 |
| 触顶是否挂 open question | **本切片不挂**。只做拒绝 + `E_BUDGET_EXCEEDED`（退出码 3，该码是 P0 错误码表登记的第一个码）。open question 队列是 Story 35 / P2 的能力，届时在此处补挂 |

另外两条实施约束：字段默认不进 md（§6 护栏 2）；两个 carrier（single-file 与 bundle）复用 `roadmap.py` 里同一份 `check_child_budget` / `count_round_start`，不允许各自实现一遍——两类 carrier 对同一语义各算一套，正是 `remove-decision` 翻过一次的车（Further Notes 风险 2）。契约测试在 `tests/test_budget.py`（15 项，两个 carrier 各跑一遍）。

`promote` 通道（explore 产出落成子节点）**不在本切片内**：它依赖 §8.3 的 trace layer 与 §8.4 的 proposal 语义，属 P5。

#### 8.6 case 2：膨胀的解法是投影，不是更多图

case 2 的症状（"图膨胀后人不知道自己在哪"）容易被误读成"图不够用"，于是解法变成加更多图——那会加重病情。真正的解法是**从同一 carrier 派生不同的投影**：

- Human 看树（默认）+ 折叠的依赖图（`--deps`）+ 仅三条 ready；trace 永不进 md。
- Agent 看 edge-driven `context`，拿到的是与该步相关的一组边而不是整棵树。
- 两者同源，不存在第二份真相——这与 Problem 3（carrier 是事实源、md 是只读派生视图）是同一条不变式。

护栏：任何把 trace 内容加进 md 的提议必须先回答 §6 的第 3 问（"这一行能让 Human 少问一句吗？"）。默认答案是不加。

## Testing Decisions

### 测试缝（seams）

**建议只用一个主缝：CLI 契约（命令参数 + stdout/stderr + 退出码）。** 所有行为测试都从命令行进入，不直接断言内部函数——这样 SQLite carrier 换进来时，同一套契约测试可以整组复用。

- **主缝**：CLI 命令层。输入确定 → 输出确定，天然黑盒，与技能现有设计一致。
- **次缝（不新增，复用现有）**：carrier adapter（single / bundle / sqlite 实现同一组方法），用同一套契约测试参数化跑三遍。这不是新缝，是现有 bundle adapter 已经打开的缝。
- 不引入 mock 层、不做进程内 API 测试。

### 什么算好测试

- 只测外部可观测行为：给了什么命令参数、返回了什么输出、落盘后 carrier 处于什么状态。
- 不测实现细节：不断言内部调用顺序、不断言某个私有方法被调用。
- 并发断言用**多进程真实调用**（同时起 N 个 CLI 进程写兄弟节点），结果是"父子状态最终一致"而不是"某个锁被持有"。
- 每个失败路径断言错误码 + 退出码，不断言错误文案。

### 要覆盖的模块与行为

- 节点身份：删除尾部子节点后新节点 uid 与显示 id 均不复用；老 roadmap 迁移后 uid 补齐。
- 输出契约：`--format` / `--fields` / `--quiet` 三种组合的字节级输出；`context` 命令等价于四次旧调用的组合结果。
- 错误码：每个码至少一条用例，断言退出码。
- DAG：`blocks` 成环被拒；`informs` 成环被允许；前驱全部完成后目标进入 ready（按边实时判定，无计数器）；加边 / 删边后 `blocked` 与 `blocked_reason` 在同一次读命令内立即反映，且**断言 carrier 的 `status` 从未被写成 `blocked`**；`--status blocked` 返回 `E_INVALID_STATUS` + 对应退出码。
- 并发：N 个 writer 并发完成兄弟节点 → **全部退出 0**（2 是合法超时，**1 是崩溃，必须一个都没有**）；无 lost completion、父状态与子节点一致、无残留锁目录；外加一条**串行控制例**——控制例都失败说明并发用例在测别的东西。已落地：`tests/test_lock_contention.py`（8 writer × 2 轮）。这条同时是 Problem #1 归因的回归防线：锁分类退回只认 `FileExistsError` 时它必须红。租约过期后可 steal；持旧 fencing token 的写入失败；越界写返回 `E_SCOPE`；冲突写返回 `E_CONFLICT`。
- 租约参数：`claim` 后 `expires_at == claimed_at + 300s`；`heartbeat` 把 `expires_at` 推到 `now + 300s`（幂等，重复调用不累加）；**`expires_at` 未到期时任何 Agent 侧 `steal` 均失败**（断言存在这样的负向用例，不只是"过期能抢"）；`release --force` 成功并落事件日志。
- 崩溃恢复：持有者静默（不心跳）后，节点在 **TTL + 一个心跳周期 = 360s** 内可被他人接管；断言恢复延迟上界，而不是"最终能恢复"。
- 视图护栏：render 后 md 主视图行数不超过阈值；`HUMAN_NOTES` 内容跨 render 存活；新字段默认不出现在 md。
- 执行图（P5）：`promote` 未 `--accept` 时 roadmap 节点数不变且 open question +1，断言的是"没有副作用"而不只是"命令成功"；`promote --accept` 后存在且仅存在一条 `derives-from` 边。`context` 在删除一条 `reference` 边后输出随之变化（对应 thoughtDAG 的 "delete one edge, get a different answer"，证明上下文由边而非由位置决定）。**负向用例：`trace add` 之后 md 主视图行数不变**（否则 case 2 的病会被 P5 重新制造出来）。`explore` 节点超出 `budget` 后追加子节点返回 `E_BUDGET_EXCEEDED` 与对应退出码（已落地：`tests/test_budget.py`，single-file 与 bundle 各跑一遍），而不是静默接受（至少两条：`max_children` 触顶、`max_rounds` 触顶；再加一条负向——只给其中一个子项时，另一个不设限且不报错）。`max_children` 只计已接受的子节点：连续提交满额条 proposal 后仍可继续提交，且 `promote --accept` 到额度上限后下一次接受返回 `E_BUDGET_EXCEEDED`（§8.5）。
- 共享表与层级过滤（P5）：`trace add` 之后 `ready` / `critical-path` / `tree` 的输出与之前**字节一致**（`layer` 过滤，Story 62）；删除一个已被 `promote` 引用的 trace 节点必须失败（跨图层 `derives-from` 的参照完整性落在同一张表里，因此是同表校验而不是跨 carrier 约定）。
- `decisions` 不迁移（P5）：`promote --accept` 后目标 plan 节点的 `decisions` 数组条目数不变、源 trace 节点 `body` 不变；老 carrier 升级后 `decisions` 原样保留，且 md 里 decisions 段的渲染结果不变。
- 上下文确定性（P5）：同一节点在 `mainline` / `reference` 入边顺序不同时，`context` 输出必须字节一致——非确定性输出会让 Agent 无法复现上一次的结论。

### 既有先例（prior art）

- 技能自带的 `test_roadmap.py` / `test_roadmap_bundle.py` / `test_storage_advisor.py`（unittest 风格，直接跑库层）。
- `tests/verify_real_plan_corpus.py`：只读真实 Markdown 计划语料的迁移契约测试——它的"只读 + 契约"写法是本 spec 推荐风格的先例。
- 新增测试沿用这些文件的组织方式，不引入新测试框架。

## Out of Scope

- **跨设备同步（P4）**：事件流升格、HLC 合并、OPN/git 传输不在本 spec 内，只在此登记为后续阶段。
- **可视化 dashboard**：HTML/Mermaid 全景图、进度看板。
- **与外部 issue tracker 的双向同步**：本 spec 只消费 blocking edges，不回写。
- **自动 carrier 迁移**：任何迁移都必须显式命令触发，`recommend-storage` 继续只做只读建议。
- **`zj-grilling` / `zj-wayfinder` / `zj-to-tickets` 的内部改造**：对外契约保持不变。
- **性能基准体系重写**：`benchmarks/roadmap_bundle_benchmark.py` 保留，不为本 spec 新增基准设施。
- **技能分发方式**：源技能在本仓库 `skills/codebase-docs/` 内，不走"删除重装"——那会绕开 PR 审阅与 ZJ-CONTEXT 术语同步。已确立的流程是改源 + 分支 + PR，合并后按 sha256 同步三处已安装副本（`~/.codex` / `~/.workbuddy` / `~/.claude`）。
- **P5 的执行图实现**：本 spec 只登记方向与边界（分层模型、边语义、写权限分层、最小命令集）。真正的 schema、迁移与 CLI 细节**已另起一篇** `docs/plans/zj-roadmap-execution-graph.md`，避免在一个已经有 62 条 user story 的文档里继续堆新东西。**那篇 spec 的输入约束已定三条：共享 carrier / 边表（`layer` 区分）、`promote` 默认 proposal、存量 `decisions` 不迁移。**
- **trace 的可视化**：把 trace layer 画成图（canvas / HTML / Mermaid）不在本 spec 内。它最容易消耗工作量，也最容易被砍，且对本 spec 目标（导航与上下文供给）不是必需的——`context` / `why` / `whereami` 三个命令已经覆盖导航诉求。

## Further Notes

### 风险

1. **视图膨胀是头号风险。** 这个技能的核心卖点是"Human 一眼看懂"。DAG、租约、owner、open question 全塞进 md，就会把资产变成负债。三条护栏（Implementation Decisions §6）应视为硬约束而非建议。
2. **两种 carrier 语义漂移。** 现状已有一例：bundle 的 `remove-decision` 是撤回保留历史，单文件模式是真删。加第三种 carrier 前必须先统一语义，否则漂移会三倍放大。
3. **并发先于 uid 是本末倒置。** 位置型 id 复用会让租约挂到错误的节点上，这种 bug 静默且难查。P0 的 uid 是 P2 的硬前置。
4. **术语冲突。** 见 Implementation Decisions §7：Node lease 不得命名为 Work Item。
5. **状态双重来源（已由纯派生决策规避）**。若 `blocked` 落盘，就会与 `pending_deps` 计数器（已推迟到 P3，见 Story 24）、派生父状态构成三个真相源，并需要一份"重算触发点"清单。实施时若出现"为了渲染方便把 blocked 缓存进 carrier"的冲动，应落本地物化视图而非共享事实源。
6. **租约回收的两难（已由"短 TTL + 心跳"决策化解）**。崩溃恢复延迟与误抢风险是一对矛盾：TTL 越长越不会误抢，但崩溃后节点僵死越久。本 spec 的解法不是加自动抢占，而是**缩短 TTL（300s）+ 心跳续约（60s）**——用续约换掉长 TTL，恢复延迟与双写风险同时下降。风险留给实施阶段的是**参数漂移**：把 TTL 调回 1800s 又不实现心跳 = 节点崩溃后卡死半小时；实现 TTL 300s 却不实现心跳 = 正常长任务每 5 分钟被回收一次。二者都比"两个都做"更糟，所以 §4 要求 `claim` 与 `heartbeat` 同批次交付，Testing 要求对过期前不可抢、心跳幂等、恢复延迟上界各有断言。

7. **P5 治疗的病，P5 自己也携带。** case 2 的症状是"图膨胀后人不知道自己在哪"，而 P5 引入了第二张天生快速增殖的图。若 trace 允许进 md、允许被 `ready` 遍历、或者 trace 节点可以不经人审就变成 roadmap 节点，那么"多记录一层、就多看一张图"会重演 case 2 的老毛病——越记录越迷路。§6 的护栏与 §8.2 的写权限分层因此不是修饰件套，是这个 feature 能否成立的前提。**判断标准很简单：trace 能自由增殖，但 md 的行数不允许随之增长。**
8. **共享 carrier / 边表把"忘记过滤 `layer`"从一个远端错误变成一个当场泄漏（§8.1.1）。** 独立表方案下，trace 泄进 `ready` 要等跨 carrier 同步才暴露；共享表下，一个漏写 `layer == 'plan'` 的查询当场就让机器噪音进入调度与 md——而 md 膨胀正是风险 1 的头号风险，两个头号风险会叠在同一个 bug 上。防线只有两条：`layer` 必填，且每个遍历命令各有一条"trace 存在时输出不变"的负向用例。**实施时若发现自己在第五遍手抄 `WHERE layer = 'plan'`，正确的动作是把它收进 carrier adapter 的默认查询，而不是继续抄。**

9. **照搬 thoughtDAG 的第四条原则会废掉 roadmap-driven 的核心价值。** "No autonomous agent redraws your graph" 适用于"画布只服务于一个人的思考"的场景；而 Story 20（Agent 不点名也能取活）恰恰是本技能的价值所在。二者必须靠"append / rewrite 分层"（§8.2）而不是靠"一刀切禁止"来调和。**若实施时被说服改成完全禁写，则本 spec 的 P2 租约、P3 并发整套对象都会失去意义——那应该是一个单独的、更保守的技能，而不是本 roadmap 的演化。**

### 待决问题（留给 Human）

- ~~**执行图是否应与 plan layer 共享同一张表**~~ **已决策 2026-09-10（zj）：共享 carrier 与边表。** 节点表多一列 `layer: plan|trace`，边表不加列（边的层级由两端节点推出）；uid 规则、`E_CYCLE`、迁移路径、adapter 契约全部共用（§8.1.1）。理由：跨图层 `derives-from` 的参照完整性必须在一处维护——两个 carrier 各自完整却无法互相校验，正是风险 2 那类缺陷。代价（遍历谓词必须带 `layer == 'plan'`）与防线见 §8.1.1 与风险 8。
- ~~**`promote` 的默认行为**~~ **已决策 2026-09-10（zj）：默认 proposal（保守方案）。** 接受动作统一为 `promote --accept <trace_uid>`；要接受多条就在同一把锁内串行，不新增批量命令。拒绝"默认直接生效 + Human 事后 reject"：一旦默认生效，Agent 的一次误判就会永久改变地图，而这正是 case 2 想消除的不确定性；proposal 让 Human 挑着接受，日常开销并不高（§8.4）。
- ~~**存量 `decisions` 是否迁移进 trace layer**~~ **已决策 2026-09-10（zj）：不迁移。** `node.decisions` 是结论摘要、trace 是过程明细，二者并存不是重复。若迁移，md 渲染会失去它今天唯一的 decisions 来源，而 trace 又明确不进 md，等于让 Human 净失去这部分视野。连带三条约束（`promote` 不回写 decisions、`context --include decisions` 仍读 `node.decisions`、迁移器不做批量转换）见 §8.3。
- ~~**`budget` 的单位**~~ **已决策 2026-09-10（zj）：结构单位**——`{ "max_children": N, "max_rounds": M }`，任一触顶返回 `E_BUDGET_EXCEEDED` 并挂 open question，可只给一个、缺失的子项视为不限（§8.5）。不用 token 预算：token 不可跨模型比较、也不可在 planning 期预估；结构单位既写得进规划也查得动（子节点数与轮次都是 carrier 已有计数）。控制 token 成本另有 §2 的 `--fields` / `--format` 与 §8.4 的 edge-driven `context`。
- **多设备 trace 合并是否在本轮处理**（P5/P4 边界待定）？Story 60 只要求 trace 节点诞生时就带 `device_id` / `agent_id` / `session_ref`  provenance，**不要求本轮实现合并**。这是 cheapest 的前置投资：provenance 事后补不回来，合并可以后来做。

- ~~**carrier 选型**~~ **已决策 2026-09-10（zj）：SQLite 先做**（`sqlite3` 属标准库，零新依赖）。事件流不升格为主事实源，它是 P4 跨设备的前提，但在单设备阶段只增加读放大。bundle 继续作为"纯文本可 diff"的导出/归档形态保留。
- ~~**`blocked` 是否落盘**~~ **已决策 2026-09-09（zj）：纯派生——读取时计算，永不落盘。** 权威是 `blocks` 边；连带改动见 Implementation Decisions §3（`--status blocked` 移出可设枚举、返回 `E_INVALID_STATUS`）。
- ~~**默认 TTL 与心跳的组合**~~ **已决策 2026-09-10（zj）：组合 B——TTL 300s + 心跳周期 60s。** 原定 1800s 被替换：它隐含"不依赖心跳续约"或"单节点任务可长达 30 分钟"两种假设之一，而 Story 26 已有 `heartbeat`，两者不能共存。备选与后果：

  | 组合 | TTL | 心跳 | 长任务被误回收 | 崩溃后恢复延迟 | 双写风险 |
  |---|---|---|---|---|---|
  | A 长 TTL、无心跳 | 1800s | 无 | 不会 | 最长 30 分钟 | 无（TTL 内绝不抢占） |
  | **B（选定）** 短 TTL + 心跳续约 | **300s** | **60s 一次** | 不会（心跳保活） | 最长 5 分钟 | 无（同样不在 TTL 内抢占） |

  B 靠心跳把恢复延迟从 30 分钟压到 5 分钟，且不引入任何双写风险，代价是每 60s 一次写（JSON carrier 上是整图重写，P3 落地 SQLite 后是单行 UPDATE，可忽略）。连带：`heartbeat` 从 Story 26 提升为 **P2 硬前置**，`claim` 与 `heartbeat` 必须同批次交付。
- ~~**是否需要"提前抢占"**~~ **已决策 2026-09-10（zj）：Agent 侧完全不做；仅保留 Human 显式 `release --force`。** 原问题问法不准确——**"过期后可抢占"本 spec 已经定了要有**（Story 27、§4），没有那个能力崩溃的 agent 会永久占住节点，没有讨论余地。真正被决策的是第三种：**TTL 未到期时，能否依据"心跳超时/人工判定持有者已死"强行抢占**。
  - 不要的理由：TTL 内持有者必然唯一，**物理上不可能双写**；而"崩溃恢复慢"这个它想解决的问题已被上一条的组合 B 消解到 5 分钟，收益归零而风险不归零。
  - 若它要的理由（记录在此，防止后人重新 open 时重复论证）：可能误抢仍存活但卡顿的持有者（GC 停顿、休眠、网络抖动），两个 agent 同时写同一节点；fencing token 只能**拒绝旧持有者后续写入**，无法撤销它已合法写入的状态与 notes，新持有者要能处理这些残留；跨设备（P4）时钟与网络不可信时误判率更高。
  - Human 侧的 `release --force` 不是"抢占的 Agent 自动化版本"：它是带审计的显式动作，必须写入事件日志，且由使用者承担误判后果。

### 与既有资产的关系

- 本 spec 是 `docs/designs/zj-wayfinder-roadmap-dual-mode.md` 的下游：那篇定义规划与跟踪的接缝，本 spec 只在跟踪侧扩展依赖与并发，接缝不变。注意该篇谈的 dual mode 是"规划 / 跟踪"两态，与 §8.5 的 `explore` / `exploit` 节点 mode 不是同一组概念——后者是单个节点内的探索性质，前者是工作流阶段。同名不同义，勿混用。
- 跨设备阶段（P4）与 ZAgenticLoop 的 OPN 消息通道存在复用可能，但本 spec 不预设该通道，保持 carrier 层可替换。
- P5 的方法来源是 [`chenxiachan/thoughtdag`](https://github.com/chenxiachan/thoughtdag)：它把 LLM/Agent 多轮会话建模为一张**以边为上下文**的可编辑无环图，主张 "The graph is acyclic. You are the loop."。本 spec 借的是它的**方法论**（边决定下一步看到什么、无环数据 + 外部闭环、first-edge-in 定主线、prune 一条边即改变上下文），而不是它的实现形态——它有画布 UI 与多 Harness 会话导入，roadmap-driven 只需要 CLI 与 carrier。二者对象的差别也决定了 §8.2 必须改写它的第四条原则：thoughtDAG 的图服务于一个人的思考，roadmap-driven 的图要服务于多 Agent 的自取活，同时保证地图不被静默改写——这两件事本来就是一对需要分开授权的动作（§8.2）。
- P5 前置依赖 P0（uid 是 trace 节点与跨图层边的前提）、P1（已有四种边与 `E_CYCLE` 基础设施）、P3（trace 快速增殖，SQLite 才撑得住）。**§8.5 的 case 1（budget / exit_criteria）是例外：它不依赖任何 P5 新结构，可以先行。**

### 落地顺序建议

case 1（§8.5，**budget / exit_criteria 部分已完成**，PR #34）→ P0 → P1 → P3 → P5。理由是：case 1 补的是既有 `mode` 字段缺失的两个属性，是本节里唯一一段"无需等待任何前置的重构就能见效"的工作；而 P5 依赖 uid、依赖边机制、也依赖 SQLite 承载快速增殖的写入量。把 P5 提前等于在位置型 id 上建第二张图，会重犯风险 3 已经警告过的本末倒置。
