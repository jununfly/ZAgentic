---
doc-kind: design
authority: primary
authority-id: design.dp-driven-skill
model-elements: [entity.design]
---

# zj-dp-driven 设计文档（定位与概要设计 · 基准）

> **本页性质：实现前的基准设计页。** `zj-dp-driven` 尚无代码 / `SKILL.md`，故本页不挂代码 `file:line`
> 锚点——行锚将在实现落地后回灌对齐。本轮**刻意不引用** `zj-wayfinder` / `zj-roadmap-driven` 的实现细节，
> 以免污染基准；吸收/取代旧 pair 与 `zj-composer` 留待「基准立稳后」的独立讨论。
> 标记约定：`[定稿]` = 本轮锁定的基线判据；`[目标]` = 已定方向、待实现的具体机制；`[未决]` = 明确留到下一轮。

## 1. 定位

> **[定稿]** 把一次复杂任务当作**动态规划（DP）在一张部分可观测状态图上的一次运行**：
> **规划 = 展开**未观测状态、**发现 = 从 findings 生成新状态**、**执行 = 推进 tickets 到终态**——
> 三者是**同一次编排调度循环（§4）的不同侧面**。过程态活在运行时 sqlite，
> **执行完即删除**；沉淀的是它引用过的一组 markdown，由 `zj-docs-ontology` 治理成长期文档。

**差异化判据**（相对任何"任务树/路线图"工具，也是本轮基准立得住、日后是否值得"取代旧 pair"的硬标准）：

1. **规划与执行一体**：不是"先 plan 后 do"的两段式，而是同一次 DP 迭代里展开 + 求解 + 回灌。
2. **过程即燃料**：状态图用完即焚，长期价值只在其引用的 md 语料——反"过程文档腐烂"。
3. **渐进披露 = DP 表压缩**：sqlite 只放图 / 索引 / 时间戳 / 指向 md 的引用；语义全在 scoped md 按需 pull。低 token 占用是一等设计目标。
4. **memoization 贯穿层二全局图**：finding 靠多归属共享处置结论（overlapping subproblem），ticket 靠全局唯一 + `blocks` 边辐射共享终态（单归属但完成事件跨 plan 生效）——两者合起来确保"已做的事不被重复编排"。

**DP 概念 → 本 skill 落点**：

| DP 原语 | zj-dp-driven 落点 | 承载实体 |
| --- | --- | --- |
| **状态图 · 层一（粗粒度）** | 每个 **task** 是一个状态；`tasks-state-graph` = task↔task 节点+边（规划分解、跨 task 依赖） | task |
| **状态图 · 层二（细粒度）** | 每个 **ticket / finding** 是一个状态；`ticket/finding-state-graph` = ticket/finding 节点+边（父子、`blocks` 依赖、`finding→ticket` 物化；finding 亦可派生 finding/task，见 §3.5） | ticket / finding |
| optimal substructure | 层一：task 完成由其 task-plan（层二区域）内 findings∧tickets 终态组合推出；层二：ticket/finding 完成由其依赖下游终态推出 | task ← task-plan ← ticket/finding |
| overlapping subproblem | **finding 多归属**：同一节点被多个 plan 引用 = 同一条观察被多路径需要；**ticket 全局唯一**：单归属但其 `blocks` 出边辐射跨 plan，完成一次 = 所有下游路径同时受益 | finding + ticket |
| memoization | **层二全局图（§3.6 F1）× 节点不复**：① finding 处置一次、跨归属传播（§3.5 多归属路径）；② ticket 全局唯一编号、终态是图上的单点事件、blocks 边自动跨区辐射（单归属路径）。两者共同构成"解一次、处处命中" | 层二全局图 |
| decision / action | ticket（原子动作，单归属，绑定 issue 或本地 md） | ticket |
| value function V | **编排 optimizer 的子集内聚评估**（非逐票排序，见 §4.2 / §3.6 F3）；参考值，不追求严谨（§8） | 算分器 |
| Bellman re-plan | **编排触发 → optimizer 选子集定序 → 执行 → 回灌新 items → 再触发**（§4.1–§4.6），带抢占 + 并发 + 热插 | 运行时循环（§4） |
| top-down（自顶向下展开） | 从 destination 的 scoped context 递归生成 tasks/findings | 规划 + 发现 |
| bottom-up（自底向上收敛） | 叶子 ticket 完成上推 task-plan → task 终态 | 执行收敛 |
| 在线 / 部分可观测 DP | 新 finding 可无归属 → 未来新建 task 编排它（fog 毕业） | orphan finding |

