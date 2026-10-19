# 子问题：Skill 编排、优先级与冲突解决

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 只决定生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate；不重新定义 artifact 字段，也不决定具体外部 adapter。
- **成功判据：** 每个核心 skill 有明确入口/输出/禁止事项/退出条件；同一请求能得到确定性的 stage plan 和 next action；冲突 fixture 证明不会重复调用、越权写入或两个 skill 同时拥有同一 artifact。
- **声明必需角色集：** B,C,A,T,U,P

## 待讨论问题（scope 草案）

- Q1：哪些生命周期阶段和 skill owner 是不可重叠的？
- Q2：输入 artifact、capability manifest、precedence 和 Human gate 如何产生唯一调用路径？
- Q3：多个 skills 误触发、失败或用户未选择时，何时停止、回退或升级？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文把生命周期阶段、capability manifest、唯一 owner、优先级、停止条件和 Human gate 明确划入本子问题边界，但没有给出阶段目录、依赖链或“阶段完成”的可判定条件（原文 L6）；Q1 也只提出“哪些生命周期阶段和 skill owner 是不可重叠的”，尚未形成可排期的答案（原文 L12）。
- **影响**：实现团队无法建立关键路径，两个 skill 可能在同一阶段读写同一 artifact；即使功能可运行，也无法判断是“阶段未完成”还是“应交给下一 owner”，导致重复调用和责任漂移。排期风险不是文档风险，而是每次请求都可能多走一轮调用。
- **建议**：先登记一份不可重叠的阶段/owner 表，最小字段为 `stage`、`owner_skill`、`input_artifact`、`output_artifact`、`prerequisite`、`exit_condition`、`rollback_target`。首版固定为 `intake → plan → execute → verify → close` 五阶段；每阶段只允许一个 owner，artifact 只能有一个写 owner，其他 skill 只能声明读或提出候选。以“入口字段齐全、唯一 owner、退出断言通过、回退目标存在”为阶段完成条件；未满足任一项即不得推进。先做 registry/manifest，再做 planner，最后接 execution，形成显式关键路径。

**观点 2**

- **发现**：成功判据要求“同一请求能得到确定性的 stage plan 和 next action”，并要求冲突 fixture 证明不会重复调用、越权写入或两个 skill 同时拥有同一 artifact（原文 L7）；Q2 则要求输入 artifact、manifest、precedence 和 Human gate 产生唯一调用路径，但原文没有规定冲突时的裁决算法或 tie-breaker（原文 L13）。
- **影响**：仅有“优先级”字段不足以保证确定性；当两个 skill 都声明 capability，系统可能按发现顺序调用、重复产出，或在 planner 已选 owner 后仍被后续 skill 越权接管。此类错误会污染 artifact，且难以从最终结果反推出错误的选择路径。
- **建议**：把 planner 做成纯函数：先校验输入 artifact，再按 `stage → artifact owner → precedence → skill id` 的固定顺序筛选；同一 `(request_id, stage, artifact)` 只能产出一个 owner，tie 不能用时间戳或加载顺序解决。plan 中必须持久化 `plan_id`、输入摘要、候选列表、淘汰原因、owner、next action 和 precedence 版本；同一 plan 内单个 skill 默认最多出现一次。若最高优先级仍并列、manifest 缺字段或 owner 与 artifact 写权限不一致，planner 返回 `CONFLICT` 并停在 Human gate，不执行任何 skill。验收至少覆盖正常、并列优先级、重复 owner、越权写入四类 fixture，并要求同一输入重复运行 20 次得到完全相同的 plan。

**观点 3**

- **发现**：Q3 直接询问多个 skill 误触发、失败或用户未选择时何时停止、回退或升级（原文 L14）；但现有成功判据只描述“不重复调用、不越权写入、不双 owner”的结果，没有把失败状态、重试上限、回退点或 Human gate 的触发条件写成协议（原文 L7）。
- **影响**：没有状态机时，“失败”容易被误判成可继续尝试，造成副作用累积；反之，任何可恢复的短暂故障都可能让整条链路过早终止。用户未选择时若继续执行，还会把待确认动作变成未经授权的写入。
- **建议**：采用 `READY / RUNNING / WAIT_HUMAN / SUCCEEDED / RETRYABLE_FAILURE / ROLLED_BACK / BLOCKED` 状态，并规定三条硬路径：① owner 冲突、输入不完整、涉及不可逆写入或用户未选择，立即进入 `WAIT_HUMAN`，零 skill 执行；② 仅网络/超时类暂态错误自动重试 1 次，连续 2 次失败就回退到最近一个已提交 artifact，进入 `ROLLED_BACK` 并升级；③ skill 已产生输出但 verify 失败时禁止下游继续，保留失败证据并回退，不得静默重跑。Human gate 的批准对象必须包含待执行 skill、写入 artifact、风险、回退目标和 next action；审批拒绝或超时保持 `BLOCKED`，不能猜测用户意图。

**观点 4**

