# UI-BRIEF · 双流程（资料编辑 + 费用报销审批）

S1 INTAKE 产物。input source: ../raw-requirement.md

## 目标 / goal
在同一产品内交付两条 UI 流程：
1. 用户资料编辑表单：加载并编辑昵称/邮箱/简介，实时校验，显式提交，成功与失败都有明确反馈，失败可恢复再提交。
2. 费用报销审批：申请人填单（金额/事由/附件 mock 引用），提交进入审批，审批人通过或驳回（驳回必填理由），驳回后申请人改完重提形成新版本。

## 目标用户
- `user`（表单编辑者 / 申请人 applicant）：编辑资料、提交报销单、被驳回后修订。
- `approver`（审批人）：查看待办、通过或驳回，审批动作排他。
- `system`（工作流引擎）：路由攸关 Applied：把 submitted 路由到 under_review；审批超时升级。

## 任务 / tasks
| flow | task |
| --- | --- |
| form | 加载当前资料并回填三个字段 |
| form | 输入过程中实时校验（昵称必填、邮箱格式、简介长度上限） |
| form | 校验不通过不得提交，提交按钮 disabled + 字段级错误文案 |
| form | 提交中锁定输入，重复点击只生效一次 |
| form | 提交由用户显式确认的对话框触发，禁止自动提交 |
| form | mock 服务端返回 200/422/超时；超时不得显示为成功 |
| form | 失败态可恢复到可编辑态，改完重新提交 |
| approval | 申请人填 金额>0 / 事由必填 / 附件为 mock 引用 |
| approval | 提交后 draft→submitted，再经系统路由到 under_review |
| approval | 审批人 sign 后才通过或驳回；驳回必须带理由 |
| approval | 驳回后可 revise 形成新版本，历史版本记录保留 |
| approval | 审批动作只能 approver 发起；非审批人（含自审批）在入口 deny-first 被拒，状态不前进 |

## 约束 / constraints
- 零运行时依赖：原生 ESM + 静态 HTML，无网络安装。
- 持久化只用本地 mock（内存 store），不发真实请求。
- 422 与超时必须可表达、可复现，且永不伪造成功。
- 所有提交 / 审批决定必须有显式 Human gate（确认对话框），记录 role / signed / at_step。
- 状态机迁移必须由 HTML 上的真实控件触发，不允许只通过初始状态构造。

## 成功标准 / success_criteria
- 表单：合法提交落庫成功态；非法字段提交被拦截且无副作用；重复提交只写一次；422/超时进 error 且可恢复。
- 审批：角色越权被拒且状态不前进；驳回必带理由；驳回后重提产生新版本且旧记录保留；双 Human gate 均实签。

## unknown（四元组，未压空）
| path | raw | reason | source |
| --- | --- | --- | --- |
| form.bio.max_length | null | 需求只说"简介长度上限"，未给具体数值；本次取 200 并在 UI 明示计数器 | ../raw-requirement.md |
| approval.attachment.required | null | 需求说"附件用 mock 引用即可"，未说是否必填；本次为选填 | ../raw-requirement.md |
| approval.reason.required_on_approve | null | 需求只对驳回强制理由；通过是否必填未说 | ../raw-requirement.md |
| approval.sla_timeout_ms | null | 需求提到超时/升级但未给时长；由 UI 显式触发模拟 | ../raw-requirement.md |
