### 视角：T

`视角来源: 跨会话独立Agent`

#### **观点 1：Q1 必须先被编译成“唯一 owner”可判定的契约，而不是靠阶段命名约定**

- **发现**：原文 L6 将范围限定为生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate，并明确“不重新定义 artifact 字段”；原文 L12 又直接追问“哪些生命周期阶段和 skill owner 是不可重叠的？”。但原文没有给出 owner 的机器判定式，也没有空 manifest、未知阶段、重复 owner 或并发请求的验收样例。
- **影响**：如果 owner 只是文档约定，同一 artifact 可能被两个 skill 同时认领，成功判据中的“不会……两个 skill 同时拥有同一 artifact”（原文 L7）无法证明。空输入会变成隐式默认 owner，重复声明会产生非确定调用；并发重放则可能把一次调用放大为多次写入。该缺口会使 Q1 不能自动验收，也会把后续 Q2/Q3 的路由结果建立在不可信前提上。
- **建议**：建立 `stage × capability × artifact` 的可执行 owner manifest，并把以下断言作为阻断闸门：每个可调用 capability 的 owner 数必须恰为 1；owner 缺失、未知、重复或同一 artifact 跨 skill 重叠时直接返回 `CONFLICT`，不生成 stage plan、不写 artifact。测试至少覆盖空 manifest、异常未知 key、极值（单请求声明全部 skill、长生命周期链）和并发（同一 request id 100 次重放）；验收为每次均得到同一个 conflict/owner 结果、调用计数为 0、越权写入数为 0。将这组 fixture 纳入 CI，任何新增 skill 先过 manifest 静态检查；失败路径固定为 `CONFLICT → Human gate`，不得静默选择第一个 owner。

#### **观点 2：Q2 的唯一调用路径应以“规范化输入 + 优先级总序 + 可重放指纹”证明**

- **发现**：原文 L13 要求输入 artifact、capability manifest、precedence 和 Human gate 共同产生唯一调用路径，原文 L7 要求“同一请求能得到确定性的 stage plan 和 next action”。现有原文只提出输入要素，没有规定缺字段、重复 capability、优先级并列、用户未选择以及 Human gate 前后哪些动作允许发生。
- **影响**：相同语义的输入若因字段顺序、空值表示或 manifest 顺序不同而走不同路径，回归测试无法区分真实变化与序列化噪声；优先级并列若被隐式打破，两个 skill 都可能执行；Human gate 若在副作用之后才检查，则“唯一路径”仍可能造成未经授权的写入。质量证据必须能证明“对”，而不是只看到一次看似正确的结果。
- **建议**：先把 artifact/manifest 规范化（字段排序、空值统一、未知字段显式拒绝），再用版本化 precedence 表求总序；任何并列最高项都输出 `AMBIGUOUS` 并停止。对每个输入生成 `route_fingerprint = hash(normalized_input, manifest_version, precedence_version, gate_state)`，同一 fingerprint 的 100 次顺序随机重放必须得到完全相同的 stage plan、next action、调用序列和副作用摘要；输入为空、字段异常、能力重复、优先级极值、并发同 fingerprint 均纳入参数化测试。Human gate 为 `required` 时，gate 之前允许的动作只能是只读计划生成，写入/外部调用必须为 0；未选择时返回 `WAITING_FOR_HUMAN`，不回退到默认 skill。以 golden fixture 保存计划与指纹，任何差异即 CI 失败；若规范化失败或 precedence 版本缺失，固定走 `INVALID_INPUT/CONFIG_ERROR → stop`，不可猜测。

#### **观点 3：Q3 必须用故障注入状态机定义停止、回退和升级，且把幂等与回滚作为验收证据**

- **发现**：原文 L14 同时提出 skills 误触发、失败或用户未选择时何时停止、回退或升级；原文 L7 将“不重复调用、越权写入”列为冲突 fixture 的成功判据。原文没有定义失败分类、自动重试上限、回退资格、Human gate 缺失时的状态，也没有给出并发失败或部分写入后的恢复规则。
- **影响**：没有状态机时，“失败后回退”可能再次调用同一 skill 或越权切换到另一个 owner；部分成功会留下不可重放的 artifact，重试会重复副作用；用户未选择可能被误读成同意默认方案。边界与回归风险集中在 timeout、异常、极值重试、并发竞态和半写状态，单纯 happy-path 测试无法证明系统安全停止。
- **建议**：把一次请求固定为 `PLANNED → GATED → RUNNING → SUCCEEDED/FAILED → FALLBACK 或 ESCALATED → STOPPED`，并定义可机械执行的规则：owner 冲突、权限错误、manifest 无效、Human 未选择均立即 `STOPPED/WAITING_FOR_HUMAN`；可重试的瞬态错误最多自动重试 1 次，第二次失败即 `ESCALATED`，禁止换 owner 猜测；每个副作用携带 request id + artifact version，重复 request id 的有效写入次数必须为 1，失败半写必须执行补偿或标记 `ROLLBACK_REQUIRED`，不能继续下游调用。用故障注入覆盖空/异常/极值（连续失败、超时、超长回退链）和并发（同 request 两个 worker、不同 skill 抢同 artifact）；验收要求每个 fixture 都能重现同一终态，禁止重复调用、越权写入和双 owner，且状态转移日志能还原停止原因。把这些 fixture 作为每次 skill/precedence/manifest 变更的回归套件；若状态未知、回滚失败或检测到竞态，失败路径统一升级 Human gate 并冻结后续写入，而不是继续“尽力完成”。