> **[定稿] DP 是两层嵌套，不是单层。** 外层在 `tasks-state-graph` 上对 task 递归；内层在每个 task-plan
> 的区域内对 `ticket/finding-state-graph` 递归。一个 task-plan 正是"外层的一个状态节点 = 内层的一个子问题
> 区域"的对应点。两层的连接拓扑见 §3.6：内层图全局一张（F1）与外层边为内层跨区边商图（F2）均已 **[定稿]**；
> 仅"编排 optimizer 的算分器具体实现"（F3，§3.6）留 §8 待定。

## 2. 功能模型：五实体

> **[定稿]** 字段级 schema 属 `[目标]`（实现时定列/类型）；此处只定实体语义与关系。状态列一律
> 取四态词表：`未完成 / 被阻塞 / 已完成 / 已放弃`。

| 实体 | 角色（DP 语义） | 关键属性 | 索引 / 归属 |
| --- | --- | --- | --- |
| **task** | **层一状态节点**（粗粒度） | `name`（据 scoped context 总结的简单清晰 self-explain 一句话）、`created_at`、`completed_at`、**scoped context**（md）、**scoped memory**（md） | 自增 `0,1,2…`；`status` **不存储、查询派生** |
| **task-plan** | task 的求解计算单元 = **层二状态图的子问题区域** | 编排一组 findings + tickets（运行时可增删改）、到终态时的简洁总结 | 与 task **1:1**（索引即 task 编号）；`status` **存储**（唯一状态源，见 §3.1） |
| **finding** | **层二 memoized 子问题状态节点** | 原子化、彼此不耦合的观察/发现（结论 / 灵感 / 新问题 / 新细节 / 遗漏细节皆可是）；**不预设已成结论或已可执行**（详见 §3.5）；新发现即追加；关联 scoped md 存放其内容与处置记录（[目标]） | 自增 `0,1,2…`；可归属 **0..n 个 task-plan**；可无归属（orphan，待未来 task） |
| **ticket** | **层二原子动作状态节点** | 绑定 github/gitlab issue 或本地 md；`json-string` 内 kv 记录；ticket↔ticket 有**父子关系 + 依赖关系**；`derived_from_finding`（见 §7 Q1）；关联 scoped md 存放其详情与执行记录（[目标]） | 自增 `0,1,2…`；同一时间**只归属一个 task-plan**（单归属） |
| **存储（carrier）** | DP 表的物理之家 | sqlite（仅过程信息）+ 同目录一组 md（长期语料） | 落点**由 Human 指定目录** |

> **[定稿] 术语——available pool**：`pool = { s ∈ 层二全局图（tickets ∪ findings）| s.status = 未完成 ∧ s 未被任何 in-flight plan 收纳 }`。
> 它是**派生视图**（由 ticket/finding 的 `status` + 其 `plan_membership` 引用集合算出），不是一等实体、不单独存储。
> §4 编排循环的"输入"即为 pool 的当前快照。

## 3. 状态规则与核心不变式

### 3.1 状态单一来源（一致性根）
> **[定稿]** 过程状态分**三级**，每级只有一个存储点，越往上越派生：
> - **层二原语**：ticket / finding **各自存储**自身生命周期状态（这是唯一被人工/agent 直接写的底）。
> - **层二区域 → 层一交界**：**task-plan 存储**其生命周期状态（`未完成 / 已完成 / 已放弃` 显式，`被阻塞` 派生）。
> - **层一投影**：**task 的状态一律由查询派生**，绝不落库。
> 动机：杜绝同一语义出现互相矛盾的副本——尤其 task 与其 task-plan 不双写。

### 3.2 被阻塞一律派生、从不存储
> **[定稿]** `被阻塞` 是计算态，不作存储列，且**在两层图上各自派生、语义同构**：
> - **层二 ticket / finding 被阻塞** ⇔ 其在 `ticket/finding-state-graph` 上的 `blocks` 依赖上游未到 `已完成`
>   （父子关系**不**自动阻塞，只有依赖边阻塞）。
> - **层一 task-plan / task 被阻塞** ⇔ 由 §3.6 F2 的**商图**派生：外层依赖边 = 内层跨区 `blocks` 边的投影，故阻塞的
>   **唯一真相源在内层**（外层无独立的 `blocked` 存储）。
> - 无阻塞来源时该字段**缺席**（不写 `false`），以免制造可漂移的副本。

