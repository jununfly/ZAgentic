# UI-DESIGN · 用户资料编辑表单

stage: S4 DESIGN_SYSTEM
direction_choice: card-b (Focused Console)
tokens_source: artifact/src/tokens.mjs

## tokens

| token | value | 用途 |
| --- | --- | --- |
| color.surface | #FFFFFF | 页面与卡片底色 |
| color.text | #1A1A1A | 正文与标签 |
| color.muted | #5B6472 | 辅助说明 |
| color.primary | #1F5EFF | 主按钮、聚焦环 |
| color.onPrimary | #FFFFFF | 主按钮文字 |
| color.danger | #B42318 | 错误文字与边框 |
| color.border | #D0D5DD | 输入框默认边框 |
| space.1..5 | 4 / 8 / 12 / 20 / 32 | 间距阶 |
| radius.control | 8px | 输入框与按钮 |
| radius.card | 14px | 表单卡片 |
| font.body | 15px / 1.55 | 正文 |
| font.label | 13px / 600 | 字段标签 |
| motion.state | 120ms ease-out | 状态过渡 |

## contrast（WCAG 2.1，阈值 4.5:1）

| 前景 / 背景 | 比值 | 结果 |
| --- | --- | --- |
| #1A1A1A on #FFFFFF | 17.40 | PASS |
| #5B6472 on #FFFFFF | 5.98 | PASS |
| #1F5EFF on #FFFFFF | 5.12 | PASS |
| #FFFFFF on #1F5EFF | 5.12 | PASS |
| #B42318 on #FFFFFF | 6.57 | PASS |

不达标时阻断，不得静默替换相近色。比值为 `artifact/src/verify.mjs` 的运行时计算值。

## component catalog

| 组件 | 来源 | 状态 | 说明 |
| --- | --- | --- | --- |
| FormShell | in-house | default | 单列表单容器，最大宽 520 |
| TextField | in-house | default / focus / invalid / disabled | 昵称、邮箱 |
| TextArea | in-house | default / focus / invalid / disabled | 简介，含字数计数 |
| InlineError | in-house | hidden / visible | 字段级错误，aria-describedby 关联 |
| SubmitButton | in-house | enabled / disabled / busy | 校验失败或提交中禁用 |
| ConfirmDialog | in-house | open / closed | 显式确认，native dialog |
| FeedbackBanner | in-house | success / error / info | role=status 或 alert |

## forbidden combinations

- 提交中（submitting）仍可编辑：禁止，fieldset disabled。
- 校验失败仍可提交：禁止，按钮 disabled 且状态机拒绝。
- 无用户确认的 submit：禁止，系统角色提交只产生 gate 拒绝。
- 成功横幅与错误横幅同时出现：禁止。
- 用颜色单独表达错误：禁止，必须同时有文字与 aria-invalid。

## 组件来源台账

全部 in-house，无第三方字体、图标或素材；无 license unknown 项。
