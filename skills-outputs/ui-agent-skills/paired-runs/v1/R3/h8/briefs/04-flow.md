# ui-flow/v1 — R3/h8（六义分义存续，任一义缺失 = hard fail）

## Flow A · 用户资料编辑表单

### screen
`ProfileEdit`：标题 + 三个 `TextField` + `ConfirmGate` + `PrimaryButton` + `StatusBadge` + `ErrorBanner`。
`*` 每个字段下方固定一行 `--fs-label` 高的错误位，避免校验触发时布局跳动。

### component
`TextField(nickname)` `TextField(email)` `TextField(bio)` `ConfirmGate(save)` `PrimaryButton(save)`
`StatusBadge` `ErrorBanner` `MockServerControl(200 / 422 / timeout)`。

### state
`idle` → `validating` → `submitting` → `success`；（`submitting` → `error`）→ `validating`（recover）。
锁：`submitting` 期间所有 TextField disabled + PrimaryButton busy，且输入不再改写 state。

### action（actor, from → to, guard）
| action | actor | from → to | guard |
| --- | --- | --- | --- |
| `load` | system | any → `idle` | 无 |
| `edit(field)` | user | `idle`/`validating`/`success`/`error` → `validating` | 非 `submitting` |
| `validate` | system | `validating` → `validating` | 产出 `error_fields` |
| `submit` | user | `validating` → `submitting` | `ConfirmGate signed` 且 `error_fields == []` |
| `submit`(重复) | user | `submitting` → `submitting` | 拒收，记 `duplicate_suppressed`，不产生 write |
| `persist(200)` | system | `submitting` → `success` | write += 1，`persisted = true` |
| `persist(422)` | system | `submitting` → `error` | `recoverable = true`，不写库 |
| `persist(timeout)` | system | `submitting` → `error` | 走 fallback 稳定路径 + `explicit_marker = true`，不写库 |
| `recover` | user | `error` → `validating` | 无 |

### intent
- 让用户**始终知道**当前资料是"已保存 / 未保存 / 保存结果未知"，不允许把未知显示成已保存。
- 让用户承担"确认"这一步，系统不得代签。
- 让重复点击在网络层只产生一次写入。

### acceptance
- F-1 成功路径：`success` + persisted + 1 次 write + user gate 实签。
- F-2 必填、F-3 格式/长度：`validating` + 字段级 error + submit blocked + 无 gate。
- F-4 重复提交：`duplicate_suppressed` + `writes == 1`。
- F-5 422：`error` + `recoverable`，不伪造成功。
- F-6 超时：`error` + fallback 稳定路径 + `explicit_marker`，不伪造成功。

## Flow B · 费用报销审批

### screen
`ExpenseApproval`：`requestForm`（金额/事由/附件引用）→ `routeZone`（系统派发）→ `decisionZone`（审批人通过/驳回）
→ `historyZone`（历史版本）+ `StatusBadge`。

### component
`TextField(amount, mono)` `TextField(reason)` `TextField(attachment_ref)` `ConfirmGate(submit)`
`ActorPicker(applicant / approver / other)` `PrimaryButton(submit|route|approve|reject|escalate|revise)`
`StatusBadge` `VersionList`。

### state
`draft` → `submitted` → `under_review` → `approved` / `rejected` →（`rejected` 经 revise）→ `draft(v+1)`。

### action（actor, from → to, guard）
| action | actor | from → to | guard |
| --- | --- | --- | --- |
| `edit` | applicant | `draft`/`rejected`(→revise) | 非终态 |
| `submit` | applicant | `draft` → `submitted` | gate signed 且 `amount > 0` 且 `reason != ""` |
| `submit`(重复) | applicant | `submitted`/`under_review` → 同态 | 拒收，gate 记 `signed=false`，不新建申请 |
| `route` | system | `submitted` → `under_review` | 需要 UI 上的派发控件触发 |
| `timeout` | system | `under_review` → `under_review` | escalate 标记，不改成功/失败，也不写 decision |
| `approve` | approver | `under_review` → `approved` | `actor.role == approver` 且 actor ≠ applicant；deny-first |
| `reject` | approver | `under_review` → `rejected` | 同上 + `reason` 必填 |
| `revise` | applicant | `rejected` → `draft`(v+1) | 旧 rejected 版本保留 |
| `persist` | system | 终态决策 → 写库 | `persisted = true` |

### intent
- 把"谁有权推进状态"做成机器可判的 deny-first 检查，而不是 UI 层的隐藏按钮。
- 让驳回信息完整到可以直接改：必须有理由，且历史版本不丢。
- 让超时升级停在"可被人工接管"的位置，不自动判定通过/驳回。

### acceptance
- A-1：`approved` + persisted + applicant/approver 双 gate 实签。
- A-2：`rejected` + persisted + 理由留存 + 可 revi 到新版本。
- A-3：金额 ≤ 0 / 事由空 → 停 `draft`，gate 未签，不写库。
- A-4：`submitted` 期间重复提交被拒，不新建申请。
- A-5：超时升级留 `under_review` + 显式标记，不伪造任何结论。
- A-6：非 approver 调用 → deny-first，`under_review` 不前进，不写库。

## unknown 四元组传递
`bio_max_length` / `attachment_required` / `timeout_budget_ms` / `approver_assignment` 四个缺口从 brief
原样带入并在每次 round-trip 后仍为 `{path, raw, reason, source}` 四键完整，未被压空或替换成猜测值。
