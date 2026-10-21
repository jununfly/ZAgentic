# UI-BRIEF Patch — Expense Reimbursement Approval（EV-v0.1 · Wave 0 审批样例）

> 本 patch 由 S1(zj-ui-brief) 产出，**仅 draft / 本地 canonical，未进入 effect**。
> 退出判据验证：对话入口(A) 与 文档编辑入口(B) 收敛到同一 canonical 内容 + 同一 revision。
> 审批样例相对表单样例的增量：引入**第二个 Human gate（approver, GF-A2）**，不在 1-8-2 内实签。

## 不变量验证（1-8-2 退出判据）
- 共同起点（seed）：`UI-BRIEF.seed.md`（空模板）
- 终点（final）：`approval/UI-BRIEF.md`
- **Path A（对话输入 = 冻结 PRD §1.B）** → canonical 内容 `C_approval`
- **Path B（直接编辑 seed）** → 把 seed 四项必填填成 `C_approval` → 同一 canonical 内容 `C_approval`
- 两条入口终点内容相同 ⇒ **proposed_revision 相同**：
  `sha256(C_approval canonical body) = 5371f5582269f8bb8e3d85a1c7980801874f3c40fa6431b177d6320054c066a7`
- ✅ 对话与文档 diff 生成同一 patch / revision

## field-level diff（seed → final）
| field | before | after |
| --- | --- | --- |
| goal_users | `<UNKNOWN: 待填充目标用户>` | 报销申请人 Applicant（已登录终端用户） / 审批人 Approver |
| goal_task | `<UNKNOWN: 待填充任务描述>` | 申请人填写报销单 → 审批人通过/驳回 → 驳回可重提交 → 通过标记 approved 并 mock 持久化 |
| constraints | `<UNKNOWN: 待填充约束>` | 4 条：框架锁 / 数据边界 / 安全边界(role=approver deny-first) / 确定性 |
| success_criteria | `<UNKNOWN: 待填充成功标准>` | 4 条：A-1 / A-2~A-6 fail-closed / 双 Human gate 可追溯 / GF-A2 实签 |
| unknown[] | 空 | 空（§1.B 齐全；第二批 Human gate 实签见 GF-A2，不在本 brief 内实签） |
| source_ref | none | frozen-prd → `docs/plans/ui-agent-skills-ev-sample-flow.md#1.B` |

## 影响字段 / owner / 下游
- `goal_users` / `goal_task` / `constraints` / `success_criteria` → owner: brief/contract owner
- 消费下游：zj-ui-flow / zj-ui-direction（S2/S3）；审批态 `APPROVED/REJECTED/NEEDS_CHANGES` 复用 review record
- 关联 artifact：UI-BRIEF.md（S1 产出）；审批专属 contract GF-A1~GF-A3 见 fixture-manifest

## open questions
- 无（§1.B 四类必填齐全）。双 Human gate 的 approver 实签（GF-A2）在 review 阶段（1-8-4 附近）由 Human 操作，不在 1-8-2 内。

## receipt 预览（非最终 receipt；最终由 verification 链路产出）
- artifact: UI-BRIEF.md
- proposed_revision: `5371f5582269f8bb8e3d85a1c7980801874f3c40fa6431b177d6320054c066a7`
- input_revision: `docs/plans/ui-agent-skills-ev-sample-flow.md#1.B`
- status: **ACCEPTED**（2026-10-21 zj 接受；revision 已锁定为 canonical revision）
- human_gate: zj 已接受 patch（2026-10-21）

## Human accept gate（1-8-2 收口条件）
- [x] zj 接受此 patch（2026-10-21）⇒ `revision:` 行已写为 proposed_revision 并锁定为 canonical revision
- 接受后：1-8-2 收口，下一步 plan 进入 1-8-3（direction cards / token-catalog / flow-action-intent 人机协作）