- **发现**：原文要求每个核心 skill 具备明确入口、输出、禁止事项和退出条件，并要求冲突 fixture 证明关键安全性质（原文 L7），但没有验收责任人、完成阈值、实施成本或回退演练的量化口径；子问题范围虽说“不重新定义 artifact 字段，也不决定具体外部 adapter”，却仍需依赖这些边界来落地编排（原文 L6）。
- **影响**：如果只补 prose，无法判断“做到什么程度算完”，也无法向迭代计划承诺资源。最可能的失败是 manifest 看似齐全但没有可执行测试，或者 planner 完成后才发现 adapter 能力/输入不满足，关键路径被迫返工。
- **建议**：由一名技术负责人维护 registry、planner 和状态机；每个 skill owner 负责自身 manifest 与 3 个 fixture（正常、冲突、失败），测试负责人负责回归闸门，产品/Human 只负责高风险 gate。以 6 个核心 skill 作为首版预算基线：manifest/registry 1.5 人日、确定性 planner 1.5 人日、停止/回退状态机 1 人日、fixture 与回归 2 人日、文档和演练 1 人日，共约 7 人日；skill 数量变化时按每个 skill 增加约 0.5 人日修正。完成条件为：每个 skill 四字段 100% 齐全；正常路径、owner 冲突、越权写入、失败回退四类 fixture 全部通过；同一输入重复运行 20 次 plan 一致；任何未决冲突均零副作用停在 gate。首个版本先用假 adapter 完成编排与回退演练，再接真实 adapter；若假 adapter 阶段仍有非确定 plan 或失败路径无回退，停止扩展能力并回到 manifest/状态机修正。

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现：** 原文把决策范围限定为生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate，同时明确不重新定义 artifact 字段或具体外部 adapter（原文 L5-L7）；但 Q1 只问哪些阶段和 owner 不可重叠，没有给出请求发起者、skill 维护者或 Human 审批者的真实任务与替代方案（原文 L10-L14）。因此，目标用户和需求目前只能视为待验证假设；“唯一 owner”若没有面向用户的责任边界，可能只是内部名义上的归属。产品/生态参照也缺失：尚不能证明它相对手工挑 skill、重复调用或越权写入的现状有足够差异价值。
- **影响：** 即使技术上完成阶段划分，也可能让请求发起者仍需自己判断该找哪个 skill，降低愿意使用的概率；优先级无法拍板，生态价值无法证伪。至少要把“请求发起者获得唯一 next action”和“维护者能发现 owner 冲突”作为两类用户结果，而不是把内部编排完成误当成产品成功。
- **建议：** 为每个生命周期阶段登记一个主用户、一个唯一 owner、一个可观察任务和一个替代基线，登记动作不得新增或改写 artifact 字段。先用不少于 10 个真实/历史请求做验证：至少 8/10 次由输入 artifact 与阶段直接给出唯一 owner 和 next action，0 次两个 skill 同时声明同一 artifact；若任一阶段在 10 个样本中出现 ≥2 次需要用户自行猜测或手工二次分派，则该阶段不得进入默认编排，退回重划 owner。把“相对手工路由的时间/点击减少”作为可证伪价值指标，若试运行中没有至少 20% 改善，就不能宣称该阶段值得自动化。

**观点 2**

- **发现：** Q2 要求由输入 artifact、capability manifest、precedence 和 Human gate 产生唯一调用路径（原文 L10-L14），而成功判据要求同一请求得到确定性的 stage plan 和 next action（原文 L7）。但原文尚未规定 manifest 如何表达“能处理什么/不能处理什么”、precedence 如何消解候选并列，也没有给出与现有替代方案的对照。若多个 skill 都能匹配，用户看不到“凭什么选它”；这正好会复现原文列出的重复调用、越权写入和两个 skill 同时拥有 artifact 的失败形态（原文 L7）。
- **影响：** 路由可能在实现上确定、在用户体验上却不可解释；一旦生态中新增 skill，旧 precedence 可能静默改变用户结果。缺乏可证伪规则时，任何“智能选择”都无法区分于 first-match 或人工经验，用户也没有理由信任自动编排。
- **建议：** 将 manifest 的匹配条件、禁止事项、产出能力和退出条件作为机器可判定项，并规定固定决策顺序：先过滤禁止事项，再按 precedence 排序；最高分唯一时只调用一个 skill，最高分并列或 manifest 缺项时不猜测，停止并进入 Human gate。设置可执行闸门：同一输入最多产生 1 个默认 owner、最多 1 次自动调用；候选数 >1 且无法由 precedence 唯一消解时必须输出候选与缺失依据。用三组基线对照（手工挑选、first-match、声明式 manifest）：在 20 个 fixture 中，自动路径至少 18/20 可解释为“匹配条件 + precedence”且 0 次重复调用；任一不可解释或越权即判该 manifest 不可发布。

**观点 3**