#### 3.2.1 外部 / 非图内阻塞的处置（不破坏派生 blocked）
> **[定稿]** 若阻塞源**不在依赖图上**（例："等第三方回复"、"等 Human 签字"、"等运维开通权限"），按下列**优先级**处理——
> 目标始终是不引入第二真相源、不把 `blocked` 从"派生"退化为"部分存储"：
>
> 1. **节点化（首选）**：建一个 finding / ticket 节点表示该外部等待（比如 `ticket-7 "等供应商回复 API 限额"`），
>    让别的节点通过 `blocks` 边依赖它。它仍是"上游未到终态"，被 §3.2 派生规则天然覆盖，
>    **不新增任何存储字段**。外部状态变化 = 该节点状态变化，单一源不变。
> 2. **`external_hold` 字段（次选）**：仅当"节点化"成本过高（例：临时性极强、不值得占一个 memo 位）时，
>    给 ticket / finding 加一条**独立正交**字段 `external_hold: reason | null`——
>    **绝不并入 `blocked` 语义**。展示态由 `shown_blocked = derived_blocked ∨ external_hold ≠ null` 合成；
>    存储与语义上两套来源**始终可区分**（`derived_blocked` 是图上事实，`external_hold` 是世界事实的旁路注记）。
>    外层 `shown_blocked` 由**两条正交路径**合成：
>    - `derived_blocked`（plan/task 级）：沿 §3.6 F2 商图规则从内层 `blocks` 边投影；
>    - `external_hold`（plan 级聚合）：`∃ 该 plan 内任一 item 的 external_hold ≠ null`（取 any，非边投影）。
>    两条路径结构不同、语义独立，合起来才得 plan/task 的 `shown_blocked`。
>
> **禁止**：把外部阻塞**直接写入** `status = 被阻塞`。那会让 `blocked` 从"纯派生"退化为"部分存储 + 部分派生"，
> 破坏 §3.1 的单一状态源——正是本设计根除的目标。

### 3.3 task 派生投影（示例规则）
> **[目标]** task.status 由 1:1 的 task-plan 投影（规则可在实现期细化，但"派生"这一性质 `[定稿]`）：
> `已完成 ⇔ plan.status = 已完成`；`已放弃 ⇔ plan.status = 已放弃`；`被阻塞 ⇔ plan 派生 blocked`；
> 否则 `未完成`。

### 3.4 所有权不变式
> **[定稿]**
> - **ticket 单归属**：同一时刻一个 ticket 只属于一个 task-plan。若两处都需要同一执行 → 说明它其实是**共享的
>   finding**，应先以 finding 表达、再由 finding 按 §3.5 处置出各 plan 各自的下游（常为 ticket，亦可为新 finding/task/细节）。
> - **finding 多归属**：一个 finding 可同时挂在多个 task-plan 上；这是 overlapping subproblem 的落点。

### 3.5 处置与 memoization 不变式
> **[定稿｜finding 含义钉死]** finding 是一条**原子化、彼此不耦合的观察/发现**，形态可以是：调研得出的结论、
> **灵光一闪的想法**、**新发现的问题**、**新发现的细节**、或**此前 miss 的细节**。
> **不得**把 finding 默认成"已确定的观点/结论"或"马上就能转化为行动的东西"——它常常只是**待加工的原材料**，
> 本身可能催生更多 finding 或新 task。（呼应 §2 关键属性。）

> **[定稿｜"已完成" = 已处置，不等于已变成行动]** finding 的 `已完成` 表示它**已被处置(dispositioned)一遍**：
> 内容落进其 scoped md，且下游后果按 finding 的**实际形态**分派，可能是
> ① n 个 tickets、② 新 findings（新问题拆出的子问题）、③ 新 task（灵感开辟的新区域）、
> ④ 仅回写进某 task 的 scoped context/memory 的细节、⑤ 判定无关而 `已放弃`。
> **产出 tickets 只是其中一种**；不存在"每个 finding 都必须 / 即将转成 tickets"的预设。

