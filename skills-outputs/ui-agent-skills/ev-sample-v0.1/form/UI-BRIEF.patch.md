# UI-BRIEF Patch — User Profile Edit Form（EV-v0.1 · Wave 0 表单样例）

> 本 patch 由 S1(zj-ui-brief) 产出，**仅 draft / 本地 canonical，未进入 effect**。
> 退出判据验证：对话入口(A) 与 文档编辑入口(B) 收敛到同一 canonical 内容 + 同一 revision。

## 不变量验证（1-8-2 退出判据）
- 共同起点（seed）：`UI-BRIEF.seed.md`（空模板，四项必填为占位）
- 终点（final）：`form/UI-BRIEF.md`
- **Path A（对话输入 = 冻结 PRD §1.A）** → canonical 内容 `C_form`
- **Path B（直接编辑 seed）** → 把 seed 四项必填填成 `C_form` → 同一 canonical 内容 `C_form`
- 两条入口终点内容相同 ⇒ **proposed_revision 相同**：
  `sha256(C_form canonical body) = 8638ddaf1200f3d217098ed49ad2940cf4983c7a082f7094b25d1a0060eee53d`
- ✅ 对话与文档 diff 生成同一 patch / revision

## field-level diff（seed → final）
| field | before | after |
| --- | --- | --- |
| goal_users | `<UNKNOWN: 待填充目标用户>` | 已登录终端用户（个人资料 owner） |
| goal_task | `<UNKNOWN: 待填充任务描述>` | 在 Next.js 14 应用中查看并编辑个人资料（昵称、邮箱、简介等受控字段），提交后由本地 mock 持久化，得到成功/错误反馈并可恢复 |
| constraints | `<UNKNOWN: 待填充约束>` | 4 条：框架锁 / 数据边界 / 安全边界 / 确定性 |
| success_criteria | `<UNKNOWN: 待填充成功标准>` | 5 条：F-1 / F-2~F-6 fail-closed / 同 revision / 可追溯 / 本地 fallback |
| unknown[] | 空 | 空（§1.A 齐全，无缺项） |
| source_ref | none | frozen-prd → `docs/plans/ui-agent-skills-ev-sample-flow.md#1.A` |

## 影响字段 / owner / 下游
- `goal_users` / `goal_task` / `constraints` / `success_criteria` → owner: brief/contract owner
- 消费下游：zj-ui-flow / zj-ui-direction（S2/S3）
- 关联 artifact：UI-BRIEF.md（S1 产出）

## open questions
- 无（§1.A 四类必填齐全）。审批样例见并行 patch `approval/UI-BRIEF.patch.md`。

## receipt 预览（非最终 receipt；最终由 verification 链路产出）
- artifact: UI-BRIEF.md
- proposed_revision: `8638ddaf1200f3d217098ed49ad2940cf4983c7a082f7094b25d1a0060eee53d`
- input_revision: `docs/plans/ui-agent-skills-ev-sample-flow.md#1.A`
- status: **ACCEPTED**（2026-10-21 zj 接受；revision 已锁定为 canonical revision）
- human_gate: zj 已接受 patch（2026-10-21）

## Human accept gate（1-8-2 收口条件）
- [x] zj 接受此 patch（2026-10-21）⇒ `revision:` 行已写为 proposed_revision 并锁定为 canonical revision
- 接受后：1-8-2 收口，下一步 plan 进入 1-8-3（direction cards / token-catalog / flow-action-intent 人机协作）
