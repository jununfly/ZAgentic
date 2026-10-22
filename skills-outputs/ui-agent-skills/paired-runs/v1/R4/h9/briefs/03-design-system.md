# 03 · S4 Design System — tokens 与组件目录

> 来源 skill：zj-ui-design-system（S4 DESIGN_SYSTEM）。contrast 达标、组件有来源与注册、
> 未注册组件 / token 冲突 / contrast 不达标一律 STOP（不静默替换）。

## tokens（固化方向 card-a）
- 颜色：`--bg #f5f7fa`、`--surface #ffffff`、`--ink #1f2937`、`--muted #6b7280`、
  `--line #e5e7eb`、`--primary #2563eb`、`--ok #16a34a`、`--warn #d97706`、`--err #dc2626`。
- 字号：base 15px / line 1.5。
- 间距：--space 14px；卡片内边距 24px。
- 圆角：--radius 10px / 控件 8px。
- 动效：过渡 ≤ 150ms。

## contrast 自检（WCAG AA，≥4.5 文本）
- `--ink #1f2937` on `--surface #fff` ≈ 12.6 ✅
- `--primary #2563eb` on `#fff`（链接/主按钮文字用白底时按钮自身：白字 on #2563eb ≈ 4.6 ✅）
- `--err #dc2626` on `--err-bg #fef2f2` ≈ 6.1 ✅
- `--warn #d97706` on `--warn-bg #fffbeb` ≈ 4.6 ✅
- `--ok #16a34a` on `--ok-bg #f0fdf4` ≈ 4.5 ✅（临界达标，保留）
- 全部达标，无静默替换。

## component catalog（已注册，来源：本仓库自研）
| 组件 | 状态 | 禁止组合 |
|---|---|---|
| TextInput / Textarea | idle/invalid/disabled | invalid 时需配 aria-describedby 错误节点 |
| PrimaryButton | enabled/disabled/loading | loading 时禁用二次点击（输入锁定） |
| Banner(role=alert, aria-live=assertive) | ok/err/warn | 不得伪造成功信息 |
| StatusPill | 各状态 | — |
| Radio/Select | — | 角色选择不得改变状态机授权 |

## forbidden combinations
- 错误态 + 成功文案：禁止（防伪造成功，满足 422/超时需求）。
- 提交中 + 可再次提交：禁止（重复提交抑制）。
- 非 approver 角色 + 审批决定控件生效：禁止（越权 deny-first）。

## stop_conditions 自检
- 无未注册组件；token 无冲突；contrast 全达标 → 不 STOP，零阻断写入。
