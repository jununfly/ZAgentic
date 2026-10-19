### 视角：B

`视角来源: 跨会话独立Agent`

#### **观点 1**

- **发现**：原文把生命周期阶段、capability manifest、唯一 owner、优先级、停止条件和 Human gate 明确划入本子问题边界，但没有给出阶段目录、依赖链或“阶段完成”的可判定条件（原文 L6）；Q1 也只提出“哪些生命周期阶段和 skill owner 是不可重叠的”，尚未形成可排期的答案（原文 L12）。
- **影响**：实现团队无法建立关键路径，两个 skill 可能在同一阶段读写同一 artifact；即使功能可运行，也无法判断是“阶段未完成”还是“应交给下一 owner”，导致重复调用和责任漂移。排期风险不是文档风险，而是每次请求都可能多走一轮调用。
- **建议**：先登记一份不可重叠的阶段/owner 表，最小字段为 `stage`、`owner_skill`、`input_artifact`、`output_artifact`、`prerequisite`、`exit_condition`、`rollback_target`。首版固定为 `intake → plan → execute → verify → close` 五阶段；每阶段只允许一个 owner，artifact 只能有一个写 owner，其他 skill 只能声明读或提出候选。以“入口字段齐全、唯一 owner、退出断言通过、回退目标存在”为阶段完成条件；未满足任一项即不得推进。先做 registry/manifest，再做 planner，最后接 execution，形成显式关键路径。

#### **观点 2**

- **发现**：成功判据要求“同一请求能得到确定性的 stage plan 和 next action”，并要求冲突 fixture 证明不会重复调用、越权写入或两个 skill 同时拥有同一 artifact（原文 L7）；Q2 则要求输入 artifact、manifest、precedence 和 Human gate 产生唯一调用路径，但原文没有规定冲突时的裁决算法或 tie-breaker（原文 L13）。
- **影响**：仅有“优先级”字段不足以保证确定性；当两个 skill 都声明 capability，系统可能按发现顺序调用、重复产出，或在 planner 已选 owner 后仍被后续 skill 越权接管。此类错误会污染 artifact，且难以从最终结果反推出错误的选择路径。
- **建议**：把 planner 做成纯函数：先校验输入 artifact，再按 `stage → artifact owner → precedence → skill id` 的固定顺序筛选；同一 `(request_id, stage, artifact)` 只能产出一个 owner，tie 不能用时间戳或加载顺序解决。plan 中必须持久化 `plan_id`、输入摘要、候选列表、淘汰原因、owner、next action 和 precedence 版本；同一 plan 内单个 skill 默认最多出现一次。若最高优先级仍并列、manifest 缺字段或 owner 与 artifact 写权限不一致，planner 返回 `CONFLICT` 并停在 Human gate，不执行任何 skill。验收至少覆盖正常、并列优先级、重复 owner、越权写入四类 fixture，并要求同一输入重复运行 20 次得到完全相同的 plan。

#### **观点 3**

- **发现**：Q3 直接询问多个 skill 误触发、失败或用户未选择时何时停止、回退或升级（原文 L14）；但现有成功判据只描述“不重复调用、不越权写入、不双 owner”的结果，没有把失败状态、重试上限、回退点或 Human gate 的触发条件写成协议（原文 L7）。
- **影响**：没有状态机时，“失败”容易被误判成可继续尝试，造成副作用累积；反之，任何可恢复的短暂故障都可能让整条链路过早终止。用户未选择时若继续执行，还会把待确认动作变成未经授权的写入。
- **建议**：采用 `READY / RUNNING / WAIT_HUMAN / SUCCEEDED / RETRYABLE_FAILURE / ROLLED_BACK / BLOCKED` 状态，并规定三条硬路径：① owner 冲突、输入不完整、涉及不可逆写入或用户未选择，立即进入 `WAIT_HUMAN`，零 skill 执行；② 仅网络/超时类暂态错误自动重试 1 次，连续 2 次失败就回退到最近一个已提交 artifact，进入 `ROLLED_BACK` 并升级；③ skill 已产生输出但 verify 失败时禁止下游继续，保留失败证据并回退，不得静默重跑。Human gate 的批准对象必须包含待执行 skill、写入 artifact、风险、回退目标和 next action；审批拒绝或超时保持 `BLOCKED`，不能猜测用户意图。

#### **观点 4**

- **发现**：原文要求每个核心 skill 具备明确入口、输出、禁止事项和退出条件，并要求冲突 fixture 证明关键安全性质（原文 L7），但没有验收责任人、完成阈值、实施成本或回退演练的量化口径；子问题范围虽说“不重新定义 artifact 字段，也不决定具体外部 adapter”，却仍需依赖这些边界来落地编排（原文 L6）。
- **影响**：如果只补 prose，无法判断“做到什么程度算完”，也无法向迭代计划承诺资源。最可能的失败是 manifest 看似齐全但没有可执行测试，或者 planner 完成后才发现 adapter 能力/输入不满足，关键路径被迫返工。
- **建议**：由一名技术负责人维护 registry、planner 和状态机；每个 skill owner 负责自身 manifest 与 3 个 fixture（正常、冲突、失败），测试负责人负责回归闸门，产品/Human 只负责高风险 gate。以 6 个核心 skill 作为首版预算基线：manifest/registry 1.5 人日、确定性 planner 1.5 人日、停止/回退状态机 1 人日、fixture 与回归 2 人日、文档和演练 1 人日，共约 7 人日；skill 数量变化时按每个 skill 增加约 0.5 人日修正。完成条件为：每个 skill 四字段 100% 齐全；正常路径、owner 冲突、越权写入、失败回退四类 fixture 全部通过；同一输入重复运行 20 次 plan 一致；任何未决冲突均零副作用停在 gate。首个版本先用假 adapter 完成编排与回退演练，再接真实 adapter；若假 adapter 阶段仍有非确定 plan 或失败路径无回退，停止扩展能力并回到 manifest/状态机修正。
