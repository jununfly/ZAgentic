# Experience Version 指标预注册（EV-v0.1 / Wave 0 · 节点 1-1-3）

> 归属路线图节点：1-1-3（预注册 direct-prompt baseline、返工/决策时间/escaped defect 指标与毕业门槛）
> 事实源：ui-agent-skills 路线图（已收口，carrier 文件已清理）
> 上游 SSOT：`discussions/ui-agent-skills-complete-solution/MASTER.md` L122 与 `sub-06-experience-version.md`（观点 3–6）
> 配套：scope manifest `ui-agent-skills-scope-manifest.md`、表单锁定 `ui-agent-skills-ev-form-lock.md`
> 状态：预注册版，运行前冻结；后续变更须经 1-10 重评流程，旧三次 run 不得直接沿用到新证据。

## 0. 定位与硬约束

- 本文件是 **运行前（before any run）** 必须冻结的比较协议与毕业闸门。任何 paired run 在协议冻结前不得开始计数。
- **预注册原则（证据先于实现）**：baseline、三项指标口径、阈值、paired run 规则、invalid-run 规则在此一次性固定；运行中发现问题只触发 `quarantine` / `re-evaluate` / `downgrade`，不得事后改写口径。
- **graduation ≠ release**：本节点与 1-9-4 的毕业只产出 `graduated-experience` 状态，**不授予** release / rollout / version-skew 权限。本轮方案明确不承诺发布（MASTER L7）。
- 责任人（沿用 `ui-agent-skills-ev-form-lock.md` §5）：产品/验收负责人 **zj**（Human gate），实现负责人 **zjj**（AI，负责样例/协议落地与记录）。
- **2026-10-21 范围扩张（pre-run）**：经 zj 决策，审批流由 Wave 1 候选提升为 Wave 0 第二条独立 sample（见 §1 baseline 表格 A-1~A-6）。因 1-9 尚未执行，无 paired run 作废；本变更待 1-10 重评轨道正式归档（e18 = 1-9→1-10 阻塞）。

## 1. Direct-prompt baseline（可控 control manifest，不是一句 "direct-prompt"）

baseline 必须是可复现的 control 记录，与 Experience Version 配对运行。每次运行对**同一任务**做成一对 control/experience，预先固定配对与顺序，保留完整日志。

baseline manifest 固定字段：

| 字段 | 冻结值 / 口径 |
| --- | --- |
| 任务 / fixture ID | 锁定于 `ui-agent-skills-ev-form-lock.md` 的两条并行 sample：① 用户资料编辑表单（F-1~F-6：成功 / 空提交 / 非法格式 / 重复提交 / 服务端 422 / 超时）；② 费用报销审批流（A-1~A-6：成功审批 / 驳回 / 非法金额 / 重复提交 / 超时 / 越权审批） |
| 仓库提交 | 记录 direct-prompt 对照组所用代码与 prompt 快照的 commit / hash；Experience 组记录对应切片提交 |
| 环境快照 | Next.js 14 (App Router) + React 18 + TS 5.x + 固定 major 的 Chromium；本地 mock / 内存态，无真实后端写回 |
| 模型 / 工具预算 | direct-prompt 组**仅用裸 prompt + 通用能力**，不接入 10 个 UI skill / adapter；预算与时长上限与 Experience 组等价 |
| 参与者 | 记录操作者、是否首次接触该任务、是否获得帮助；同一 run 内 control/experience 由同一操作者执行以控制变量 |
| 起止事件 | 任务开始 = 用户接收任务说明；任务结束 = 用户确认“完成/放弃” |
| defect 分类 | 按严重度分级：critical / high / medium / low（见 §3.3） |

约束（来自 sub-06 观点 4 / P 观点 4）：
- Experience 失败时记录失败原因并 fallback 到 baseline，但该 pair 仍标为失败 / 不计入毕业，**不得删除失败样本**。
- 不能用一次 baseline 去支撑三个不同 Experience 版本；三次 paired run 必须各自包含 baseline 与 Experience。

## 2. 三项毕业指标的操作化定义（口径 + 分母）

### 2.1 返工率（rework rate）
- **定义**：完成任务所需返工次数 / 任务数。
- **返工事件**：用户因校验失败、提交被拒、错误恢复、字段误解而回头修改已填内容或重新发起提交的动作。
- **不计入**：纯浏览、无状态的焦点切换；等待时间单列（见 2.2）。
- **改善判定**：`(baseline 返工率 − EV 返工率) / baseline 返工率 ≥ 20%`。

### 2.2 用户决策时间（decision time）
- **定义**：从任务开始事件到用户作出并确认决定的时间（秒）。
- **口径**：等待时间（submitting 态、网络/服务等待）单列记录，不并入决策时间；但计入总体体验时长作为辅助观察。
- **学习效应隔离**：task 顺序做 counterbalance，避免三次都由熟悉 EV 的同一顺序驱动（sub-06 U 观点 3）。
- **改善判定**：`(baseline 决策时间 − EV 决策时间) / baseline 决策时间 ≥ 15%`。