- **发现：** Q3 明确要求处理多个 skill 误触发、执行失败和用户未选择时的停止、回退或升级（原文 L10-L14）；原文成功判据还要求有禁止事项和退出条件，并用冲突 fixture 证明不重复调用、不越权写入（原文 L7）。然而当前结论仍是“待讨论”，Human 拍板也仍是“待拍板”（原文 L54-L73），说明用户在不确定状态下的可接受等待、确认和升级边界尚未形成。若把失败简单交给下一个 skill，用户会遭遇重复副作用；若沉默停止，又无法知道下一步。
- **影响：** 自动化的负面体验会直接抵消其节省成本：一次误触发可能造成 artifact 被错误 owner 写入，连续回退会扩大副作用，未选择时强行代选则破坏 Human gate 的信任。失败路径若没有统一出口，也无法与“确定性的 next action”成功标准对齐。
- **建议：** 固化三段式协议并写入 fixture：①误触发——在执行前发现候选冲突、禁止事项或 owner 不唯一，立即停止且不写入，给出最多 3 个候选和缺失证据；②执行失败——只允许对同一 skill 做 1 次幂等重试，第二次失败即回退到只读诊断，不自动换 owner；③用户未选择——等待 Human gate，超时不执行、不改变 artifact，并升级给指定 owner。以 30 个失败 fixture 验收：0 次失败后自动换 owner、0 次未选择时写入、100% 失败结果包含原因与 next action；任一条件不满足则状态保持 NEEDS_CONTEXT，不得标记为完成。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文 L6 将本子问题限定为生命周期阶段、唯一 owner、停止条件和 Human gate；原文 L7 又要求冲突 fixture 证明“不会……两个 skill 同时拥有同一 artifact”；原文 L12 直接追问哪些阶段和 owner 不可重叠。原文没有给出阶段集合、owner 注册规则或读写重叠判定。
- **影响**：如果只靠优先级解决冲突，优先级会掩盖两个 skill 都能写同一 artifact 的结构性错误；调用顺序一变就可能重复写入、互相覆盖，且无法判断哪个 skill 对长期状态负责。允许多个只读观察者不等于允许多个写 owner，二者必须分开建模。
- **建议**：建立不可变的阶段状态机（至少区分识别/规划、执行、验证、交接四类职责），manifest 为每个 `stage × artifact-kind` 声明一个且仅一个写 owner，并分别声明 read、write、emit 能力。机械闸门为：写 owner 数量必须等于 1；缺 owner 或大于 1 都进入 `BLOCKED_OWNER_CONFLICT`，不得执行；多个只读 skill 只能串接在 owner 之后。将该不变式加入冲突 fixture，验收标准是 0 个重复写 owner、0 次冲突计划落地。

**观点 2**

- **发现**：原文 L7 要求“同一请求能得到确定性的 stage plan 和 next action”；原文 L13 要求输入 artifact、capability manifest、precedence 和 Human gate 共同产生唯一调用路径；原文 L16-L46 的视角模板尚未规定如何把这些输入收敛为单一路径。
- **影响**：若候选发现顺序、运行时注册顺序或模型措辞参与决策，同一请求可能选出不同 skill；“优先级”也可能被误用为自动覆盖 owner 冲突的万能规则。这样既无法复现线上决策，也无法安全重试或审计。
- **建议**：实现无副作用的 resolver：先规范化请求与 artifact 版本，再按 manifest 能力过滤候选，按阶段 owner 过滤，按固定 precedence 排序，最后要求最高分候选唯一；同级并列、能力缺失、manifest 无法解析时一律 `BLOCKED_AMBIGUOUS`，不得按发现顺序猜选。输出应包含阶段序列、skill ID+manifest 版本、next action、Human gate 状态和 plan hash；机械验收为同一输入快照重复解析 100% 得到同一 hash。没有候选时返回可解释的 `UNSUPPORTED_INPUT`；有多个候选但无显式串联依赖时停止，而不是隐式串行调用。

**观点 3**

- **发现**：原文 L6 明确把 Human gate 纳入本子问题；原文 L14 追问“用户未选择时”何时停止、回退或升级；原文 L7 要求不越权写入，但当前草案没有规定批准发生在调用前还是调用后。
- **影响**：若 skill 先写入再请求确认，Human gate 失去约束力；若用户未选择时自动选默认 skill，则“未选择”会被错误解释为授权，尤其会把不可逆写入变成越权操作。不同 skill 各自弹确认还会造成一次请求多次提示和重复调用。
- **建议**：resolver 在任何不可逆写入、跨信任边界调用或 owner 冲突前产生单一 `PENDING_HUMAN` 节点；在批准前只允许只读检查，写入次数必须为 0。用户批准后仅执行已冻结的 plan hash；拒绝转 `CANCELLED_BY_HUMAN`，未选择或超过配置的 24 小时 gate TTL 转 `BLOCKED_NEEDS_SELECTION`，两者都不得自动回退或自动挑选。Human gate 必须由编排器集中发出一次，skill 本身禁止私自再开第二个 gate。

