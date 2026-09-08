# zj-roadmap-driven: DAG 依赖、节点租约与并发执行

> Spec 生成时间：2026-09-09 · 来源会话：zj-roadmap-driven 深度评审（性能 / token / 巧思 / 选型 + AI & Human readiness + Loop/Graph/DAG 多 Agent）
> 目标技能：`zj-roadmap-driven`（安装版位于用户技能目录，源技能位于 `skills/` bucket 之外；本次只写 spec，不改已安装技能）
> 建议 triage label：`ready-for-agent`

## Problem Statement

`zj-roadmap-driven` 现在是一台"单人手写账本"：它假设只有一个 Agent 在写、只有一棵树在长、只有 Human 在点名派活。这个假设在单会话里成立，一旦进入多 Agent（同设备并行、agent + subagent、跨设备）就会四处漏：

1. **并发写不安全。** 每个写命令都是 `load → 修改 → 整图 save`，锁是整图 mkdir 互斥（10s 超时、无 TTL、无心跳）。两个 Agent 同时完成兄弟节点时，各自基于旧快照计算父状态，后写覆盖前写——经典 lost update。
2. **只有树，没有依赖。** 父子关系之外无法表达"1-2-3 依赖 1-4-1"这类跨子树依赖。`blocked` 状态存在，但没有任何代码设置它，是个空枚举值。
3. **Agent 不会自己取活。** 没有就绪集概念，Human 不点名就没有下一步；多 Agent 场景下等于人为串行。
4. **Token 经济性差。** 所有输出一律 `indent=2` 全量 JSON，没有字段投影、没有紧凑格式、没有 quiet；一个决策要跑两次进程（`decide` + `render`）；`tree` 在单文件模式默认深度 10，一次误用就能灌进几千 token。
5. **节点 id 会复用。** 子节点序号取"最后一个 child + 1"，删掉尾部子节点后新节点拿回旧 id，租约、历史、外部引用（ticket / ADR / 设备间同步）全部会串号。
6. **Human 的视野在多 Agent 下反而变差。** md 视图里没有 owner、没有待决问题队列、没有阻塞链、没有关键路径——Agent 一多，人先瞎。
7. **错误不可程序化判断。** 只有文本 stderr + `exit 1`（锁超时才是 2），Agent 无法区分"节点不存在""状态非法""有环""有冲突"，只能靠字符串匹配或整段回贴。
8. **没有收敛判据。** `exploit` 节点没有 exit criteria，`explore` 节点没有 budget，Loop 没有终止条件。

## Solution

保留"树 = Human 主视图、carrier = 事实源、md = 只读派生视图"这条核心不变式，在其上加三层能力：

- **P0 稳定性与经济性**：不可变节点 uid、`context` / `next` 命令、输出投影与紧凑格式、稳定错误码。低风险纯增量，且是后续所有并发的地基（uid 不稳定就去搞租约，租约会挂到复用 id 上）。
- **P1 依赖层（DAG）**：在树之外加一层正交边（`blocks` / `informs` / `supersedes` / `derives-from`），`blocked` 由边推导，提供 `ready` / `critical-path` / `impact` 查询。**树仍然是人类主视图，边默认不进 md**。
- **P2 并发租约**：节点级 lease（claim / heartbeat / steal / release）+ 作用域令牌 + `--if-rev` 乐观并发，把排他单位从"整图"降到"节点"。
- **P3 carrier 演进**：新增 SQLite carrier（stdlib `sqlite3`，零新依赖）作为第三种 Roadmap carrier，用事务解决 lost update、用递归 CTE 算 DAG 就绪集与关键路径；bundle 保留为可 diff 的导出形态。
- **P4 跨设备**：事件流升格为事实源 + HLC 字段级合并 + OPN/git 同步，各设备物化本地视图。

同时给 Human 侧补三块：owner 列、待决问题（open question）队列、关键路径；并给 md 定三条护栏，防止视图膨胀毁掉"一眼看懂"这个卖点。

## User Stories

### 基础：正确性与身份（P0）

1. As an Agent，I want every roadmap node to carry an immutable `uid` that never changes even if sibling nodes are deleted，so that leases, history and external references cannot silently point at a recycled id。
2. As an Agent，I want the human-facing display id (`1-1-2`) to stay positional and readable，so that Human can keep saying "开始 1-3-1" without knowing about uids。
3. As an Agent，I want every command to accept either a display id or a uid，so that I never have to guess which one a previous step recorded。
4. As an Agent，I want a stable machine-readable error code (`E_NODE_NOT_FOUND` / `E_INVALID_STATUS` / `E_CYCLE` / `E_LOCKED` / `E_CONFLICT` / `E_SCOPE`)，so that I can branch on failure without string-matching stderr。
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
18. As an Agent，I want `blocked` status to be derived from unfinished `blocks` in-edges rather than set by hand，so that the status never contradicts the graph。
19. As an Agent，I want `blocked_reason` to list the edge ids that are blocking a node，so that I can explain a stall instead of just reporting it。
20. As an Agent，I want a `ready` command returning the topological ready set (pending, no unfinished `blocks`, no active lease)，so that I can pick work without Human pointing at a node。
21. As an Agent，I want `critical-path` to return the longest unfinished chain，so that I can tell Human what actually blocks completion。
22. As an Agent，I want `impact <node>` to return the downstream affected set，so that I can warn before a change ripples。
23. As a Human，I want the md view to show a short "阻塞链" list when something is blocked，so that I see why progress stopped without opening the JSON。
24. As an Agent，I want ready-set computation to be O(1) incremental (a `pending_deps` counter decremented on predecessor completion)，so that a 5,000-node roadmap stays fast。

