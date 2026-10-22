# UI-BRIEF draft — R3/h8

## 目标
把裸需求里的两条 UI 流落成可离线重放的实现：用户资料编辑表单、费用报销审批。
两者共用同一套交互契约：实时校验、显式确认、提交中锁定、失败可恢复、状态不伪造。

## 目标用户
- 普通用户（表单流）：编辑并保存自己的昵称 / 邮箱 / 简介。
- 申请人（审批流）：填写并提交报销单，被驳回后修订重提。
- 审批人（审批流）：查看、通过或驳回；驳回必须留理由。

## 任务（每条都是要验收的行为）
1. 表单：加载展示 → 三字段实时校验 → 校验不过禁止提交 → 提交中锁定输入（重复点击只生效一次）
   → 成功/失败明确反馈 → 失败后可改再提。
2. 审批：填单（金额 > 0、事由必填、附件 mock 引用）→ 提交 → 路由到审批中 → 审批人通过/驳回（驳回带理由）
   → 驳回后申请人修订形成新版本 → 越权调用被拒且状态不前进。

## 约束
- 只用本地 mock 持久化，无真后端、无网络、零依赖 ESM。
- 422 与超时必须可表达，且都不能伪装成成功。
- 每次提交、每次审批决定都要显式确认（human gate）。
- 状态机的每条迁移都要能从界面控件触发，不能只靠直接塞 initial state。

## 成功标准
- 12 条冻结 fixture（F-1..F-6 / A-1..A-6）全部逐键比对通过。
- 失败路径（422 / 超时 / 重复提交 / 越权）都停在 honest 状态，persisted 不撒谎。
- 实现逻辑在 .mjs 模块里，HTML 只做绑定。

## unknown 四元组（缺口保留，不猜）
| path | raw | reason | source |
| --- | --- | --- | --- |
| brief.constraints.bio_max_length | null | 需求只说"简介长度上限"，未给数值 | raw-requirement.md |
| brief.constraints.attachment_required | null | 未说附件是否必填，A-3 附件为 null 但不因此报错 | fixtures/approval/A-3 |
| brief.scope.timeout_budget_ms | null | 未给超时阈值 | raw-requirement.md |
| brief.users.approver_assignment | null | 未说审批人如何分配 | raw-requirement.md |

处置：bio_max_length 取 200 并在界面显示剩余字数（可被人改）；其余保持 unknown，不影响 must-pass 行为。
