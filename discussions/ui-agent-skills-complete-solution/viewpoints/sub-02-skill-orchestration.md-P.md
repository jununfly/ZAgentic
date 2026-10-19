### 视角：P（流程 / 组织协作）

`视角来源: 跨会话独立Agent`

#### 观点 1：用“阶段责任卡”锁死唯一 owner，而不是只写 skill 能力

- **发现：** 原文把本子问题限定为“生命周期阶段、skill capability manifest、唯一 owner、优先级、停止条件和 Human gate”，并明确“不重新定义 artifact 字段，也不决定具体外部 adapter”（原文 L6）；但 Q1 只提出“哪些生命周期阶段和 skill owner 是不可重叠的”，没有责任到岗、交接输入或 owner 缺席时的替补规则（原文 L10-L14）。
- **影响：** 若只登记 capability，不登记每个阶段的单一负责人，两个 skill 可能都认为自己可以接管同一 artifact；交接失败时团队会靠意愿互相等待。这样即使最终输出字段正确，也无法满足“不会两个 skill 同时拥有同一 artifact”的成功判据（原文 L7）。
- **建议：** 为每个生命周期阶段建立一张可审计的“阶段责任卡”：`stage_id`、唯一 `owner_skill`、输入 artifact 状态、输出状态、禁止动作、交接接收者、Human gate、替补/升级者。规定 `owner_skill` 必须恰为 1 个；owner 只能在输出状态写入后释放 artifact，接收者确认后才获得写锁。若 10 分钟内无人确认交接，自动转为 `BLOCKED_HANDOFF` 并升级给流程维护者；任何没有 owner 或 owner 数量大于 1 的 manifest，直接拒绝生成 stage plan。

#### 观点 2：把 capability manifest 变成“值班路由单”，让协作接口可执行

- **发现：** 原文要求“同一请求能得到确定性的 stage plan 和 next action”，并把输入 artifact、capability manifest、precedence 和 Human gate列为 Q2 的联合决策输入（原文 L7、L13）；但当前文本没有规定谁负责读取输入、谁发布 plan、下游 skill 如何确认或拒绝。
- **影响：** 缺少统一路由角色会出现多入口并行解释：上游以为已派单，下游却按自己的 capability 再次触发；用户看到的是重复调用或没有 next action。跨角色协作接口也不可追责，因为无法区分“manifest 不匹配”和“执行者未接单”。
- **建议：** 指定一个不拥有业务 artifact 的 `orchestrator` 作为唯一派单人，按以下顺序产出不可变 `stage_plan`：①校验 artifact 状态；②筛选 capability 命中者；③按 precedence 排序；④应用 Human gate；⑤只发一个 `next_action`。每个派单必须含 `plan_id`、当前 owner、候选 skill 列表、选择理由、接收确认期限和拒绝码；skill 只能返回 `ACCEPT`、`DECLINE(reason)` 或 `BLOCKED(missing_input)`，不能自行改派。5 分钟内未 ACK 记一次路由阻塞；同一 `plan_id` 出现两个 `ACCEPT` 时立即冻结写入并进入冲突仲裁。

#### 观点 3：用“优先级 + 锁 + 幂等键”处理误触发，避免组织协作退化成抢写

- **发现：** 原文的成功判据明确要求冲突 fixture 证明“不重复调用、越权写入或两个 skill 同时拥有同一 artifact”（原文 L7）；Q2 又要求 precedence 产生唯一调用路径，而 Q3 直接询问多个 skill 误触发时何时停止、回退或升级（原文 L13-L14）。这说明冲突不只是算法排序问题，还需要执行中的占有与回收机制。
- **影响：** 没有可见锁和幂等约束时，两个团队都可能先写后报；后续即使按优先级撤销，也会留下不可逆副作用。失败时若按“再试一次”处理，重复调用会放大外部成本，并使责任边界无法复盘。
- **建议：** 将 `artifact_id + stage_id + plan_id` 作为幂等键，并采用租约式写锁：最高 precedence 的 skill 获得 1 个 15 分钟租约，续租不得超过 2 次；低优先级命中者只能观察或返回 `SHADOWED`，不得写入。任何已存在锁的第二次调用必须在 fixture 中记录为“未执行调用”，而不是执行后去重。租约过期前不得抢占；过期后先进入 2 分钟仲裁窗口，仍无 owner 心跳才由 orchestrator 回收并重派。出现一次越权写入或同一 artifact 双 owner，立即停止该 plan、冻结 artifact、保留审计日志，并升级 Human，而不是自动回滚未知副作用。

#### 观点 4：把 Human gate 设计成可回答的决策包，并设置“歧义即停”阈值

- **发现：** Q3 明确包含“用户未选择时，何时停止、回退或升级”（原文 L14），而成功判据要求每个核心 skill 有入口、输出、禁止事项和退出条件（原文 L7）。现有原文没有定义 Human 需要选择什么、多久未响应算未选择，也没有区分低风险默认值与不可逆动作。
- **影响：** Human gate 若只显示“请选择 skill”，用户无法判断后果；若系统擅自替用户选择，又会突破职责边界。结果可能是请求停滞、反复追问，或在高风险场景静默越权，流程阻力集中在用户而非编排机制。
- **建议：** gate 只允许三种明确结果：`APPROVE(plan_id)`、`REJECT(reason)`、`CHOOSE(candidate_id)`；决策包必须同时展示候选 skill、precedence 依据、将写入的 artifact、禁止动作、预计副作用和撤销能力。低风险、可逆且唯一候选可在 30 秒无响应后采用默认路径；存在两个以上同优先级候选、不可逆写入、权限扩大或缺少 artifact 时，0 秒自动执行，直接 `WAITING_FOR_HUMAN`。用户拒绝后最多重算 1 次；仍无可行路径就升级并停止，不循环追问。

#### 观点 5：建立失败回退阶梯和复盘责任，避免“失败重试”吞掉阻塞

- **发现：** 原文把“多个 skills 误触发、失败或用户未选择”合并为 Q3，并要求明确停止、回退或升级（原文 L14）；同时要求每个 skill 有退出条件，且冲突 fixture 要证明不会重复调用和越权写入（原文 L7）。但当前 scope 草案没有失败分类、重试上限、回退 owner 或升级接收者。
- **影响：** 若所有失败都回退到上一个 skill，可能重新触发同一错误；若所有失败都升级 Human，又会把可自动修复的输入缺失变成运营噪音。团队也无法知道是 capability 缺口、执行故障、权限问题还是用户决策阻塞，后续无法修正流程。
- **建议：** 固定四级失败阶梯并在每级指定责任人：`MISSING_INPUT` 由当前 owner 一次性列出缺口并暂停；`DECLINED` 由 orchestrator 按 precedence 只尝试 1 个次选；`RETRYABLE_ERROR` 由原 owner指数退避重试最多 2 次；`CONFLICT/UNSAFE` 立即冻结 artifact 并升级 Human/流程负责人。任一级超过 15 分钟或累计 2 次失败，停止自动推进，生成含 `plan_id`、owner、失败码、已尝试动作、下一责任人的升级单。每次升级必须在 1 个工作周期内由责任人确认；未确认则升级到子问题 owner，并把失败 fixture 纳入下一轮验收。