### 并发与所有权（P2）

25. As an Agent，I want `claim <node> --agent <id> --ttl <sec>` to take a node lease，so that two agents never execute the same node。
26. As an Agent，I want `heartbeat` to extend my lease，so that a long step is not stolen from me mid-flight。
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

- 稳定错误码 + 退出码映射：`E_NODE_NOT_FOUND`、`E_INVALID_STATUS`、`E_CYCLE`、`E_LOCKED`、`E_CONFLICT`、`E_SCOPE`、`E_STORAGE`。
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

- `blocked` 改为**推导状态**：在写事务内由未完成的 `blocks` 入边计算，并写入 `blocked_reason`（边 id 列表）；边被移除或前驱完成时重算。
- 就绪判定：`status == pending` 且 `pending_deps == 0` 且无有效租约。`pending_deps` 是增量计数器，前驱完成时递减，O(1)。
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
  "heartbeat_at": "2026-09-09T01:12:00Z",
  "expires_at": "2026-09-09T01:30:00Z"
}
```

- `claim` / `heartbeat` / `release` / `steal`；默认 TTL 1800s；过期租约可被 `steal`，并递增 fencing token 使旧持有者后续写入失败。
- 作用域令牌：`--as-agent <id> --scope <node_uid>`，越界写返回 `E_SCOPE`；subagent 默认无 scope（只读）。
- 乐观并发：`--if-rev <sha>`（沿用 bundle 已有的 canonical sha256 基础设施），冲突返回 `E_CONFLICT` + 当前 rev，由 Agent 重读重试。
- 字段级所有权：status / notes 归租约持有者，label / scope 归 planner，decisions 只追加不覆盖。
- 失败语义：`attempts` 递增、`last_error` 记录、`retry_backoff` 退避；超过阈值转 `blocked` 并挂 open question。

### 5. Carrier 演进：SQLite 优先于"自研事件流"（P3）

- 新增第三种 Roadmap carrier（SQLite），与 single-file JSON、Roadmap bundle 并列，由同一套 adapter 契约承载。
- 选择理由：`sqlite3` 属标准库，**零新依赖**；WAL 支持多读一写；事务一次性解决 lost update；递归 CTE 天然表达 DAG 就绪集、关键路径、影响集；history / decisions / edges / leases 各归一表。
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
- DAG：`blocks` 成环被拒；`informs` 成环被允许；前驱完成后 `pending_deps` 归零且目标进入 ready；`blocked_reason` 随边变化重算。
- 并发：两进程并发完成兄弟节点 → 父状态最终一致（无 lost update）；租约过期后可 steal；持旧 fencing token 的写入失败；越界写返回 `E_SCOPE`；冲突写返回 `E_CONFLICT`。
- 视图护栏：render 后 md 主视图行数不超过阈值；`HUMAN_NOTES` 内容跨 render 存活；新字段默认不出现在 md。

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
- **已安装技能文件的修改**：本 spec 不落代码改动；实施走技能的"删除重装"流程。

## Further Notes

### 风险

1. **视图膨胀是头号风险。** 这个技能的核心卖点是"Human 一眼看懂"。DAG、租约、owner、open question 全塞进 md，就会把资产变成负债。三条护栏（Implementation Decisions §6）应视为硬约束而非建议。
2. **两种 carrier 语义漂移。** 现状已有一例：bundle 的 `remove-decision` 是撤回保留历史，单文件模式是真删。加第三种 carrier 前必须先统一语义，否则漂移会三倍放大。
3. **并发先于 uid 是本末倒置。** 位置型 id 复用会让租约挂到错误的节点上，这种 bug 静默且难查。P0 的 uid 是 P2 的硬前置。
4. **术语冲突。** 见 Implementation Decisions §7：Node lease 不得命名为 Work Item。

### 待决问题（留给 Human）

- **carrier 选型**：本 spec 选 SQLite（零依赖、事务、递归 CTE）。替代方案是"事件流为主 + 物化快照"，好处是纯文本可 diff、天然适合跨设备，代价是读放大与更复杂的实现。是否接受 SQLite？
- **`blocked` 是否落盘**：本 spec 选"事务内推导并写入 status + blocked_reason"，好处是与现有状态机兼容；替代方案是"读取时计算、永不落盘"，好处是无陈旧风险。
- **默认 TTL**：1800s 是否合适，是否需要按 mode 区分（explore 更长）。
- **是否需要 `steal`**：允许抢占能救活崩掉的租约，也引入误抢风险；是否只在同 device 内允许？

### 与既有资产的关系

- 本 spec 是 `docs/designs/zj-wayfinder-roadmap-dual-mode.md` 的下游：那篇定义规划与跟踪的接缝，本 spec 只在跟踪侧扩展依赖与并发，接缝不变。
- 跨设备阶段（P4）与 ZAgenticLoop 的 OPN 消息通道存在复用可能，但本 spec 不预设该通道，保持 carrier 层可替换。
