# Roadmap 并发与依赖模型（zj-roadmap-driven）

`doc-kind: design`
`authority: primary`
`authority-id: design.roadmap-concurrency-model`

> Bounded question: 多 Agent 并发写、跨子树依赖、以及跨 carrier 扩展读，zj-roadmap-driven 分别靠什么设计保证安全与一致？
> 来源 spec：`docs/plans/zj-roadmap-dag-concurrency.md`（已于 2026-09-16 抽取至本 designs 后从仓库删除，原稿见 git 历史 `929b4ab^`）。本文提炼权威结论与决策理由，完整 62 条 user story 与论证以 git 历史中的原 plan 为准。

## 核心不变式（一切阶段的地基）

> **树 = Human 主视图；carrier = 事实源；md = 只读派生视图。**

任何新能力都在这条不变式之上叠加，不得推翻：
- 边（依赖 / 上下文）默认不进 md，只服务于调度或 Agent 上下文。
- 所有遍历谓词（`ready` / `critical-path` / `impact` / `tree` / md 渲染）按构造过滤 `layer == 'plan'`，共享表不能把 trace 噪音泄进调度或视图。
- 视图护栏是硬约束，不是建议：md 主视图永远是「树 + 就绪前 3 + 待决问题」；任何新字段默认不进 md；每加一个视图元素先答「这一行能让 Human 少问一句吗」，默认不加。

## P0 — 节点身份：显示 id 与 uid 分离（先于一切并发改动）

- 每个节点有**不可变 `uid`**（时序唯一串），一经生成永不变更、永不复用；跨系统引用（ticket / ADR / 租约 / 事件 / 同步对端）一律用 uid。
- 显示 id（位置路径 `1-1-2`）保持可读，只用于人机对话与 md 渲染。
- 子节点序号计数器**单调递增**，删除尾部子节点不再回收序号 —— 最低成本的防复用补丁，即使还没引入 uid 也应先做。
- **并发先于 uid 是本末倒置**：位置型 id 复用会让租约挂到错误节点，这类 bug 静默且难查。P0 是 P2/P5 的硬前置。

## P1 — 依赖层：树保留给 Human，边服务于调度

边类型（正交在树之上，不替代父子关系）：

| 类型 | 语义 | 参与阻塞 | 允许成环 |
| --- | --- | --- | --- |
| `blocks` | 硬依赖，前驱完成才就绪 | 是 | 否（拒绝并报 `E_CYCLE`） |
| `informs` | 软依赖，提供上下文 | 否 | 是 |
| `supersedes` | 取代另一节点，后继标 archived | 否 | 否 |
| `derives-from` | 来源追溯（ADR、grilling 结论） | 否 | 是 |

关键决策：
- **`blocked` / `blocked_reason` 纯派生（读取时计算，永不落盘）**，唯一权威是 `blocks` 边。`--status blocked` 从 `add` / `update` 可设枚举移除，人工设置返回 `E_INVALID_STATUS`。
- 就绪判定：`status == pending` 且**无未完成的 `blocks` 前驱**且无有效租约，按边实时算 O(V+E)，不依赖计数器（`pending_deps` 计数器推迟到 P3 的 carrier 递归 CTE，不在派生层加缓存 —— 见 Plan §Story 24 决议）。
- 落盘会制造「重算触发点清单」这类第二真相源，本仓库已为 `remove-decision` 的 carrier 语义漂移付过学费，故不落盘。

## P2 — 并发：节点租约取代整图锁

**归因修正（重要）**：并发失败模式**不是 lost update**。整条写命令在整图锁内串行，读-改-写不交错，父状态派生而非快照，物理上不存在「后写覆盖前写」。真实失败是**拿不到锁的进程直接崩溃退出 1**（运行时 shim 把 `os.mkdir` 的 `FileExistsError` 换成 `PermissionError(errno is None)`，旧代码只认 `FileExistsError` 导致锁等待循环从不执行）。因此 **P3（SQLite）不能用「解决 lost update」当动机**——那个动机已被锁层修复推翻，P3 只剩四条独立正当性（见下）。