**观点 4**

- **发现**：原文 L6 明确“不重新定义 artifact 字段，也不决定具体外部 adapter”，但又要求决定 capability manifest；原文 L7 要求每个核心 skill 有明确入口、输出、禁止事项和退出条件；原文 L13 将 manifest 作为唯一调用路径的输入之一。由此可见，编排契约必须独立于具体 adapter，并且需要演进规则，草案尚未给出。
- **影响**：没有版本协商时，旧 stage plan 可能调用已改变输出语义的 skill；adapter 若直接向上暴露自己的字段或默认值，会把外部系统差异泄漏进 owner/precedence，形成不可逆耦合。静默降级还可能把“能力不存在”伪装成成功。
- **建议**：为 manifest 使用语义版本并在 plan 中固定 `skill-id + manifest-version + plan-hash`。minor 版本只允许增加可忽略字段；major 版本不兼容时必须拒绝执行（阈值为 0 次 major mismatch 自动降级）。adapter 只能实现已注册 capability，向编排器返回稳定的成功/拒绝/失败/未知结果，不得自行改变 owner 或 precedence。对每个 manifest 做入口、输出、禁止事项、退出条件的契约测试，目标为 100% 通过；skill 被移除或版本不可用时走显式 migration map，否则 `BLOCKED_CONTRACT_MISMATCH`，不寻找“看起来相似”的替代 skill。

**观点 5**

- **发现**：原文 L7 的成功判据要求“不重复调用、不越权写入”；原文 L14 要求处理 skill 误触发、失败和未选择时的停止/回退/升级；原文 L65-L73 仍将结论和沉淀指令标为待讨论，说明失败语义尚未被固定为可审计协议。
- **影响**：把所有失败都重试会重复提交非幂等操作；在结果未知时直接切换到另一个 skill，会出现两个 skill 先后拥有同一 artifact 的隐性双 owner。没有统一终止态，调用方也无法区分“可安全重试”与“必须人工核对”。
- **建议**：统一四类结果：`NOT_STARTED`、`FAILED_BEFORE_SIDE_EFFECT`、`FAILED_AFTER_SIDE_EFFECT`、`OUTCOME_UNKNOWN`。仅对无副作用或已声明幂等的动作自动重试，最多 2 次且携带同一 idempotency key；`OUTCOME_UNKNOWN` 禁止再次调用，先由原 owner 做 reconcile，仍不明则升级 Human；非幂等写入失败后不得切换 owner。只有 manifest 明确声明等价前置条件、输入契约和补偿动作时才允许显式 fallback，否则停止为 `BLOCKED_RECONCILIATION`。冲突 fixture 的硬门槛是每个 artifact 每次 plan 至多一次非幂等写调用，失败路径也不得新增第二个写 owner。

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文 L6 将范围限定为生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate，并明确“不重新定义 artifact 字段”；原文 L12 又直接追问“哪些生命周期阶段和 skill owner 是不可重叠的？”。但原文没有给出 owner 的机器判定式，也没有空 manifest、未知阶段、重复 owner 或并发请求的验收样例。
- **影响**：如果 owner 只是文档约定，同一 artifact 可能被两个 skill 同时认领，成功判据中的“不会……两个 skill 同时拥有同一 artifact”（原文 L7）无法证明。空输入会变成隐式默认 owner，重复声明会产生非确定调用；并发重放则可能把一次调用放大为多次写入。该缺口会使 Q1 不能自动验收，也会把后续 Q2/Q3 的路由结果建立在不可信前提上。
- **建议**：建立 `stage × capability × artifact` 的可执行 owner manifest，并把以下断言作为阻断闸门：每个可调用 capability 的 owner 数必须恰为 1；owner 缺失、未知、重复或同一 artifact 跨 skill 重叠时直接返回 `CONFLICT`，不生成 stage plan、不写 artifact。测试至少覆盖空 manifest、异常未知 key、极值（单请求声明全部 skill、长生命周期链）和并发（同一 request id 100 次重放）；验收为每次均得到同一个 conflict/owner 结果、调用计数为 0、越权写入数为 0。将这组 fixture 纳入 CI，任何新增 skill 先过 manifest 静态检查；失败路径固定为 `CONFLICT → Human gate`，不得静默选择第一个 owner。

**观点 2**

