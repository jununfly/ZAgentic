视角来源: 跨会话独立Agent

**观点 1：RACI 必须落到每个 Wave 的交付物，而不能只停留在角色名单**

- **发现**：原文把本子问题的边界写成第一版垂直切片、skills/adapters、Wave 顺序、资源边界和毕业标准，且 Q2 明确要求 Wave 0–3 的“责任、退出条件和失败回退”（原文 L6、原文 L13）；但当前没有把“谁负责产出、谁复核、谁批准、谁被通知”映射到任何交付物。原文的 B/C/A/T/U/P 是声明必需的讨论角色集（原文 L8），不是实施 RACI。
- **影响**：没有实施级 RACI 时，Wave 可能由“最先动手的人”隐式接管；失败 fixture、指标记录或退出证据无人签收，后续 Wave 仍可能继续。这样即使三次运行完成，也无法证明是同一套被授权、被复核的流程。
- **建议**：为每个 Wave 建一行交接登记：交付物、Responsible、Accountable、Consulted、Informed、入口条件、退出证据、回退目标、截止时间。至少区分 skill/adapter 实作者、运行记录责任人、质量复核者和 Human 批准者；每一行只能有一个 Accountable。Human 必须 gate 住范围、baseline 冻结、Wave 退出和 graduation；其余日常复核可以由指定责任人执行，不能用“角色已参与讨论”代替签收。

**观点 2：Wave 0–3 要用“可签收的 handoff contract”连接，而不是用口头依赖推进**

- **发现**：Q2 要求依赖顺序、责任、退出条件和失败回退（原文 L13），但成功判据只列出了目标垂直切片、skill 契约字段和三次运行指标（原文 L7），没有定义上一 Wave 交给下一 Wave 的最小包、签收者或未通过时的状态。
- **影响**：Wave 之间会出现隐性前置条件：例如契约字段尚未齐全就开始集成，或集成失败后把半成品继续带入毕业评审。组织上会把“没有交接证据”误当成“没有阻塞”，并且难以定位是依赖缺失、责任缺位还是验收失败。
- **建议**：将顺序固化为可审计的交接链：Wave 0 交付已批准的切片范围、排除项、资源上限和冻结的 baseline 方案；Wave 1 交付每个纳入 skill 的输入/输出/禁止事项/依赖/停止条件/失败 fixture；Wave 2 交付同一垂直切片的完整集成运行包和逐项指标记录；Wave 3 只接收已签名的三次 paired-run 证据并执行 graduation review。下一 Wave 只能在上一 Wave 的 Accountable 签收后启动；退出失败自动回退到最近一次通过的 Wave，未合格产物进入 quarantine，不能靠口头豁免穿越 Wave。

**观点 3：资源边界要成为 scope gate 和 WIP 限制，而不是一句原则性声明**

- **发现**：原文明确本子问题要锁定“资源边界”，同时规定本轮不重新设计 artifact、adapter 或安全机制，也不承诺 release/rollout/version-skew（原文 L6–L7）；但没有给出纳入 skill/adapter 数量、可用工程人时、运行次数、评审容量或新增范围的处理规则。
- **影响**：当实现遇到阻力时，团队很容易通过临时增加 skill、重做 adapter 或把 release 兼容性带进来“解决”问题，导致 Experience Version 失去可比性；资源耗尽也会被伪装成延期，而不是一个可识别的范围失败。
- **建议**：在 Wave 0 由 Human 批准资源账本：一个 React/Next.js 表单或审批流、固定纳入清单、固定运行预算、固定评审人力和明确 out-of-scope 清单；每个 Wave 设 WIP 上限，新增 skill/adapter、改变 artifact/security 设计或触及 release/rollout/version-skew 都必须重新评估并由 Human 批准。超出预算时，自动停止新范围、保留最近通过的 baseline 和运行证据；若无法在边界内完成，将候选状态降级为 scope-incomplete/NEEDS_CONTEXT，而不是宣称毕业。

**观点 4：baseline 与 paired run 必须由 Human 先冻结，运行过程只能按协议执行**

