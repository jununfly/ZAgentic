# UI-DESIGN.md — Expense Reimbursement Approval（EV-v0.1 · Wave 0 审批样例）

> 上游：`approval/UI-BRIEF.md` · `revision: 5371f5582269f8bb8e3d85a1c7980801874f3c40fa6431b177d6320054c066a7`
> Owner：zj-ui-direction（S3，唯一写 owner）；本文件为 S3 选定方向后的 canonical 方向落点。
> 状态：draft / 本地 canonical，未进入 effect（生产代码归 1-8-4/1-8-5）。
> 增量：审批三态语义色（approved/rejected/pending）随 card-b 落定。

## direction_choice（Human 选定，2026-10-21）
- **selected**: `card-b · Status-Dense`
- 选定人：zj（Human gate 解除，原 WAIT_HUMAN → RESOLVED）
- 理由/provenance：`zagentic/ui-kit v0`（internal, license: proprietary）；选中依据 = 审批队列强调待办识别，强状态色块（approved=#16A34A / rejected=#DC2626 / pending=#D97706）+ compact 密度最贴合。无外部未授权引用，不触发 FF-DIR-03 quarantine。

## 选定方向约束（供 S4 token/catalog 与 S5 flow 消费）
- 色板：白底 + 主色 #2563EB；状态色 approved=#16A34A / rejected=#DC2626 / pending=#D97706
- 字体：Inter（fallback system-ui）；标题 700
- 密度：compact，状态列优先
- 动效：状态色块脉冲提示待办
- 取舍已记录（见 design-collab.md §1 card-b）
- **GF-A2 仍生效**：APPROVED/REJECTED 必须由 approver（role=approver）实签，不系统生成。

## 关联 artifact
- 方向卡候选：`approval/design-collab.md` §1（card-a/b/c 全列）
- token/catalog：`approval/design-collab.md` §2（已含审批三态语义色，对齐 card-b）
- flow 六义：`approval/ui-flow.v1.md`