> **[定稿｜finding 的 memo 路径 = 处置一次 + 跨归属传播 + 之后只读复用]** 因 finding 多归属（§3.4），处置必须**跨归属传播**，
> 才等价于 DP"填 memo → 后续 call site 全命中"：
> 1. 某 task-plan 推进时**首次触达** finding1（finding1 现同时挂 plan1、plan2…）。
> 2. 与 Human/agent 一起**处置** finding1：按上述形态产出下游（tickets / 新 findings / 新 task / scoped 细节），
>    并把下游**分派到每一个引用它的 plan 的合理位置**（各 plan 后续需求不同）。
> 3. **从所有归属它的 plan 中摘除 finding1**、标 `已完成`（或 `已放弃`）；结论/内容存于 finding1 的 scoped md。
> 此后任何 plan 复用 finding1，读的是它的 memo（已落地的下游 + 结论），**不重跑**。
> 少 (2) 的分派 → 某 plan 依赖断链；少 (3) 的摘除 → 会被重复处置，违背 memoization。
> finding 的 `已完成` 与"其 tickets 自身完成"**解耦**：处置只表示"已分派下游"，其价值由**下层** tickets /
> 新生成的 finding 继续承载（见 §4）。

> 例（**仅一种形态**：结论 → tickets）：finding0「Kafka 3.6 是否原生支持 Schema Registry」同时挂 plan-A/plan-B；
> 查证得"支持" → 物化为 `ticket-A1`（选型结论）+ `ticket-B1`（schema 走 Confluent），finding0 从两 plan 摘除、标完成，
> plan-B 后续直接读 memo、不复查。**其余形态**（灵感 / 新问题 / 遗漏细节）处置产物不同，按上 ①–⑤ 落。

> **[定稿｜memoization 不只属于 findings]** 上面描述的是 finding 的**多归属 memo** 路径。memoization 的"重叠→只解
> 一次→处处命中"效应同样落在 **tickets** 上：层二图全局一张（§3.6 F1），每张 ticket 是**全局唯一节点**——无论
> 它由编排 plan 时直接生成、从 parent-ticket 拆解而来、还是由 finding 处置后转化而来，完成一次即通过 `blocks`
> 出边对所有下游（散布在不同 plan 区域）同时生效，无需重复执行。两种路径合起来才完整表达了 DP 的
> "overlapping subproblem → memo table"语义：**finding 靠多归属共享、ticket 靠全局唯一 + 边辐射共享**。

### 3.6 两层状态图的关系（嵌套 / 连接拓扑）
> **[定稿]** 存在两层：层一 `tasks-state-graph`（task↔task），层二 `ticket/finding-state-graph`（ticket/finding↔ticket/finding）。
> 每个 task-plan 是"层一节点 ↔ 层二一片区域"的对应。连接拓扑已据「finding 多归属」与「状态单一来源」两条不变式收口：

- **[定稿 F1｜内层图 = 全局一张]** 层二是**单一全局** `ticket/finding-state-graph`；task-plan 是其上选出的**子区域**
  （区域内 ticket 集互斥、finding 集可跨区重叠）。共享 finding 是**同一个节点**、绝不按 plan 复制 → memoization 成立。
  - **存储后果**：节点的 plan 归属是多对多引用；删除/裁剪按**节点**处理，不按 plan 边界。
  - **可视化后果（取巧，详 §6）**：某 finding 同时出现在多个 plan 区域时，各区各画一次并加"重叠"角标 + 异色，
    本视图**不**追求表达"该 finding 究竟与哪些 plan 重叠"的全局连线。

- **[定稿 F2｜外层边 = 内层跨区边的商图]** `tasks-state-graph` 的依赖/`blocks` 边是**投影、不独立存储**：
  存在 task A → task B 的依赖边 ⇔ 层二中"A 区域内某 ticket/finding"依赖"B 区域内某 ticket/finding"。
  - **单一真相源**：依赖唯一记录在层二 `blocks` 边；外层 `blocked` 由 §3.2 派生 → 两层不会各有一套阻塞真相。
  - **回灌跨层**：内层 ticket 完成 → 满足跨区边 → 外层对应 task 自然解锁，无需手写外层边。
  - **[边界]** 此处"外层边"仅指**依赖 / blocks** 语义；top-down 展开产生的 task **父子包含**关系是另一回事，不参与 `blocked` 派生（属规划结构）。