### 2.3 Escaped UI defects（逃逸缺陷）
- **定义**：任务完成后，由**独立观察员**按严重度发现的、未被自动化验证捕获的 UI 缺陷。
- **严重度分级**：
  - critical：关键可达性/停止条件缺失、关键错误提示不可理解、用户无法独立恢复、键盘/读屏无法到达关键控件、误提交风险。
  - high：焦点丢失、错误恢复路径不通、明显布局/语义错误。
  - medium / low：次要视觉或文案问题。
- **收集方式**：独立观察员在用户完成后复核，记录类型、严重度、是否用户已察觉、是否影响决策。
- **改善判定（MASTER L122）**：**每次 run 均不恶化**；三次汇总 escaped defect 改善 `≥ 20%`（即 `(baseline 合计 − EV 合计) / baseline 合计 ≥ 20%`）。任一 run 出现未接受的 critical/high escaped defect → 该 run 不毕业（不得用另外两次平均掉）。

## 3. 毕业门槛（thresholds，沿用 MASTER L122）

| 指标 | 门槛 | 聚合方式 |
| --- | --- | --- |
| 返工率 | 相对 baseline 改善 **≥ 20%** | 按 run 聚合对比 |
| 决策时间 | 相对 baseline 改善 **≥ 15%** | 按 run 聚合对比 |
| Escaped UI defects | **每次不恶化** + 三次汇总改善 **≥ 20%** | 每次单独达标 + 三次合计对比 |
| 关键护栏 | 零 critical/high gate 失败、零越权 action、零 provenance/receipt 缺失 | 任一违反即不毕业 |

硬性否决项（人工 gate，sub-06 U 观点 4）：主持人救援、用户无法完成、关键错误未被用户察觉、键盘/读屏无法到达关键控件 → 状态降级 / 隔离，不得借“本轮不承诺 rollout”掩盖。

## 4. Paired run 协议（same case / environment / config）

- **结构**：预注册三次运行 **R1 / R2 / R3**，每次都包含同一批已锁定任务/fixture 的**一对匹配**：一次 direct-prompt baseline，一次 Experience Version。
- **等价性**：同一任务目标、等价数据、同一成功定义、相同角色权限与环境快照。
- **顺序 counterbalance**：R1/R2/R3 在 control/experience 顺序上交错，隔离用户学习效应。
- **记录模板（每次 run 固定留存）**：
  1. 运行 ID（R1/R2/R3）、版本、fixture、环境指纹；
  2. 返工次数及导致返工的用户动作；
  3. 决策时间起止与等待时间（单列）；
  4. 独立观察员发现的 escaped UI defects（按严重度）；
  5. 复核者、屏幕/DOM 证据、处置。
- **原始证据留存**：所有事件日志与截图/录屏原始留存，不可事后重写 prompt 或删异常样本。
- **运行前人工批准**：阈值与聚合规则在**任何运行前**由 Human（zj）批准冻结。

## 5. Invalid-run 规则（不计入口径，补跑）

出现以下任一情况，该 pair / run 标为 **invalid**，不计入三次有效样本，须以**新 run ID** 补跑（不补算、不平均）：

| 类型 | 判定 |
| --- | --- |
| 配置漂移 | case / environment / config 与预注册协议不一致 |
| 环境变化 | 浏览器/字体/模型/工具预算/仓库提交变更 |
| 日志缺失 | 缺原始事件、缺屏幕/DOM 证据、缺决策起止记录 |
| 人工救援 | 主持人介入、用户被提示“下一步怎么做”、中途人工修补 |
| 范围变更 | scope manifest、paired protocol、指标定义发生变化（旧 run 仅作历史，需 re-evaluate） |
| 选择偏差 | 只保留 Experience 成功样本、baseline 与 Experience 使用不同难度任务 |

无效 run 由指定复核者提出、Human 批准是否按同协议重跑；**运行责任人不得自行裁定**（sub-06 P 观点 4）。

## 6. 状态与降级（与 sub-06 观点 5/6 一致）

至少区分：`candidate` / `wave-passed` / `quarantined` / `needs-re-evaluation` / `graduated-experience` / `downgraded`。

- **只能人工 gate 控制**：视觉层级、可理解性、关键错误提示、用户决策起止确认、自动化难判定的 UI 语义。
- **fallback 控制**：可预期超时、非关键能力缺失 → fallback 到预登记稳定路径或 direct-prompt，显式标记 pair，不静默成功。
- **必须 quarantine**：flaky fixture、非确定性 adapter、环境污染、缺失事件、无法重现的 escaped defect → 隔离项不进入毕业分母，修复后以新 run ID 重跑。
- **必须重评**：scope / 依赖版本 / 任务集 / 指标定义 / paired protocol 变化 → 旧三次 run 作废。
- **必须状态降级**：critical/high escaped defect、任一指标不可解释恶化、三次 run 不完整、baseline 不可比、人工 gate 未通过、fallback 未登记 → 降为 `NEEDS_CONTEXT`，暂停向 release/rollout 传播。

## 7. 引用与衔接

- 资源 / 许可证 / fixture / owner / 风险账本 → 节点 **1-1-4**（Wave 0 账本）。
- 三次 paired run 执行与原始日志留存 → 节点 **1-9-1 / 1-9-2 / 1-9-3**。
- 指标聚合、剩余风险与 fallback 演练 → 节点 **1-9-4**（graduation packet）。
- 阈值与协议变更 → 节点 **1-10**（重评治理）。
