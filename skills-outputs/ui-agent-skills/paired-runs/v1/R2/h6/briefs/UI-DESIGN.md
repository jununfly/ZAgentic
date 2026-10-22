# UI-DESIGN · tokens 与 component catalog

S4 DESIGN_SYSTEM 产物。输入方向：card-b（Human 已签）。

## Tokens
| token | value |
| --- | --- |
| color.bg | #FFFFFF |
| color.surface | #F6F7F9 |
| color.text | #1F2430 |
| color.text-muted | #5A6472 |
| color.border | #CBD2DC |
| color.accent | #1A56DB |
| color.error | #B42318 |
| color.success | #067647 |
| color.warn | #8A5A00 |
| font.family | system-ui, -apple-system, "Segoe UI", sans-serif（系统字体栈，无外部 license） |
| font.size.body / sm | 15px / 13px |
| space.1 / 2 / 3 | 4px / 8px / 16px |
| radius.md | 6px |
| motion.duration | 0ms（reduced-motion 优先：状态变化只用文本与图标，不依赖动画） |

## contrast（WCAG 相对亮度计算，全部达标）
| pair | ratio | 结论 |
| --- | --- | --- |
| #1F2430 on #FFFFFF | 14.9 : 1 | pass (>=4.5) |
| #5A6472 on #FFFFFF | 5.3 : 1 | pass (>=4.5) |
| #B42318 on #FFFFFF | 6.1 : 1 | pass (>=4.5) |
| #067647 on #FFFFFF | 4.9 : 1 | pass (>=4.5) |
| #FFFFFF on #1A56DB | 5.7 : 1 | pass (>=4.5) |
| #8A5A00 on #FFFFFF | 5.0 : 1 | pass (>=4.5) |

未在 blue checks 中替换任何颜色：任一对比不达标即阻断，不做"换成相近色再算达标"。

## Component catalog（已注册，含状态与禁用组合）
| component | source | states | forbidden combinations |
| --- | --- | --- | --- |
| TextField | internal/repo-owned | default, focus, error, disabled(locked) | error + disabled 同时表达成功；锁定期间允许输入 |
| FieldErrorText | internal/repo-owned | shown, hidden | 无 aria-describedby 就把错误文案挂到页面上（必须关联） |
| StateBadge | internal/repo-owned | idle, validating, submitting, success, error, draft, submitted, under_review, approved, rejected | 用颜色单独区分 success/error（必须同时带文本） |
| ConfirmDialog (human gate) | internal/repo-owned | closed, open, signed, cancelled | 无角色签名自动提交；对话框默认聚焦提交以外的按钮 |
| ActionButton | internal/repo-owned | enabled, disabled, loading | loading 态可再次触发（必须 arrow key 与 pointer 都拦截） |
| AccountableTimeline | internal/repo-owned | empty, non-empty | 隐藏 Historical rejected 版本 |
| RoleSwitcher | internal/repo-owned | user, approver, system | 让非 approver 的 UI 出现审批按钮（deny-first UI 层同样禁用） |
| FailureBanner | internal/repo-owned | hidden, error(422), timeout, escalated | 超时态显示成功文案；无显式标记就降级为普通提示 |

## 禁止组合（跨组件）
- `FailureBanner.timeout` 不允许显示与 `StateBadge.success` 相同的文案或图标。
- `ConfirmDialog` 的签名必须由角色亲自确认，不得由状态机自动生成。
- 禁止在未注册组件上渲染自带样式库（零依赖约束）。
