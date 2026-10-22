# UI-DESIGN tokens & catalog — R3/h8（方向选定后固化）

方向：card-b `Explicit Gate`（见 02-direction.md，human gate 已签）。

## Tokens
| 类别 | token | 值 |
| --- | --- | --- |
| 色 | `--surface` | `#FFFFFF` |
| 色 | `--panel` | `#F5F6F8` |
| 色 | `--ink` | `#1B1F24` |
| 色 | `--muted` | `#5B6472` |
| 色 | `--accent` | `#14509B` |
| 色 | `--ok` | `#0F7B3F` |
| 色 | `--ok-chip` | `#E6F4EC` |
| 色 | `--danger` | `#B3261E` |
| 色 | `--warn` | `#8A5A00` |
| 色 | `--warn-chip` | `#FFF6E0` |
| 字号 | `--fs-label` / `--fs-body` / `--fs-num` | `12px` / `14px` / `14px mono` |
| 间距 | `--sp-1..4` | `4 / 8 / 12 / 20 px` |
| 圆角 | `--radius` | `6px` |
| 动效 | `--dur-state` | `120ms`（只做颜色/描边过渡；`@media (prefers-reduced-motion: reduce)` 下归零） |
| 边框 | `--stroke` | `1px solid #D6DAE0`，错误态换 `#B3261E` 并保持 1px 不靠加粗表达 |

## Contrast 校验（全部达标，实测值）
| pair | ratio | 门槛 |
| --- | --- | --- |
| ink on surface | 16.561 | 4.5 ✓ |
| muted on surface | 5.982 | 4.5 ✓ |
| muted on panel | 5.532 | 4.5 ✓ |
| white on accent | 7.923 | 4.5 ✓ |
| danger on surface | 6.536 | 4.5 ✓ |
| ok on surface | 5.350 | 4.5 ✓ |
| warn on warn-chip | 5.507 | 4.5 ✓ |
| white on danger | 6.536 | 4.5 ✓ |
| ink on warn-chip | 15.386 | 4.5 ✓ |
| ink on ok-chip | 14.602 | 4.5 ✓ |

规则：不达标时 **不得换成相近色重算**，只能改值后重跑；本次无此项。

## Component catalog（全部自有来源，无外部 runtime）
| 组件 | 来源 | 状态 |
| --- | --- | --- |
| `TextField` | 本仓库 | default / focused / **invalid(+message)** / disabled / locked |
| `ConfirmGate` | 本仓库 | unsigned / signed / blocked（blocked 下不可签） |
| `PrimaryButton` | 本仓库 | idle / hover / **busy(disabled)** / disabled |
| `StatusBadge` | 本仓库 | idle/validating/submitting/success/error；draft/submitted/under_review/approved/rejected |
| `ErrorBanner` | 本仓库 | visible(error) / visible(timeout, 带显式未确认标记) / hidden |
| `DecisionPanel` | 本仓库 | enabled(approver) / **denied(non-approver)** / needs-reason |
| `VersionList` | 本仓库 | collapsed / expanded（历史驳回版本保留） |

## Forbidden combinations（禁止组合，违反即阻断）
1. `PrimaryButton[busy]` + 可点击提交（= 重复写入）。
2. `StatusBadge[submitting]` + `Success` 文案同时出现（= 伪造成功）。
3. `ConfirmGate[unsigned]` + 任何 write 动作（= 自动提交）。
4. `DecisionPanel[denied]` + 状态前进（= 越权放行）。
5. `TextField[invalid]` + `PrimaryButton[enabled]`（= 校验不过还能提交）。
6. `StatusBadge[timeout/error]` + `persisted=true` 展示（= 谎报持久化）。