- **[未决 F3｜值函数 V 的角色重定义]** 旧框架问"V 选下一个 plan / ticket"；§4 编排调度模型下，这个问法不再成立——
  plans 由 optimizer 按需创建/热插、多 plan 可并行推进、plan 内次序由 blocks 拓扑约束决定。
  V 的实际角色 = **编排 optimizer 评估候选子集的内聚得分**（"选哪批 items 做本轮最优"），而非逐票排序。
  具体算分因子与触发时机随实现期定（§8）。

## 4. 运行时循环（编排调度）

> **[定稿]** DP 主循环发生在**编排层**——每轮从 available pool 选出高内聚子集、定内部拓扑序、产出一个 task-plan。
> 这不是"V 逐票排序"，而是**带抢占 + 并发 + 热插的编排调度循环**，直到 §5.1 完成判据成立。

### 4.0 初始化（destination → task0 → pool bootstrap）

> **[定稿]** 启动 `zj-dp-driven` 时的 bootstrap 序列：
> 1. **Human 给出 destination 描述**——一句话或一小段，说明这次 DP 要到达什么终态。
> 2. **agent 据此生成 task0 的 scoped context**——destination 落成 task0 的 scoped context md，成为后续所有展开的
>    顶层参照。
> 3. **首批展开**——agent 基于 destination 做初步分析，生成首批 tickets 和 findings 入 available pool。
> 4. 进入 §4.1 编排主循环（首次触发条件 = "pool 非空 ∧ 无 in-flight plan"）。

### 4.1 编排触发

编排不是线性 round-by-round，以下任一条件均可触发一次新编排决策：

| 触发源 | 说明 |
|---|---|
| 新 items 出现 | ticket 执行涌现、finding 处置产物、Human 手动添加 |
| 当前 plan 被阻塞 | §3.2 派生 blocked → 编排器自然跳过该 plan，选其他可行 plan 顶上（阻塞式抢占） |
| 优先级抢占 | Human/agent 判定当前 in-flight plan 不是最该推进的 → **释放 plan claim**（不新增第五态，status 仍 `未完成`），另开新 plan；旧 plan 之后可被重新 claim 续接 |
| agent 空闲 | 一个 agent 交完手头 tickets → 触发"有没有可编排/可 claim 的下一步"检查 |

### 4.2 编排决策（DP 的"转移"）

```
输入：available pool（未被任何 plan 收纳的 tickets + findings）
      + in-flight plans（已 claim 且未终态，可热插）
      + 层二全局图拓扑（§3.6 F1）

优化目标（判据 = MVP / 强关联性 / 高内聚性）：
  从 pool 选出子集 S，使 S 内部关联度最高、对 pool\S 切割最小、
  且 S 的产出本身构成一个可交付最小增量（MVP）。
  确定 S 内部的拓扑序（由 blocks 边约束，无约束段标注为"可并行"）。

输出：
  ① 新建 task-plan（S 成为其内容），或
  ② 无可行子集 → 触发结算轮（§4.5），或
  ③ 部分 items 热插到已有 in-flight plan（见 §4.3）
```

> **[定稿] optimizer 的路由决定权**：新 items 入 pool 后，由 optimizer 在每次触发时决定其去向——
> 热插到匹配的 in-flight plan（若高关联且无阻塞），或留在 pool 等待后续轮次的新 plan 编排。
> agent 执行期的局部判断（§4.3）是补充路径，不取代 optimizer 的全局路由。

> **[定稿] 算法复杂度约束**："从 pool 选高内聚子集"本质是 densest-k-subgraph 变体（NP-hard）。
> optimizer **使用贪心 / 局部启发式**（§1 差异化判据 3 "少 token、不追求严谨"），**绝不做穷举或精确最优搜索**——
> 实现者不得将"最优解"读为数学最优；它是参考排序 + 可解释的人类确认。

### 4.3 热插（plan 非不可变合同）

> **[定稿]** in-flight plan 允许被追加 items——新 ticket/finding 若**高关联且无阻塞**，可热插到匹配的 in-flight plan，
> 无需等它结束后重新编排。

判定"高关联且无阻塞"由**两者互补**：
- **optimizer 批量检查**（全局视野）：每次编排触发时，optimizer 同时审视 pool 与 in-flight plans，把适合归入已有 plan 的 items 直接热插。
- **agent 执行期追加**（局部信息）：agent 在推进 ticket 过程中发现"这件事该归当前 plan"→ 直接 add（不需 plan claim，见 §4.4 锁规则）。