- **发现**：原文 L13 要求输入 artifact、capability manifest、precedence 和 Human gate 共同产生唯一调用路径，原文 L7 要求“同一请求能得到确定性的 stage plan 和 next action”。现有原文只提出输入要素，没有规定缺字段、重复 capability、优先级并列、用户未选择以及 Human gate 前后哪些动作允许发生。
- **影响**：相同语义的输入若因字段顺序、空值表示或 manifest 顺序不同而走不同路径，回归测试无法区分真实变化与序列化噪声；优先级并列若被隐式打破，两个 skill 都可能执行；Human gate 若在副作用之后才检查，则“唯一路径”仍可能造成未经授权的写入。质量证据必须能证明“对”，而不是只看到一次看似正确的结果。
- **建议**：先把 artifact/manifest 规范化（字段排序、空值统一、未知字段显式拒绝），再用版本化 precedence 表求总序；任何并列最高项都输出 `AMBIGUOUS` 并停止。对每个输入生成 `route_fingerprint = hash(normalized_input, manifest_version, precedence_version, gate_state)`，同一 fingerprint 的 100 次顺序随机重放必须得到完全相同的 stage plan、next action、调用序列和副作用摘要；输入为空、字段异常、能力重复、优先级极值、并发同 fingerprint 均纳入参数化测试。Human gate 为 `required` 时，gate 之前允许的动作只能是只读计划生成，写入/外部调用必须为 0；未选择时返回 `WAITING_FOR_HUMAN`，不回退到默认 skill。以 golden fixture 保存计划与指纹，任何差异即 CI 失败；若规范化失败或 precedence 版本缺失，固定走 `INVALID_INPUT/CONFIG_ERROR → stop`，不可猜测。

**观点 3**

- **发现**：原文 L14 同时提出 skills 误触发、失败或用户未选择时何时停止、回退或升级；原文 L7 将“不重复调用、越权写入”列为冲突 fixture 的成功判据。原文没有定义失败分类、自动重试上限、回退资格、Human gate 缺失时的状态，也没有给出并发失败或部分写入后的恢复规则。
- **影响**：没有状态机时，“失败后回退”可能再次调用同一 skill 或越权切换到另一个 owner；部分成功会留下不可重放的 artifact，重试会重复副作用；用户未选择可能被误读成同意默认方案。边界与回归风险集中在 timeout、异常、极值重试、并发竞态和半写状态，单纯 happy-path 测试无法证明系统安全停止。
- **建议**：把一次请求固定为 `PLANNED → GATED → RUNNING → SUCCEEDED/FAILED → FALLBACK 或 ESCALATED → STOPPED`，并定义可机械执行的规则：owner 冲突、权限错误、manifest 无效、Human 未选择均立即 `STOPPED/WAITING_FOR_HUMAN`；可重试的瞬态错误最多自动重试 1 次，第二次失败即 `ESCALATED`，禁止换 owner 猜测；每个副作用携带 request id + artifact version，重复 request id 的有效写入次数必须为 1，失败半写必须执行补偿或标记 `ROLLBACK_REQUIRED`，不能继续下游调用。用故障注入覆盖空/异常/极值（连续失败、超时、超长回退链）和并发（同 request 两个 worker、不同 skill 抢同 artifact）；验收要求每个 fixture 都能重现同一终态，禁止重复调用、越权写入和双 owner，且状态转移日志能还原停止原因。把这些 fixture 作为每次 skill/precedence/manifest 变更的回归套件；若状态未知、回滚失败或检测到竞态，失败路径统一升级 Human gate 并冻结后续写入，而不是继续“尽力完成”。

### 视角：U（用户研究 / UX）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现：** 原文把成功判据写成“同一请求能得到确定性的 stage plan 和 next action”，但没有规定用户能看到哪些阶段、当前为何停留、下一步由谁负责；Q2 又要求输入 artifact、capability manifest、precedence 和 Human gate 共同产生唯一调用路径（原文 L7、原文 L13）。这说明当前缺口不是再增加一个 owner，而是缺少可被人跟随的路径呈现。
- **影响：** 对熟悉内部 skill 名称的人，调用可能看似确定；对普通使用者，`stage plan` 仍是黑箱。用户会把“等待 Human gate”“没有匹配 owner”和“skill 执行失败”误认为同一种卡住，重复提交请求或手工绕过入口，造成重复调用和越权写入风险。用户流程因此无法证明是“通顺”的。
- **建议：** 为每次请求生成一个用户可见的四段状态条：`目标/输入确认 → 当前生命周期阶段 → 唯一 owner 与理由 → next action/退出条件`，只展示自然语言理由，skill key 作为可展开的技术细节。规划器必须满足 `(stage, artifact) -> exactly 1 owner`；若候选 owner 数量为 0 或大于 1，则在任何写入前停止，展示冲突项并只提一个澄清问题。若用户 2 次未回应，状态转为 `WAITING_USER`，不自动猜测、不重跑；用户补充后从规划阶段重算，而不是从中间 skill 续写。

**观点 2**

