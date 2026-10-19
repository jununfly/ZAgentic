视角来源: 跨会话独立Agent

**观点 1：scope manifest 必须先成为可执行的测试边界**

- **发现**：原文把本子问题限定为锁定“第一版垂直切片、纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准”，并明确“不重新设计 artifact、adapter 或安全机制”（原文 L6）；同时成功判据要求每个纳入 skill 具备“输入/输出/禁止事项/依赖/停止条件/失败 fixture”（原文 L7）。但当前 scope 草案没有给出 manifest 的字段、冻结时点、fixture 完整性判定或超范围行为的处置。
- **影响**：若没有冻结的 manifest，测试会在运行中偷偷扩大纳入范围，导致 baseline 与 Experience Version 比较的对象不一致；缺少失败 fixture 还会把“异常路径没有验证”误报成“代码能跑”。这会直接污染返工率、用户决策时间和 escaped UI defects 三项证据，且无法判断失败来自 skill、adapter、环境还是测试数据。
- **建议**：在 Wave 0 产出并签名一份 scope manifest，至少固定切片入口、纳入/排除的 skill 与 adapter、每个 skill 的六项契约字段、fixture ID/预期失败类型、依赖版本、浏览器/数据/权限前提、指标采集规则和 owner。manifest 变更必须触发重评；未登记的能力只能标记为 out-of-scope，不能进入 graduation 分母。验收条件是：每个纳入项都能映射到一个成功 fixture、一个失败 fixture 和一条可复现命令；任一缺项则 Wave 0 不退出。

**观点 2：Wave 0–3 应按“证据先于实现”设置退出和回退**

- **发现**：原文只提出“Wave 0–3 的依赖顺序、责任、退出条件和失败回退是什么”（原文 L13），没有给出顺序本身；而成功判据要求至少三次完整运行并相对 direct-prompt baseline 改善（原文 L7）。因此不能把四个 Wave 仅当作开发阶段，也不能用某个页面能运行替代 Wave 退出证据。
- **影响**：没有逐 Wave 的可复现退出条件，会出现先跑体验、后补契约和 baseline 的顺序错误；一旦后补测量，前面的“改善”无法追溯，失败时也无法知道应回退实现、回退 scope 还是暂停整条 Experience Version。跨 Wave 的回归风险会在最后一次运行才集中暴露。
- **建议**：采用以下测试闸门和责任映射：Wave 0 由 scope/测量 owner 负责，冻结 manifest、fixture、随机化/配对方案和 direct-prompt baseline，缺一项即回到准备态；Wave 1 由 skill/adapter owner 负责，逐项验证输入/输出/禁止事项/依赖/停止条件及失败 fixture，契约或适配失败时只能 fallback 到已知稳定路径并记录原因；Wave 2 由垂直切片 owner 与测试 owner 负责，完成端到端 UI 流程、异常路径和人工体验 gate，发现 flaky fixture 或非确定性 adapter 时 quarantine，不得吞掉失败；Wave 3 由独立验收 owner 负责，执行三次 paired run、回归和 graduation review，任一硬闸门失败则回到最近一个通过的 Wave 或将状态降为 `NEEDS_CONTEXT`。每个 Wave 的退出记录都应包含运行 ID、版本、fixture、结果和未关闭风险。

**观点 3：baseline 和三次 paired run 必须先注册比较协议，才能证明改善**

- **发现**：原文要求“至少三次完整运行相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善”（原文 L7），并把 Q3 明确写成“如何设计 baseline、三次运行和 graduation criteria，避免‘代码能跑’冒充成功”（原文 L14）。原文没有规定一对运行的任务、人员、输入、时间预算、环境、顺序和指标口径如何保持可比。
- **影响**：如果 baseline 与 Experience Version 使用不同任务难度、不同 fixture、不同浏览器状态或不同时间预算，三项指标的变化可能只是实验偏差；若把三次单独操作误作三次完整运行，样本不足以覆盖失败分支。尤其是用户决策时间会受学习效应影响，返工率会受任务复杂度影响，escaped UI defects 又依赖运行后的人工复查，三者不能只靠日志中的“成功”字段推断。
- **建议**：在 Wave 0 预注册 paired-run protocol：每次 run 使用同一批已锁定任务/fixture、相同角色权限和环境快照，分别执行 direct-prompt 与 Experience Version，记录运行前后版本、输入、时长、用户决策起止事件、返工定义、缺陷严重度及复核者；对任务顺序做 counterbalance，避免三次都由熟悉 Experience Version 的同一顺序驱动。三次 run 必须各自完整覆盖成功与失败 fixture，并保留原始事件和屏幕/DOM 证据；缺事件、换环境或中途人工修补的 pair 标为 invalid，不能补算为改善。

**观点 4：graduation 是质量证据闸门，不是“代码能跑”标签**