### 4.4 并发与锁（两层 claim）

> **[定稿]**

| 锁层级 | 粒度 | 作用 | 释放条件 |
|---|---|---|---|
| **plan-level claim** | 一个 agent 持有一个 plan | 防两个 agent 同时对同一个 plan 做**重编排**（re-optimize 其结构） | plan 终态 / 主动释放（优先级抢占时） / agent 会话结束 / **超时释放**（[未决] §8） |
| **ticket-level claim** | 一个 agent 持有一张 ticket | 防两个 agent 重复执行同一张 ticket | ticket 到终态 / agent 释放 / **超时释放**（[未决] §8） |

**不受 claim 约束的操作（lock-free）**：
- **finding 处置**：幂等，任何 agent 可直接处置（摘除 + 标态 + 分派下游），即使被触及的 plan 被另一 agent claim——因为 finding 是多归属全局节点，它的处置不是"修改某个 plan 的编排结构"，而是"更新层二图的一个节点 + 从其所有归属 plan 中摘除"。
- **热插 add**：向 in-flight plan 追加 items 不需要 plan claim（见 §4.3）。

> **[定稿] 并发原子性保证**：finding 处置和热插 add 的原子性由 **carrier 单写者**保证——
> sqlite 的串行化写入天然确保"同一 finding 不会被两个 agent 同时处置成功"（第二个写入读到已摘除状态即 no-op）。
> 无需额外分布式锁或乐观并发控制。若未来引入并行写（如 WAL 并行写多连接），需重审此假设。

### 4.5 结算轮

> **[定稿]** 当 optimizer 判定 pool 中**再也凑不出满足内聚阈值的子集**（剩余 items 互相低关联、散乱），
> 触发结算轮：一个特殊 task-plan 收纳 pool 中**所有**未解决 tickets + findings，次序退化为主线顺序（blocks 拓扑
> 优先、其余按编号递增），逐个处理，不做内聚性优化。
>
> **claim 语义**：结算轮不再被 re-optimize，因此 **plan-level claim 退化**——任何 agent 可直接领取其中的 tickets
> （只需 ticket-level claim），无需独占整个结算 plan 的编排权。

### 4.6 终止与收摊

```
所有 task 到终态（§5.1）
  → 总结呈现（含结算轮）
  → Human 标注：结算轮完成状态 + 整个 dp-driven 完成状态（两个独立 gate）
  → §5.2 两段式收摊（治理 md → 删 sqlite）
```

### 4.7 保留的性质

- **渐进披露**：每一步只载入"焦点 plan + 其祖先链 + 关联子图"上下文；items 正文按需从 scoped md 拉。
- **回灌的机械性**：ticket 终态沿层二图边传播 → plan 内成员全终态 → 触发总结 → task 沿层一商图投影（§3.6 F2）。
- **memoization 贯穿**：finding 处置一次处处命中（§3.5）；ticket 全局唯一、完成即辐射所有下游路径——两种路径合起来让"已做过的事不被重复编排"。

## 5. 存储与生命周期

### 5.1 完成判据
> **[定稿]** **所有 task 均到终态（`已完成` 或 `已放弃`）⇔ 整个动态规划完成。** 无"部分完成即收摊"的中间态。

### 5.2 两段式收摊（Q4=a）
> **[定稿]** 完成判定后按固定顺序，且**过程 sqlite 在治理期间仍可读**：
> 1. **导出关系快照**：agent 将层二图中的关键跨 plan 依赖、finding 多归属映射、物化链路等**结构性关系**
>    摘要为一份"process-summary.md"落进同目录——确保即使治理者未主动查图，也不遗漏非显式关联。
> 2. **治理 md**：Human 用 `zj-docs-ontology` 对本目录那组 md（含上述快照）做文档治理——此时 sqlite 仍在，
>    治理可引用过程图补 doc-map。
> 3. **删除 sqlite**：治理完成后，过程态 sqlite 直接删除（它是"燃料"，不是"档案"）。
> 理由：若先删再治理，治理阶段就丢失了过程图这份证据源；若不导出快照，治理者只看各独立 md 可能遗漏跨 md 的
> 隐含关联结构（因为 sqlite 的 blocks 边 / plan membership 不会自然出现在单篇 md 里）。