租约设计（已决策参数）：
- `claim` / `heartbeat` / `release` / `steal`；**默认 TTL 300s + 心跳周期 60s，二者必须同批次交付**（TTL 300s 单独存在会在 5 分钟回收正常任务；只实现 TTL 不实现心跳 = 长任务每 5 分钟被回收）。
- **TTL 未到期时 Agent 侧绝不抢占**；唯一例外是 Human 显式 `release --force`（须写事件日志，使用者担责）。过期租约可被 `steal` 并递增 fencing token，使旧持有者后续写入失败。
- 作用域令牌 `--as-agent <id> --scope <node_uid>`，越界写返回 `E_SCOPE`；**不给 `--scope` 就是不限，不是只读**（subagent 只读靠父 Agent 派活时下发 `--scope` 兑现）。
- 乐观并发 `--if-rev <sha>`，冲突返回 `E_CONFLICT` + 当前 rev。
- 字段级所有权：status / notes 归租约持有者，label / mode / budget / exit_criteria 归 planner，decisions 只追加不覆盖。
- **fencing 优先于字段所有权**：出示已作废 token（< fencing）的僵尸持有者，对**任何**字段（含 planner 字段）的写都拒 —— 否则把 `--status` 换成 `--label` 就能绕过回收。
- 失败语义：`attempts` 递增、`last_error` 记录、指数退避 `min(60*2^(n-1), 3600)`，默认 `max_attempts=3`；达阈值挂 `open_question` 升级 Human，**升级只挂字段不改 `status`**（blocked 仍纯派生，避免制造第二真相源）。

## P3 — Carrier 演进：SQLite 优先于「自研事件流」

- Roadmap carrier 收敛为 single-file JSON 与 SQLite 两种，由**同一套 adapter 契约**承载（`Roadmap` 继承 ~40 方法、只覆写存储原语）。
- 选择理由：`sqlite3` 标准库零新依赖；WAL 多读一写；递归 CTE 天然表达 DAG 就绪/关键路径/影响集；history / decisions / edges / leases 各归一表。
- **SQLite 的四条约正当性（lost update 已剔除）**：① 长事务跨多对象原子写（JSON 只能整图重写）；② 跨设备 P4 需要按行按字段的 HLC 合并粒度；③ 5000 节点读放大（今天每次读都 load 整图）；④ DAG 递归查询一次 CTE 完成。
- 决策：先做 SQLite，不把事件流升格为主事实源（P4 前提，但单设备阶段只增读放大）；`recommend-storage` 仍只读建议，迁移只走显式命令。
- **两种 carrier 语义漂移是头号同类缺陷**：加新 carrier 前先统一语义（如 `remove-decision` = 撤回保留历史，非物理删除），同一套契约测试三 carrier 各跑一遍。

## 错误码与退出码纪律

- 机制已落地：`RoadmapError` 基类 + `ERROR_EXIT_CODES` 表 + `exit_code_for`；失败输出 `Error: E_XXX: …`，Agent 按 code 分支不按文案。
- **错误码细粒度（给 Agent 分支），退出码粗粒度（给编排区分重试语义）**：0 成功 / 1 通用失败 / 2 锁超时（可重试）/ 3 预算触顶（收手）。**新错误码默认映射退出码 1，只有新增「需不同重试语义」的类别才开新退出码**，防止退出码膨胀。
- 每个新码必须配一条断言退出码的用例，只加码不锁退出码等于复制旧缺口。

## 测试缝（三 carrier 同语义）

- 主缝 = **CLI 契约**（subprocess：参数 + stdout JSON + stderr 的 `E_*` code）；次缝 = carrier adapter（同一套契约参数化跑三遍）。不引入 mock、不做进程内 API 测试。
- 并发断言用**多进程真实调用**（N 个 CLI 进程写兄弟节点），结果是「父子最终一致」而非「某锁被持有」；N 个 writer 必须**全部退出 0**（1 是崩溃，一个都不能有）。
- 红绿双向：每条新约束要有「抽掉实现会红」的负向证明；字节级不变断言用于「trace 不泄进视图」类命题。

## 风险（本模型层面）

1. **视图膨胀是头号风险** —— DAG / 租约 / owner / open question 全塞 md 会把资产变负债，护栏视为硬约束。
2. **carrier 语义漂移** —— 加 carrier 前先统一语义，否则漂移三倍放大。
3. **并发先于 uid 本末倒置** —— P0 是 P2/P5 硬前置。
4. **状态双重来源** —— `blocked` 落盘会与计数器、派生父状态成三真相源；要渲染便利性就落本地物化视图而非共享事实源。

## 后续

P5（执行图 / trace layer）是另一张图的设计，权威见 [`zj-roadmap-execution-graph.md`](zj-roadmap-execution-graph.md)。
