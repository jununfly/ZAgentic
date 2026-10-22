# ui-flow/v1 · 六义（screen / component / state / action / intent / acceptance）

S5 FLOW 产物。六义严格分义，不合并。

## 1. screen
- `screen.form` — 用户资料编辑页（index.html）
- `screen.approval` — 费用报销审批页（approval.html）

## 2. component
仅引用 UI-DESIGN 已注册组件：TextField, FieldErrorText, StateBadge, ConfirmDialog, ActionButton,
AccountableTimeline, RoleSwitcher, FailureBanner。

## 3. state
### form 状态集
`idle` → `validating` → `submitting` → `success` | `error`；`error` → `validating`（recover）

### approval 状态集
`draft` → `submitted` → `under_review` → `approved` | `rejected`；
`rejected` → `draft`（revise，版本 +1，历史记录保留）；
`under_review` → `under_review`（escalate，显式升级标记）

## 4. action
| flow | action | 触发角色 | from | to（由状态机计算） | 备注 |
| --- | --- | --- | --- | --- | --- |
| form | edit | user | idle / validating / error | validating | 重算字段级错误 |
| form | validate | system | validating | validating | 幂等，不改状态 |
| form | submit | user（人签） | validating | submitting | 有字段错误或已在 submitting 则拒绝 |
| form | persist | system | submitting | success / error | 200 成功；422 可恢复错误；超时走 fallback |
| form | recover | user | error | validating | 失败后恢复编辑 |
| approval | edit | applicant | draft / rejected | draft | rejected 进入 draft 时版本递增 |
| approval | submit | applicant（人签） | draft | submitted | 校验失败停 draft；非 draft 判 duplicate |
| approval | route | system / approver 受理 | submitted | under_review | 工作流路由 |
| approval | approve | approver（人签，禁自审批） | under_review | approved | 非 approver 在入口 deny |
| approval | reject | approver（人签，必带理由） | under_review | rejected | 理由为空则拒绝，状态不前进 |
| approval | escalate | system（超时） | under_review | under_review | 显式升级标记，不写持久化，等人工接管 |

## 5. intent
| intent | 表达 |
| --- | --- |
| 不自动提交 | 每个改变状态的用户动作先由本人确认签名，role / signed / at_step 入账 |
| 不伪造成功 | 超时与 422 只进 error 态并带显式标记；持久化仅在实际写入成功时置位 |
| 提交幂等 | submitting / submitted 期间重复触发被忽略，写入次数不增加 |
| 审批排他 | 只有指定审批人且非申请人本人可以审批；越权在入口 deny，状态不前进 |
| 可追溯 | 驳回后重提生成新版本，历史驳回记录保留 |

## 6. acceptance
- 表单成功路径：mock 200 加本地持久化，success 态，写入次数等于真实成功写入数。
- 表单非法路径：字段级错误指向具体字段，禁止提交，无写入，无签名记录。
- 表单重复：第二次提交被忽略，写入次数不增加。
- 表单失败：422 进 error 且可恢复；超时进 error 且带显式标记与稳定路径 fallback；两者均未持久化。
- 审批成功或驳回：终态正确、已持久化、双签名在位；驳回附理由；越权或无签名均无状态前进。
- 审批超时升级：状态不前进、不落库、且必须留下显式升级标记。

## Human gate 记录语义（两流程各自 owner）
- form：只在角色本人确实完成签名时记录，未签名意味着确认环节从未发生，列表为空。
- approval：通过授权检查的每一次人类动作都记录；signed 表示该动作是否真正生效。
  未通过授权检查的调用者不是本审批 gate 的参与者，因此不记 gate，只记拒绝原因。