### 5.3 权威边界（继承的硬纪律，不复述旧 pair）
> **[定稿]**
> - **sqlite 内容不应被任何长期文档引用**——它是可删的过程态，引用它 = 引用一个注定消失的东西。
> - **只有同目录那组 md 是长期文档语料**；sqlite 内的过程信息**单向引用**这些 md 与其他长期文档。
> - 依赖方向：`sqlite 过程图 → 结构化 md →（经 ontology 治理后）长期文档`。节点/票的终态只表示**过程状态**，
>   不是产品/架构/正确性的证据。

### 5.4 过程态落点纪律
> **[定稿]** 目录**由 Human 指定**，skill 绝不默认 `~/` / 仓库根 / cwd。sqlite 进程以**当前用户权限**运行，
> **绝不写指定目录之外**——这是唯一的隔离边界（无网络、无凭证）。**[未决]** 与既有过程区约定
> （`docs/plans/`、`tmp/skills-outputs/`）如何并存——留 §8 统一谈，本轮不预设、不写死路径。

## 6. 可视化呈现（概要）

> **[目标]** 一张交互视图，分两区：
> - **左区**：全局 DAG，**两层同屏**——层一 `tasks-state-graph`（task→task-plan），层二 `ticket/finding-state-graph`
>   （plan 内 tickets & findings 的父子/依赖/物化边），节点带简单状态标记；**无 task-plan 关联的 findings（orphan）
>   排在该区下方**，与主图分离呈现。
> - **[定稿] claim 可视化区分**（承 §4.4 / Q8）：被 agent claim 的 in-flight plan 与释放 claim（暂停）的 plan
>   在视觉上有明确差异（如实线边框 vs 虚线 / 高亮 vs 灰化），让 Human 一眼识别"哪些在推进、哪些挂着"。
> - **右区**：点击左区任一元素 → 以**卡片**展示该元素的详细信息（含 scoped context/memory 引用、物化关系、时间戳）。
> - **[定稿] 共享 finding 的取巧渲染**（承 §3.6 F1 全局内层图）：一个 finding 归属多个 task-plan 时，各区**各画一次**
>   并加"重叠"角标 + 异色；本视图**不**画"它与哪些 plan/区域重叠"的全局连线，也不追求表示重叠对象是谁。
> - **[未决]** 渲染方式（静态 HTML / CLI 生成 / 依赖何种布局引擎）与技术契约留实现期。

## 7. 本轮锁定的四条判据（Q1–Q4 决策记录）

- **Q1（`finding→ticket` 物化边表达）→ (a)**：`[定稿]` ticket 增列 `derived_from_finding: int | null`，1→n 天然满足；
  物化改派即置 null。此列**只覆盖 §3.5 ① "处置产物含 ticket" 这一形态**；finding 派生**新 finding / 新 task** 的
  溯源边未定列，随 carrier schema 实现期定（§2 `[目标]`）。过程表越薄越好，单归属已足以推回 finding→plan 的分派。
- **Q2（blocked 存储 vs 派生 + 状态单一来源）→ (b)**：`[定稿]` `被阻塞` 一律派生（§3.2）；
  **task-plan 存储其状态、task 恒派生**（§3.1 三级链），二者同源、不双写即"确保结果一致性"的落点。
- **Q3（终态标注的边界，按推荐分层）**：`[定稿]` **ticket 完成由 agent 判**（依据交付物 / 绑定 issue 的状态）；
  **task-plan 终态由 Human 判**（战略层）；当 plan 内所有 findings∧tickets 到终态时，agent 自动生成简洁总结供
  Human 一键确认；**不新造 stale 机制**——长期未标注的 plan 自然保持 `未完成`，沿 §3.2 派生链阻塞其下游 task——
  Human 延迟即流程延迟，无需额外惩罚因子。
- **Q4（收摊顺序）→ (a)**：`[定稿]` 完成判定 → 治理 md（sqlite 仍可读）→ 删 sqlite（§5.2）。

## 8. 明确留到下一轮的未决面

