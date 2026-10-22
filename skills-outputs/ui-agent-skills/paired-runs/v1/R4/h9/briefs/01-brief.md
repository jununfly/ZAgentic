# 01 · S1 Intake — UI-BRIEF

> 来源 skill：zj-ui-brief（S1 INTAKE）。职责：把需求解析为可校验 brief，缺口留 `unknown`，
> 不替用户编造，连续追问 ≤ 2 次，非法字段 deny-first。

## goal（目标）
为同一产品做两个本地 mock 页面（无真后端）：① 用户资料编辑表单；② 费用报销审批流。
以可重放的状态机驱动，跑通 12 个冻结 fixture（F-1..F-6 / A-1..A-6），`all_match: true`，exit 0。

## goal_users（目标用户）
- 终端用户（资料编辑者 / 报销申请人）
- 审批人（仅其可发起审批决定）
- 系统（路由、超时升级）

## tasks（任务）
1. 资料表单：加载→编辑→实时校验→显式确认提交→persist→成功/错误；错误可恢复；超时不当成功。
2. 报销审批：填报→提交→路由→审批（通过/驳回带理由）→驳回后改完重提交成新版；越权拒绝。

## success_criteria（成功标准）
- 12/12 fixture 全匹配；park/resume 协议正确（submit 挂起，persist 唤醒）。
- 每个状态迁移在 UI 有可达控件（S1 可达性）。
- 每次提交/审批均需显式确认（human gate 实签）。

## constraints（约束）
- 本地 mock，无真实网络/后端；服务端可返回 422 或超时(0)。
- 重复提交被抑制（输入锁定，仅一次写入）。
- 越权审批 deny-first，状态不前进。

## unknown[]（证据缺口，按四元组保留）
- `path: ui/visual-direction` — 具体视觉方向与配色由 S3 拍板，本阶段不替用户决定（见 02-brief）。
- 其余四类必填齐全，无其它 unknown。

## stop_conditions 自检
- 必填齐全 → 不追问；schema 自洽 → 不 STOP。本阶段零阻断写入。
