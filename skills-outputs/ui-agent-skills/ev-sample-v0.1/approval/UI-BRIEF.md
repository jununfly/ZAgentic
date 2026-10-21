# UI-BRIEF.md — Expense Reimbursement Approval（EV-v0.1 · Wave 0 审批样例）

brief_schema_version: 1.0.0
revision: 5371f5582269f8bb8e3d85a1c7980801874f3c40fa6431b177d6320054c066a7
input_revision: "docs/plans/ui-agent-skills-ev-sample-flow.md#1.B" (frozen PRD, 2026-10-21)

## goal_users
- 报销申请人 Applicant（已登录终端用户）
- 审批人 Approver / reviewer

## goal_task
申请人填写费用报销单（金额、事由、附件 mock），提交后进入审批；审批人查看并通过 / 驳回；驳回后申请人可修改重提交；通过则标记 approved 并 mock 持久化。

## constraints
- 框架锁：Next.js 14 + React 18 + TS 5.x + 固定 major Chromium（同表单样例）
- 数据边界：本地 mock / 内存态；审批状态本地模拟，无真实后端写回
- 安全边界：审批 action 必须 role=approver（deny-first；非审批人调用审批 = 越权，阻断）
- 确定性：fixture + env fingerprint 固定

## success_criteria
- A-1 成功路径：合法提交 → under_review → approver approve → approved + 持久化
- A-2~A-6 边界路径均可被确定性验证捕获且 fail-closed
- 双 Human gate（申请人提交 + 审批人决定）全程可追溯，互不替代
- approver 决定的 APPROVED / REJECTED 须由 Human 实签，不可系统自动生成（GF-A2）

## unknown[]
（空 — 冻结 PRD §1.B 四类必填齐全，无缺项；第二批 Human gate 的实签不变量见 GF-A2，不在本 brief 内实签）

## source_ref
- type: frozen-prd
- ref: docs/plans/ui-agent-skills-ev-sample-flow.md#1.B
- note: 审批样例，2026-10-21 经 zj 决策从 Wave 1 候选提升为 Wave 0 第二条独立 sample