> **[未决]** 以下不影响基准定位，故本轮**不预设、不自作主张**：
> - **编排 optimizer 的算分器实现**（§3.6 F3）：内聚度的具体因子与阈值（effort / 关联密度 / 切割面 / 解锁度 /
>   未标时长）、触发频率、与 V 的关系。方向已定 = **评估候选子集的参考值、少 token、不追求严谨**（§4.2），实现期单独讨论。
> - **claim 超时释放 / TTL 机制**（§4.4）：agent 异常退出后如何判定"已死"而非"在思考"——heartbeat？固定 TTL？
>   实现期定具体策略，设计页仅锁定"释放条件包含超时"这一事实。
> - **sqlite 损坏 / 进程崩溃的恢复路径**：WAL 是否足够？是否需要 backup-before-mutate？实现期验证。
> - **首次上线的渐进策略**：先自用（单人单 agent）→ 再推广（多 agent 并发场景）；渐进期间哪些功能可裁剪。
> - **旧 pair → zj-dp-driven 的数据迁移路径**：已有 roadmap JSON / wayfinder 地图如何映射到新模型——属吸收阶段议题。
> - **可视化实现契约**：渲染后端、状态标注粒度、orphan findings 的排版细节。
> - **过程态落点与既有 `docs/plans/` / `tmp/skills-outputs/` 约定的并存关系**（§5.4）。
> - **命名之外的对外契约**：`SKILL.md` frontmatter、CLI 命令面、opt-in 配置名（按"共享命名根 + self-explain +
>   单复数一致"偏好统一）。
> - **吸收/取代 `zj-wayfinder` / `zj-roadmap-driven` / `zj-composer` 的策略与波及面评估**——本轮**不在范围内**。

## 9. 验证方向（metrics 种子）

> **[目标]** 以下为设计期锁定的**验证判据方向**，实现期精化具体阈值与采集方式。
> 目的：为日后判定"取代旧 pair 是否挣到"提供可操作的对比基准，避免凭印象收场。

| Metric | Baseline | Unit | Method | Target |
|---|---|---|---|---|
| Token efficiency | 旧 pair 同任务的 token consumption | tokens/session | 对比实验：同一 destination 分别用新/旧跑 | ≤ 旧 pair 的 70% |
| 编排轮次 | 旧 pair 的 issue 数 / node 数 | count | 同一任务对比 | 不劣于旧 pair |
| 内聚命中率 | — | % | optimizer 产出的 plan 被 Human 标注"完成"时无人工拆分/重组 | ≥ 80% |
| 回灌正确性 | — | count | ticket 终态后 blocked 重算的调用次数 vs 正确值 | 100% correct |
| 结算轮触发率 | — | % | 整个 DP 运行中触发结算轮的占比（越低说明 optimizer 分组能力越强） | ≤ 10%（初估） |

> **[未决]** 基线数字需旧 pair 同任务跑通后获得；上述 target/threshold 为初估参考、实现后可校准。
> Owner：实现期指派。Exit condition：5 个 metric 均有可重复的测量方法 + 首次基线数据落地。

## Source map

- [zj-docs-ontology SKILL.md](../../skills/codebase-docs/zj-docs-ontology/SKILL.md) — §5.2 收摊阶段治理 md 语料的下游执行者；本页"过程即燃料"落地的运行时依赖权威。
- [ADR 0010 — 本地文件持久化约定](../zj-adr/0010-local-file-persistence-convention.md) — §5.4 过程态落点纪律的上游约定；sqlite + md 双载体的落点必须遵循。

> **本页性质**：**zj-dp-driven** skill 尚无代码目录（本轮只落文档），故无本 skill 的 SKILL.md
> 或 file:line 锚可列；上述两条是当前**已存在、且本页设计明确依赖**的外部权威。skill 实现落地后须回灌
> 其自身锚点，使每条 `[目标]` 断言可被源码验证，未对齐前不得升级为"与实现对齐"。

## Related authority

- [skill 运行期闭包自包含](zj-skill-runtime-closure.md) — `design.skill-runtime-closure`：本设计页不被任何运行时 skill 反向依赖，仅 reviewer 留痕。

## 本轮边界声明

`[定稿]` 本页只确立**定位 + 功能模型 + 概要设计**基准，未创建 skill 代码目录、未改任何脚本/测试、未把本页登记进
`docs/README.md` Design 索引或 `docs/ontology/model.json`（这些登记留待基准 review 通过、或随实现 PR 一并做）。
**未 commit**，按你的习惯等指令。
