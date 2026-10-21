# Design Collaboration — Expense Reimbursement Approval（EV-v0.1 · Wave 0 审批样例）

> 上游：`approval/UI-BRIEF.md` · `revision: 5371f5582269f8bb8e3d85a1c7980801874f3c40fa6431b177d6320054c066a7`（S2 已锁定）
> 本文件 = S3 方向卡(非 canonical) + S4 token/catalog(draft)；**均 draft / 本地 canonical，未进入 effect**。
> 增量（相对表单样例）：引入**第二个 Human gate（approver, GF-A2）**，审批决定须 Human 实签，不系统生成。
> 方向 choice 落 `UI-DESIGN.md` 需 Human 选定（WAIT_HUMAN）。

## 1. Direction Cards（S3 · zj-ui-direction，2–3 张可比候选）

### card-a · Authority Neutral
- 色彩：白底 + 中性灰 + 主色 #2563EB；审批态色：approved=#16A34A / rejected=#DC2626 / pending=#D97706
- 字体：system-ui；标题 600
- 密度：comfortable
- 动效：状态切换淡入、决策按钮确认态
- 适用场景：企业审批流，强调权威与清晰
- 取舍：视觉平淡
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）

### card-b · Status-Dense
- 色彩：浅灰底 + 强状态色块（approved/rejected/pending 大色标）
- 字体：Inter；标题 700
- 密度：compact，状态列优先
- 动效：状态色块脉冲提示待办
- 适用场景：审批队列，强调待办识别
- 取舍：小屏状态色块拥挤
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）

### card-c · Soft Review
- 色彩：暖白 + 柔和强调，圆角大面板
- 字体：rounded 栈
- 密度：airy
- 动效：弹性过渡
- 适用场景：轻量审批，强调审阅舒适
- 取舍：权威感弱
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）

## 2. Token / Catalog（S4 · zj-ui-design-system draft）

| token | value | purpose | source / license |
| --- | --- | --- | --- |
| color.bg | #FFFFFF | 页面背景 | zagentic/ui-kit v0 / proprietary |
| color.surface | #F7F8FA | 卡片容器 | zagentic/ui-kit v0 / proprietary |
| color.primary | #2563EB | 主操作 | zagentic/ui-kit v0 / proprietary |
| color.status.approved | #16A34A | 通过态 | zagentic/ui-kit v0 / proprietary |
| color.status.rejected | #DC2626 | 驳回态 | zagentic/ui-kit v0 / proprietary |
| color.status.pending | #D97706 | 待审态 | zagentic/ui-kit v0 / proprietary |
| font.family | system-ui stack | 正文 | zagentic/ui-kit v0 / proprietary |
| space.scale | 4 / 8 / 12 / 16 / 24 | 间距栅格 | zagentic/ui-kit v0 / proprietary |
| radius.base | 8px | 控件圆角 | zagentic/ui-kit v0 / proprietary |

> Provenance：全内部来源，license=proprietary，无外部未知 license 引用（FF-DIR-03 不触发）。

## 3. Direction Choice（Human gate · RESOLVED，2026-10-21）

- 候选：card-a / card-b / card-c（并列）
- **已选定**：`direction_choice = card-b · Status-Dense`（zj 指定）
- 落点：`approval/UI-DESIGN.md.direction_choice`（S3 唯一写 owner，已写入）
- human_gate：WAIT_HUMAN → RESOLVED

## 4. Provenance Summary（退出判据追踪）
- 方向选择候选 + gate：✅ 3 张卡可比、license 已注、choice 占位 WAIT_HUMAN
- token/catalog：✅ 全表带 source/license（含审批三态语义色）
- flow/action/intent（含 approver role + GF-A2）：见 `approval/ui-flow.v1.md`
- 理由/provenance：✅ 内部来源统一标注，无 quarantine