- **发现：** 原文将“输入 artifact、capability manifest、precedence 和 Human gate”并列为产生唯一调用路径的依据，却没有说明真实用户如何提供或理解这些内部概念（原文 L13）；同时，子问题明确“不重新定义 artifact 字段”（原文 L6），意味着本子问题应消费已有输入，而不是把内部 manifest 变成用户必须学习的表单。
- **影响：** 如果入口一次展示所有 manifest、优先级规则和 owner 选项，用户需要先理解系统术语才能完成任务，首屏摩擦会集中在“我该选哪个 skill”。如果系统默默补全缺失 artifact，又会把错误输入带入后续阶段。两种路径都会削弱“真实使用现场”的可用性：前者阻塞，后者隐性误导。
- **建议：** 入口只要求三类可验证信息：`用户目标`、`当前 artifact 是否存在/版本`、`是否允许产生外部或不可逆写入`；manifest、precedence 和候选 owner 默认隐藏，仅在路由不唯一或 gate 命中时按需展开。缺字段时最多连续追问 2 个问题，每个问题只对应一个缺口，并显示“回答后将进入哪个阶段”；超过 2 次仍不完整则回到 `NEEDS_CONTEXT`，保存草稿但不调用 skill。验收时以 5 条未使用内部术语的任务脚本测试入口：至少 4/5 的用户能在 30 秒内完成首轮输入且不需要解释 skill 名称，否则不得把 manifest 直接暴露给用户。

**观点 3**

- **发现：** Q3 明确询问“多个 skills 误触发、失败或用户未选择时，何时停止、回退或升级”（原文 L14），而成功判据要求冲突 fixture 证明“不重复调用、越权写入或两个 skill 同时拥有同一 artifact”（原文 L7）。原文目前没有给出这些状态的用户信号、重试次数或回退边界。
- **影响：** 没有显式状态和阈值时，系统很容易在多个候选间循环、失败后重复写入，或把用户未选择误当成同意默认项。用户看到的只是“又运行了一次”，无法判断是否需要补充信息；失败也无法区分可恢复故障与需要人工介入的冲突。
- **建议：** 固化以下状态转换和阈值：
  
  | 情况 | 用户可见状态 | 自动动作 | 失败路径 |
  | --- | --- | --- | --- |
  | 唯一 owner 且输入完整 | `READY` | 仅调用一次 | 执行失败后进入 `FAILED`，不自动换 owner |
  | owner 为 0 或 >1 | `NEEDS_SELECTION` | 不调用、不写入 | 展示候选及差异；用户未选择则保持等待，2 次无回应升级 Human |
  | 可重试的瞬时失败 | `RETRYING` | 同一 owner 最多重试 1 次 | 第二次失败进入 `FAILED`，保留日志和恢复点 |
  | 非幂等写入、权限、外部系统或不可逆动作 | `HUMAN_GATE` | 暂停在写入前 | 未确认则 `CANCELLED/WAITING_USER`，绝不以超时代替确认 |
  
  回退只能回到最近一个已验证的只读阶段；任何已写 artifact 都必须先显示变更摘要和恢复方式，禁止用另一 skill“接管”来掩盖失败。

**观点 4**

- **发现：** 原文把 Human gate 列入唯一调用路径的决定因素（原文 L13），但没有区分“需要确认”与“需要补充信息”，也没有定义确认后用户能看到的后果。成功判据只说有 Human gate，并未覆盖可达性/无障碍（原文 L7）。
- **影响：** gate 过多会让用户在每个低风险阶段都被打断，gate 过少则可能默许危险写入。若确认界面依赖颜色、鼠标悬停或晦涩的 skill 名称，键盘用户、屏幕阅读器用户或认知负担较高的用户无法获得等价决策信息；“用户未选择”的失败路径也会变成无声超时。
- **建议：** 只在三类条件触发 gate：不可逆/外部写入、权限边界变化、或 owner 仍不唯一；只读规划和幂等校验不弹 gate。确认卡片必须用纯文本说明“将由谁、在什么 artifact 上、产生什么变化、如何撤销”，提供键盘可达的 `确认/返回/取消` 操作、焦点回收、状态文本和不依赖颜色的错误提示。默认焦点放在“返回/查看详情”，不得把确认按钮作为隐式默认。用户 60 秒无操作时保持 `HUMAN_GATE`，不自动通过；连续 2 次取消则建议回到输入修正，而不是重新触发同一 gate。

**观点 5**

- **发现：** 原文只规定“每个核心 skill 有明确入口/输出/禁止事项/退出条件”，以及冲突 fixture 要证明不重复调用、不越权写入、不共享 artifact owner（原文 L7）；没有规定普通用户是否能识别入口、理解输出、从失败恢复，也没有把用户体验证据写入退出条件。
- **影响：** 内部 fixture 即使全绿，也可能只证明机器遵守规则，不能证明用户知道下一步或能在失败后恢复。若体验问题在 skill 执行后才暴露，修复成本会从入口提示扩大到整个生命周期；没有指标时，团队会把“路由成功”误报为“任务完成”。
- **建议：** 在每个核心 skill 的退出条件中追加用户侧验收：准备至少 5 条真实任务轨迹（正常完成、owner 冲突、输入缺失、skill 失败、Human gate 未确认），每条记录用户目标、看到的 next action、实际结果和是否产生写入。发布前要求：至少 4/5 条轨迹能让首次使用者在 30 秒内说出下一步；失败路径 100% 显示可恢复状态和恢复入口；冲突/未选择 fixture 100% 不调用、不写入；键盘全流程 100% 可完成。任一阈值不达标，skill 状态不得从 `DRAFT` 转为可用，回退到入口或状态文案修正，而不是放宽 gate 或增加自动重试。