- **发现**：原文成功判据把“锁定一个 React/Next.js 表单或审批流”、skill 契约和“三次完整运行相对 direct-prompt baseline 的改善”放在同一组，并明确本轮“不承诺 release/rollout/version-skew”（原文 L7）；Q3 又要求避免“代码能跑”冒充成功（原文 L14）。这意味着 graduation 至少要同时证明范围、契约、行为和对照指标，而不能只依赖构建或冒烟通过。
- **影响**：若只设自动化构建/端到端 happy path 作为毕业条件，空输入、异常响应、重复提交、权限边界、长文本、并发点击和 adapter 超时等边界失败会以 escaped UI defects 形式逃逸；若三次运行中有一次严重回归仍允许毕业，平均改善会掩盖不可接受的单次事故。由于不承诺 release/rollout/version-skew，毕业也不能被解释成生产发布许可。
- **建议**：将 graduation 设为联合闸门：scope manifest 完整且无未评估变更；所有纳入 skill 的六项契约和失败 fixture 通过；React/Next.js 目标流的成功、失败、空/异常/极值、重复/并发和权限场景有可复现证据；三次 paired run 全部有效，三项预注册指标在聚合结果上优于 direct-prompt baseline，且任一 run 不得出现未接受的 critical/high escaped UI defect 或不可解释的指标恶化；人工复核确认用户决策时间的起止事件和视觉/交互缺陷。任一条件不满足只能保持候选态或降为 `NEEDS_CONTEXT`，不能以“代码可运行”替代。

**观点 5：不同风险必须使用不同控制，不可用单一自动化闸门兜底**

- **发现**：原文把失败回退列为 Wave 顺序问题的一部分（原文 L13），把 escaped UI defects 列为成功指标（原文 L7），并明确不承诺 release/rollout/version-skew（原文 L7）。这些风险的可观测性和可逆性不同：代码/契约失败可自动复现，视觉和用户决策质量需要人看，fixture 非确定性会污染统计，版本或 scope 改变则会使既有证据失效。
- **影响**：把所有异常都记成测试失败会掩盖安全的降级路径；把所有异常都自动 fallback 又可能悄悄改变被测系统；把 flaky 结果留在样本中会制造虚假改善；把旧 run 沿用到新 manifest 或依赖版本则会产生不可比证据。尤其人工无法可靠替代自动化边界覆盖，自动化也无法单独证明视觉缺陷和用户决策是否可接受。
- **建议**：明确控制边界：
  - 只能用**人工 gate**控制的风险：视觉层级、可理解性、关键错误提示、实际用户决策起止确认，以及自动化难以判定的 UI 语义；人工复核必须留截图/录屏、复核者、严重度和处置。
  - 适合**fallback**控制的风险：skill/adapter 的可预期超时、非关键能力缺失或可恢复错误；fallback 到 manifest 中预先登记的稳定路径或 direct-prompt，并显式标记 pair 结果，不能静默成功。
  - 必须**quarantine**的风险：flaky fixture、非确定性 adapter、环境污染、缺失事件或无法重现的 escaped defect；隔离项不得进入 graduation 的改善分母，修复后以新运行 ID 重跑。
  - 必须**重评**的风险：scope manifest、依赖/浏览器/模型版本、任务集合、指标定义或 paired protocol 发生变化；变化后旧三次 run 只能作为历史记录，不能直接沿用为当前证据。
  - 必须**状态降级**的风险：critical/high escaped UI defect、任一指标不可解释地恶化、三次 run 不完整、baseline 不可比、人工 gate 未通过或 fallback 未登记；将候选/毕业状态降为 `NEEDS_CONTEXT`，暂停向 release/rollout 解释的传播。

**观点 6：回归证据要覆盖边界与失败路径，否则三次运行仍不足以证明质量**

- **发现**：角色任务要求逐个待讨论问题回答“怎么测、边界 case、回归风险、质量证据、可复现验证步骤”（T 角色方法）；原文却只在成功判据中列出失败 fixture 和 escaped UI defects（原文 L7），没有明确空值、异常、极值或并发等边界清单。Q1 又要求界定最小切片和不应纳入内容（原文 L12），说明边界本身需要显式裁决。
- **影响**：三次 happy-path 运行可以全部通过，却仍可能在空表单提交、服务返回 malformed payload、重复点击审批、超长字段、并发更新或权限变化时产生 UI 错误；这些缺陷若未进入 fixture 和回归集，最终的 escaped UI defects 数值会被系统性低估。无法复现的失败也无法判断是产品缺陷还是环境噪声。
- **建议**：为 manifest 中的每个 skill 和目标流建立最小边界矩阵：空/缺失、非法类型、最大长度、超时/重试、服务异常、重复提交、并发状态变化、权限不足和浏览器刷新；每个 case 固定输入、预期 UI 状态、允许 fallback、日志事件和严重度。Wave 1 先做契约/fixture 验证，Wave 2 做端到端和人工 UI gate，Wave 3 在三次 paired run 后重跑全部高风险回归集；任何未定位、不可复现或与环境相关的结果先 quarantine，不能以“偶发”关闭。
