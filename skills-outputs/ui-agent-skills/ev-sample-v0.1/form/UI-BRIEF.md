# UI-BRIEF.md — User Profile Edit Form（EV-v0.1 · Wave 0 表单样例）

brief_schema_version: 1.0.0
revision: 8638ddaf1200f3d217098ed49ad2940cf4983c7a082f7094b25d1a0060eee53d
input_revision: "docs/plans/ui-agent-skills-ev-sample-flow.md#1.A" (frozen PRD, 2026-10-21)

## goal_users
- 已登录终端用户（个人资料 owner）

## goal_task
在 Next.js 14 应用中查看并编辑个人资料（昵称、邮箱、简介等受控字段），提交后由本地 mock 持久化，得到成功/错误反馈并可恢复。

## constraints
- 框架锁：Next.js 14 (App Router) + React 18 + TypeScript 5.x + 固定 major 的 Chromium
- 数据边界：本地 mock / 内存态，无真实后端写回；远程写回仅作 1-8-5 演练项
- 安全边界：危险 action（真实网络写回、删除账号等）deny-first
- 确定性：fixture + env fingerprint 固定

## success_criteria
- F-1 成功路径：合法提交 → mock 200 + 本地持久化 + success 态
- F-2~F-6 边界路径均可被确定性验证捕获且 fail-closed（绝不伪造成功）
- 同一 case 可由对话或 UI-BRIEF.md diff 进入同一 canonical revision 与 plan
- 方向卡、tokens/catalog、flow/action/intent、prototype/preview、approval、receipt 全程可追溯
- 远程服务 / 未知字段 / 素材 quarantine 等失败场景均有本地 fallback 且不伪造成功

## unknown[]
（空 — 冻结 PRD §1.A 四类必填齐全，无缺项）

## source_ref
- type: frozen-prd
- ref: docs/plans/ui-agent-skills-ev-sample-flow.md#1.A
- note: 表单样例主体；与 1.B 审批样例并列于 Wave 0 双样例（2026-10-21 决策提升为第二条 sample）