### 视角：P（流程 / 组织协作）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现：** 原文把本子问题限定为“生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate”，并明确“不重新定义 artifact 字段，也不决定具体外部 adapter”（原文 L6）；但 Q1 只提出“哪些生命周期阶段和 skill owner 是不可重叠的”，没有责任到岗、交接输入或 owner 缺席时的替补规则（原文 L10-L14）。
- **影响：** 若只登记 capability，不登记每个阶段的单一负责人，两个 skill 可能都认为自己可以接管同一 artifact；交接失败时团队会靠意愿互相等待。这样即使最终输出字段正确，也无法满足“不会两个 skill 同时拥有同一 artifact”的成功判据（原文 L7）。
- **建议：** 为每个生命周期阶段建立一张可审计的“阶段责任卡”：`stage_id`、唯一 `owner_skill`、输入 artifact 状态、输出状态、禁止动作、交接接收者、Human gate、替补/升级者。规定 `owner_skill` 必须恰为 1 个；owner 只能在输出状态写入后释放 artifact，接收者确认后才获得写锁。若 10 分钟内无人确认交接，自动转为 `BLOCKED_HANDOFF` 并升级给流程维护者；任何没有 owner 或 owner 数量大于 1 的 manifest，直接拒绝生成 stage plan。

**观点 2**

- **发现：** 原文要求“同一请求能得到确定性的 stage plan 和 next action”，并把输入 artifact、capability manifest、precedence 和 Human gate列为 Q2 的联合决策输入（原文 L7、L13）；但当前文本没有规定谁负责读取输入、谁发布 plan、下游 skill 如何确认或拒绝。
- **影响：** 缺少统一路由角色会出现多入口并行解释：上游以为已派单，下游却按自己的 capability 再次触发；用户看到的是重复调用或没有 next action。跨角色协作接口也不可追责，因为无法区分“manifest 不匹配”和“执行者未接单”。
- **建议：** 指定一个不拥有业务 artifact 的 `orchestrator` 作为唯一派单人，按以下顺序产出不可变 `stage_plan`：①校验 artifact 状态；②筛选 capability 命中者；③按 precedence 排序；④应用 Human gate；⑤只发一个 `next_action`。每个派单必须含 `plan_id`、当前 owner、候选 skill 列表、选择理由、接收确认期限和拒绝码；skill 只能返回 `ACCEPT`、`DECLINE(reason)` 或 `BLOCKED(missing_input)`，不能自行改派。5 分钟内未 ACK 记一次路由阻塞；同一 `plan_id` 出现两个 `ACCEPT` 时立即冻结写入并进入冲突仲裁。

**观点 3**

- **发现：** 原文的成功判据明确要求冲突 fixture 证明“不重复调用、越权写入或两个 skill 同时拥有同一 artifact”（原文 L7）；Q2 又要求 precedence 产生唯一调用路径，而 Q3 直接询问多个 skill 误触发时何时停止、回退或升级（原文 L13-L14）。这说明冲突不只是算法排序问题，还需要执行中的占有与回收机制。
- **影响：** 没有可见锁和幂等约束时，两个团队都可能先写后报；后续即使按优先级撤销，也会留下不可逆副作用。失败时若按“再试一次”处理，重复调用会放大外部成本，并使责任边界无法复盘。
- **建议：** 将 `artifact_id + stage_id + plan_id` 作为幂等键，并采用租约式写锁：最高 precedence 的 skill 获得 1 个 15 分钟租约，续租不得超过 2 次；低优先级命中者只能观察或返回 `SHADOWED`，不得写入。任何已存在锁的第二次调用必须在 fixture 中记录为“未执行调用”，而不是执行后去重。租约过期前不得抢占；过期后先进入 2 分钟仲裁窗口，仍无 owner 心跳才由 orchestrator 回收并重派。出现一次越权写入或同一 artifact 双 owner，立即停止该 plan、冻结 artifact、保留审计日志，并升级 Human，而不是自动回滚未知副作用。

**观点 4**

- **发现：** Q3 明确包含“用户未选择时，何时停止、回退或升级”（原文 L14），而成功判据要求每个核心 skill 有入口、输出、禁止事项和退出条件（原文 L7）。现有原文没有定义 Human 需要选择什么、多久未响应算未选择，也没有区分低风险默认值与不可逆动作。
- **影响：** Human gate 若只显示“请选择 skill”，用户无法判断后果；若系统擅自替用户选择，又会突破职责边界。结果可能是请求停滞、反复追问，或在高风险场景静默越权，流程阻力集中在用户而非编排机制。
- **建议：** gate 只允许三种明确结果：`APPROVE(plan_id)`、`REJECT(reason)`、`CHOOSE(candidate_id)`；决策包必须同时展示候选 skill、precedence 依据、将写入的 artifact、禁止动作、预计副作用和撤销能力。低风险、可逆且唯一候选可在 30 秒无响应后采用默认路径；存在两个以上同优先级候选、不可逆写入、权限扩大或缺少 artifact 时，0 秒自动执行，直接 `WAITING_FOR_HUMAN`。用户拒绝后最多重算 1 次；仍无可行路径就升级并停止，不循环追问。