- **发现**：成功判据要求至少三次完整运行，并且要相对 direct-prompt baseline 比较返工率、用户决策时间和 escaped UI defects（原文 L7）；Q3 也专门要求避免“代码能跑”冒充成功（原文 L14）。但原文尚未规定 baseline 的任务样本、prompt、输入、环境、顺序、指标口径和失效运行的判定。
- **影响**：若 baseline 在运行中漂移，或只挑选对 skill 有利的案例，三次比较就无法区分流程收益与任务难度、参与者熟悉度或环境变化。用户决策时间和 escaped defect 还可能因人工补救而被低估，形成“有数字但不可复核”的毕业证据。
- **建议**：Wave 0 先建立并由 Human gate 冻结 baseline protocol：同一批任务/输入和等价 direct-prompt，对每次 paired run 预先记录顺序、环境、操作者、原始输出、返工、决策时间和 escaped UI defect 定义；baseline 与 treatment 必须成对运行，不得事后重写 prompt 或删异常样本。协议偏离、环境变化、记录缺失的 run 进入 quarantine，不计入三次；是否按同协议重跑由指定复核者提出、Human 批准，不能由运行责任人自行裁定。

**观点 5：三次运行应是连续的质量门，不是事后凑出的总样本数**

- **发现**：原文只要求“至少三次完整运行”并在三个指标上改善（原文 L7），同时 Q3 要求定义 graduation criteria（原文 L14）；这还没有回答每次运行是否都必须完整、某一指标退化如何处理、异常样本能否替换，以及三次结果由谁判定。
- **影响**：如果允许先跑很多次再挑三次，或用一次成功运行覆盖两次失败运行，就会把 graduation 变成选择性汇总；返工率、决策时间和 escaped UI defects 之间的权衡也会在最后一刻才暴露，团队会把“平均改善”误读为流程稳定。
- **建议**：在 baseline gate 时预注册逐次和总体规则：每次 paired run 必须有完整证据包；单次严重 escaped UI defect、关键停止条件失效或记录不全，先 quarantine 并标注原因；不得静默替换。三次有效 run 完成后，再按预注册阈值检查三个指标及不可接受缺陷门，输出逐次结果、总体结果和偏差说明。指标冲突、样本无效或阈值需要临时调整时，必须 Human re-evaluation；在重评前状态保持 candidate/NEEDS_CONTEXT，不能升级为 graduated。

**观点 6：Human 决策点要有拒绝、暂停和降级权，不能只在表格里“待拍板”**

- **发现**：原文的 Human 拍板表把 B、C、A、T、U、P 六轮都标为“待拍板”，且“是否 conclusion”均为“否”（原文 L54–L63）；文档状态仍是 NEEDS_CONTEXT（原文 L65–L73）。这说明决策尚未发生，但没有列出每次拍板的输入、批准范围、拒绝后去向或升级路径。
- **影响**：如果 Human 只对最终结果点头，前面的范围、资源、baseline 和 Wave handoff 就会形成事实承诺；发生责任争议或数据异常时，团队可能以“流程已经跑过”为理由继续推进。更严重的风险——范围越界、指标口径变更、严重 UI 缺陷豁免、release/rollout 外溢——不能由自动脚本或单个执行者替 Human 接受。
- **建议**：把 Human gate 固定为六类决策：批准最小切片/排除项与资源账本；批准 RACI 和 Wave 0–3 handoff contract；冻结 baseline/paired-run protocol；批准每次异常的 quarantine 或同协议重跑；审阅三次运行及指标冲突后的 re-evaluation；最终批准 graduation。每个 gate 都记录证据、决策人、日期、条件和拒绝动作。无 Human 决策时保持 NEEDS_CONTEXT；违反边界或出现无法解释的指标时暂停并降级；孤立的坏 run 进入 quarantine；可修复的流程偏差按批准协议 fallback 重跑。不得把“本轮不承诺 release/rollout/version-skew”（原文 L7）解释成可以绕过这些人工闸门。
