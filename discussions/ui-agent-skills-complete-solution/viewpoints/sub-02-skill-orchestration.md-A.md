### 视角：A（架构师 / 约束）

`视角来源: 跨会话独立Agent`

#### **观点 1：用“阶段—artifact—owner”不变式封住不可重叠边界（回答 Q1）**

- **发现**：原文 L6 将本子问题限定为生命周期阶段、唯一 owner、停止条件和 Human gate；原文 L7 又要求冲突 fixture 证明“不会……两个 skill 同时拥有同一 artifact”；原文 L12 直接追问哪些阶段和 owner 不可重叠。原文没有给出阶段集合、owner 注册规则或读写重叠判定。
- **影响**：如果只靠优先级解决冲突，优先级会掩盖两个 skill 都能写同一 artifact 的结构性错误；调用顺序一变就可能重复写入、互相覆盖，且无法判断哪个 skill 对长期状态负责。允许多个只读观察者不等于允许多个写 owner，二者必须分开建模。
- **建议**：建立不可变的阶段状态机（至少区分识别/规划、执行、验证、交接四类职责），manifest 为每个 `stage × artifact-kind` 声明一个且仅一个写 owner，并分别声明 read、write、emit 能力。机械闸门为：写 owner 数量必须等于 1；缺 owner 或大于 1 都进入 `BLOCKED_OWNER_CONFLICT`，不得执行；多个只读 skill 只能串接在 owner 之后。将该不变式加入冲突 fixture，验收标准是 0 个重复写 owner、0 次冲突计划落地。

#### **观点 2：把编排做成纯函数解析器，确保同一输入只有一个 stage plan（回答 Q2）**

- **发现**：原文 L7 要求“同一请求能得到确定性的 stage plan 和 next action”；原文 L13 要求输入 artifact、capability manifest、precedence 和 Human gate 共同产生唯一调用路径；原文 L16-L46 的视角模板尚未规定如何把这些输入收敛为单一路径。
- **影响**：若候选发现顺序、运行时注册顺序或模型措辞参与决策，同一请求可能选出不同 skill；“优先级”也可能被误用为自动覆盖 owner 冲突的万能规则。这样既无法复现线上决策，也无法安全重试或审计。
- **建议**：实现无副作用的 resolver：先规范化请求与 artifact 版本，再按 manifest 能力过滤候选，按阶段 owner 过滤，按固定 precedence 排序，最后要求最高分候选唯一；同级并列、能力缺失、manifest 无法解析时一律 `BLOCKED_AMBIGUOUS`，不得按发现顺序猜选。输出应包含阶段序列、skill ID+manifest 版本、next action、Human gate 状态和 plan hash；机械验收为同一输入快照重复解析 100% 得到同一 hash。没有候选时返回可解释的 `UNSUPPORTED_INPUT`；有多个候选但无显式串联依赖时停止，而不是隐式串行调用。

#### **观点 3：Human gate 是副作用前的不变式，不是事后提示（回答 Q3）**

- **发现**：原文 L6 明确把 Human gate 纳入本子问题；原文 L14 追问“用户未选择时”何时停止、回退或升级；原文 L7 要求不越权写入，但当前草案没有规定批准发生在调用前还是调用后。
- **影响**：若 skill 先写入再请求确认，Human gate 失去约束力；若用户未选择时自动选默认 skill，则“未选择”会被错误解释为授权，尤其会把不可逆写入变成越权操作。不同 skill 各自弹确认还会造成一次请求多次提示和重复调用。
- **建议**：resolver 在任何不可逆写入、跨信任边界调用或 owner 冲突前产生单一 `PENDING_HUMAN` 节点；在批准前只允许只读检查，写入次数必须为 0。用户批准后仅执行已冻结的 plan hash；拒绝转 `CANCELLED_BY_HUMAN`，未选择或超过配置的 24 小时 gate TTL 转 `BLOCKED_NEEDS_SELECTION`，两者都不得自动回退或自动挑选。Human gate 必须由编排器集中发出一次，skill 本身禁止私自再开第二个 gate。

#### **观点 4：用 manifest 版本协商隔离向后兼容风险，禁止 adapter 反向定义编排契约**

- **发现**：原文 L6 明确“不重新定义 artifact 字段，也不决定具体外部 adapter”，但又要求决定 capability manifest；原文 L7 要求每个核心 skill 有明确入口、输出、禁止事项和退出条件；原文 L13 将 manifest 作为唯一调用路径的输入之一。由此可见，编排契约必须独立于具体 adapter，并且需要演进规则，草案尚未给出。
- **影响**：没有版本协商时，旧 stage plan 可能调用已改变输出语义的 skill；adapter 若直接向上暴露自己的字段或默认值，会把外部系统差异泄漏进 owner/precedence，形成不可逆耦合。静默降级还可能把“能力不存在”伪装成成功。
- **建议**：为 manifest 使用语义版本并在 plan 中固定 `skill-id + manifest-version + plan-hash`。minor 版本只允许增加可忽略字段；major 版本不兼容时必须拒绝执行（阈值为 0 次 major mismatch 自动降级）。adapter 只能实现已注册 capability，向编排器返回稳定的成功/拒绝/失败/未知结果，不得自行改变 owner 或 precedence。对每个 manifest 做入口、输出、禁止事项、退出条件的契约测试，目标为 100% 通过；skill 被移除或版本不可用时走显式 migration map，否则 `BLOCKED_CONTRACT_MISMATCH`，不寻找“看起来相似”的替代 skill。

#### **观点 5：失败恢复按副作用状态分级，回退不能制造第二个 owner**

- **发现**：原文 L7 的成功判据要求“不重复调用、不越权写入”；原文 L14 要求处理 skill 误触发、失败和未选择时的停止/回退/升级；原文 L65-L73 仍将结论和沉淀指令标为待讨论，说明失败语义尚未被固定为可审计协议。
- **影响**：把所有失败都重试会重复提交非幂等操作；在结果未知时直接切换到另一个 skill，会出现两个 skill 先后拥有同一 artifact 的隐性双 owner。没有统一终止态，调用方也无法区分“可安全重试”与“必须人工核对”。
- **建议**：统一四类结果：`NOT_STARTED`、`FAILED_BEFORE_SIDE_EFFECT`、`FAILED_AFTER_SIDE_EFFECT`、`OUTCOME_UNKNOWN`。仅对无副作用或已声明幂等的动作自动重试，最多 2 次且携带同一 idempotency key；`OUTCOME_UNKNOWN` 禁止再次调用，先由原 owner 做 reconcile，仍不明则升级 Human；非幂等写入失败后不得切换 owner。只有 manifest 明确声明等价前置条件、输入契约和补偿动作时才允许显式 fallback，否则停止为 `BLOCKED_RECONCILIATION`。冲突 fixture 的硬门槛是每个 artifact 每次 plan 至多一次非幂等写调用，失败路径也不得新增第二个写 owner。