**观点 5**

- **发现：** 原文把“多个 skills 误触发、失败或用户未选择”合并为 Q3，并要求明确停止、回退或升级（原文 L14）；同时要求每个 skill 有退出条件，且冲突 fixture 要证明不会重复调用和越权写入（原文 L7）。但当前 scope 草案没有失败分类、重试上限、回退 owner 或升级接收者。
- **影响：** 若所有失败都回退到上一个 skill，可能重新触发同一错误；若所有失败都升级 Human，又会把可自动修复的输入缺失变成运营噪音。团队也无法知道是 capability 缺口、执行故障、权限问题还是用户决策阻塞，后续无法修正流程。
- **建议：** 固定四级失败阶梯并在每级指定责任人：`MISSING_INPUT` 由当前 owner 一次性列出缺口并暂停；`DECLINED` 由 orchestrator 按 precedence 只尝试 1 个次选；`RETRYABLE_ERROR` 由原 owner指数退避重试最多 2 次；`CONFLICT/UNSAFE` 立即冻结 artifact 并升级 Human/流程负责人。任一级超过 15 分钟或累计 2 次失败，停止自动推进，生成含 `plan_id`、owner、失败码、已尝试动作、下一责任人的升级单。每次升级必须在 1 个工作周期内由责任人确认；未确认则升级到子问题 owner，并把失败 fixture 纳入下一轮验收。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

独立观点已通过 scope、架构和 UX 闸门。本题采用声明式 capability manifest + 确定性 resolver + 单写 owner + 可暂停状态机，把“skill 会不会抢活/越权/无限重试”变成可测协议。

1. 每个原子 skill manifest 必须登记 `skill_id/version/stage/input/output/forbidden/required_capabilities/stop_condition/owner/precedence/failure_fixture`；阶段责任卡保证 `(stage, artifact) → exactly one owner`。manifest 与 artifact schema 解耦，plan 固定 `skill_id + manifest_version + plan_hash`。

2. resolver 顺序固定为：校验 artifact/schema → 过滤 forbidden → 匹配 capability → 按 precedence 排序 → 唯一候选才生成 plan → 判断 Human gate → 只发一个 next_action。并列、缺字段、owner 不唯一或权限扩大时立即 `WAITING_FOR_HUMAN/NEEDS_CONTEXT`，不猜、不自动换 owner。

3. 执行采用 `plan_id` 与 `artifact_id + stage_id` 幂等键、租约写锁和 `ACCEPT/DECLINE/BLOCKED` 响应；skill 不能自行改派。失败阶梯为 missing input 暂停、decline 只试一个次选、retryable error 由原 owner 有界重试、conflict/unsafe 立即冻结并升级。任何双 owner/越权写入冻结 plan 并保留审计。

4. 验收以 20 个路由 fixture 证明至少 18/20 可由匹配条件+precedence 解释、0 次重复调用；30 个失败 fixture 证明 0 次自动换 owner、0 次未确认写入、100% 有 reason/next action；另用 10 条真实/历史请求验证默认路由相对手工路由决策时间至少改善 20%。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | U | 同 provider 跨会话 | 待拍板 | 否 | |
| 6 | P | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** Skill 编排应是声明式、确定性的状态机，而不是把多个 prompt 串起来。每个阶段和 artifact 只能有一个默认写 owner；无法唯一解析时必须暂停并把理由交给 Human。
- **解法：** 以 capability manifest、stage responsibility card、precedence、plan hash、租约写锁和幂等键实现 resolver；执行/失败都产出可审计状态。唯一候选的低风险只读计划可自动推进；外部写入、权限变化、并列候选和不可逆动作必须 Human gate。
- **remaining-risks 控制：** 新 skill 可能与旧 manifest/owner 冲突，长期 precedence 也会漂移；通过版本锁、冲突 fixture、plan hash、停止条件、租约和发布前回归控制。无法判定的请求保持 `NEEDS_CONTEXT`，不以“相似 skill”自动替代。
- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增 Skill Capability Manifest、Resolver/Precedence 和 Failure State Machine ADR；每个 skill 的 SKILL.md 必须包含输入、输出、禁止事项、依赖、停止条件和失败 fixture。
  - 跨子文档约束登记：`sub-01` 的字段语义不可由 skill 改写；`sub-03` adapter 只能作为已注册 capability；`sub-04` policy/approval 是 resolver 的前置；`sub-05` verification gate 先于自动修复。
  - 待删临时脚手架：本子文档 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；Human 确认前保留讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

