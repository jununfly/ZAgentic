# ui-flow/v1 — User Profile Edit Form（EV-v0.1 · Wave 0 表单样例）

> 上游：`form/UI-BRIEF.md`(S2) + `form/design-collab.md`(S3/S4 draft)
> Owner：zj-ui-flow（S5，唯一写 owner）；schema lock = ui-flow/v1（1-2-3）
> 状态：draft / 本地 canonical，未进入 effect；六义分义存续，unknown 四元组保留。

## 六义（six distinct meanings）

### screen
- `ProfileEditPage`：个人资料编辑页，含受控表单与反馈区

### component
- `ProfileForm`：表单容器
- `FieldInput`：单字段受控输入（昵称/邮箱/简介）
- `SaveButton`：提交按钮（含 loading 态）
- `FeedbackToast`：成功/错误反馈

### state
- `idle`：初始/未改
- `editing`：字段被修改
- `submitting`：提交中（deny 重复提交）
- `success`：mock 200 + 本地持久化
- `error`：失败态（fail-closed，不伪造成功）

### action
- `editField(field, value)`：修改字段
- `submit()`：提交 → 调 mock 持久化
- `reset()`：恢复初始

### intent
- `updateProfile`：用户希望更新其个人资料并本地持久化（语义意图，区别于 action 的机械调用）

### acceptance
- `F-1` 合法提交 → mock 200 + 持久化 + success 态
- `F-2` 非法邮箱 → error，不持久化
- `F-3` 空必填 → 阻断提交
- `F-4` 提交中重复提交 → deny
- `F-5` 持久化失败 → error，不伪造成功
- `F-6` 远程写回（仅 1-8-5 演练）→ deny-first，不真实回写

## unknown 四元组（保留过 round-trip）
- path: none
- raw: none
- reason: none
- source: none

> 说明：六义未合并、未借协议（A2UI/M3E 仅作 B1 adapter 输入）、未丢弃 unknown。硬失败项（丢义/双 owner/unknown 未保留）均不触发。
