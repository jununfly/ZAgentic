# UI-DESIGN.md — tokens 与 component catalog（S4）

固化 direction_choice=card-b。contrast 用 WCAG 相对亮度公式实算（见每行数值，阈值 4.5:1）。

## tokens

| token | value | 用途 |
| --- | --- | --- |
| `--surface` | #FFFFFF | 页面底色 |
| `--surface-sunken` | #F2F4F7 | 只读区块 / 时间线底 |
| `--ink` | #0F172A | 正文（on surface 17.85） |
| `--ink-muted` | #475467 | 辅助说明（on surface 7.69） |
| `--ink-faint` | #667085 | 仅 on --surface-sunken（4.51），禁止用于白底正文 |
| `--primary` | #2F4BD8 | 主操作（on surface 6.73；白字 on primary 6.73） |
| `--danger` | #B42318 | 错误/驳回（on surface 6.57；白字 6.57） |
| `--ok` | #067647 | 成功（on surface 5.69） |
| `--warn-ink` | #8A5A00 | 超时/升级提示文字（on #FFF6E5 5.52） |
| `--warn-bg` | #FFF6E5 | 超时/升级提示底 |
| `--line` | #D0D5DD | 1px 分隔线（非文本，不受 4.5 约束） |
| `--radius` | 10px | 卡片圆角 |
| `--space` | 4/8/12/16/24/32 | 间距阶 |
| `--dur` | 120ms | 状态过渡；`prefers-reduced-motion` 下置 0 |

字体：系统无衬线栈；无外部字体文件，无 license 缺口。

## component catalog

| 组件 | 来源 | 状态 | 说明 |
| --- | --- | --- | --- |
| `Field` | 自研 | default / focus / invalid / disabled(locked) / readonly | label 永久可见，错误文本 `aria-describedby` 指向，`aria-invalid` 同步 |
| `PrimaryButton` | 自研 | default / hover / busy / disabled | busy 时 `aria-busy=true` 且不可再次触发；disabled 由提交中或校验失败驱动 |
| `ConfirmGate` | 自研 | unchecked / checked | 勾选 + 文案"我确认…"；未勾选时提交按钮 disabled，禁止自动提交 |
| `StatusBanner` | 自研 | success / error / warn / info | `role=status` 或 `role=alert`；error 必带可执行的下一步 |
| `Timeline` | 自研 | item(done/current/pending) | 审批版本与决定留痕，旧版本只增不删 |
| `RoleSwitch` | 自研 | applicant / approver / other | 演示越权拒绝；other 触发 deny-first |

## forbidden combinations
- `--ink-faint` 放在 `--surface` 上做正文（4.51 仅对 sunken 成立）。
- 错误只靠颜色表达（必须同时有文本与 `aria-invalid`）。
- 提交中仍可编辑的 Field（locked 必须同时 `disabled` 且视觉可辨）。
- 未勾选 ConfirmGate 却可点击 PrimaryButton。
- 超时用 success 色或 success 文案表达。

catalog 之外不新增组件；未注册组件一律阻断（本轮无）。无 token 冲突，contrast 全部达标。
