# ui-flow/v1 — Expense Reimbursement Approval（EV-v0.1 · Wave 0 审批样例）

> 上游：`approval/UI-BRIEF.md`(S2) + `approval/design-collab.md`(S3/S4 draft)
> Owner：zj-ui-flow（S5，唯一写 owner）；schema lock = ui-flow/v1（1-2-3）
> 状态：draft / 本地 canonical，未进入 effect；六义分义存续，unknown 四元组保留。
> 增量：审批 action 必须 `role=approver`（deny-first）；APPROVED/REJECTED 由 Human 实签（GF-A2），不系统生成。

## 六义（six distinct meanings）

### screen
- `ExpenseFormPage`：报销单填写页
- `ApprovalReviewPage`：审批人审阅页（role-gated）

### component
- `ExpenseForm`：报销单表单（金额/事由/附件 mock）
- `SubmitButton`：申请人提交
- `ApprovalPanel`：审批面板（仅 approver 可见可操作）
- `DecisionButtons`：通过 / 驳回（approver 实签）

### state
- `draft`：填写中
- `under_review`：已提交待审
- `approved`：审批通过（Human 实签）
- `rejected`：驳回（Human 实签）
- `needs_changes`：驳回后可修改重提交

### action
- `submitExpense()`：申请人提交 → under_review
- `approve()`：approver 通过（**role=approver 校验，deny-first；非审批人调用 = 越权阻断**）
- `reject()`：approver 驳回（同上 role 校验）
- `revise()`：申请人按驳回意见修改后重提交

### intent
- `submitReimbursement`：申请人希望提交报销并进入审批
- `approveReimbursement`：审批人（role=approver）对报销单做出通过/驳回决定（语义意图，区别于机械 action 调用；决定须 Human 实签 GF-A2）

### acceptance
- `A-1` 合法提交 → under_review → approver 通过 → approved + 持久化
- `A-2` 非 approver 调 approve/reject → 越权阻断，状态不变
- `A-3` 驳回 → needs_changes，申请人可重提交
- `A-4` 审批中重复决策 → deny
- `A-5` 持久化失败 → error，不伪造成功
- `A-6` 远程写回（仅 1-8-5 演练）→ deny-first，不真实回写

## unknown 四元组（保留过 round-trip）
- path: none
- raw: none
- reason: none
- source: none

> 说明：六义未合并、未借协议、未丢弃 unknown；审批态 `APPROVED/REJECTED/NEEDS_CHANGES` 复用 review record。硬失败项不触发。
