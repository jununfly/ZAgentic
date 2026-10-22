# Verification receipt — R3/h8

## 验证矩阵（每条都有可重放命令）
| cell | claim | threshold | command | result |
| --- | --- | --- | --- | --- |
| product-grammar | 12 条冻结 fixture 全部逐键通过 | 0 mismatch | `node run-fixtures.mjs <fixtures-root>` | PASS (exit 0, all_match true) |
| grammar-usage-of-runtime | 逻辑在 .mjs 模块里，HTML 只做绑定 | 0 处业务逻辑在 inline script | `node -e "read index.html"` + grep `import` | PASS |
| runtime-reachability | 每条声明的迁移都有 UI 控件触发 | 0 UNREACHABLE | 遍历 `TRANSITIONS` × index.html | PASS (24/24 reachable) |
| runtime-failure-path | 422 / timeout 都不伪造成功 | persisted 必须 false | fixture F-5 / F-6 | PASS |
| runtime-lock-path | 重复提交只写一次 | writes == 1 | fixture F-4 | PASS |
| runtime-authority-path | 非审批人调用不前进状态 | final_state 不变 + persisted false | fixture A-6 | PASS |
| runtime-replay | 未知响应码 deny-first | 抛错而非猜义 | `outcomeFromCode(499)` | PASS (UnknownResponseError) |
| contrast | 10 组前景/背景对比度达标 | ratio >= 4.5 | WCAG 相对亮度实算 | PASS (最低 5.350) |
| dom-binding | 脚本引用的元素 id 全部存在 | 0 missing | id 集合比对 | PASS (41 used / 44 declared, missing none) |
| reduced-motion | 尊重系统偏好 | 动效归零 | `@media (prefers-reduced-motion: reduce)` | PASS |

## 未达标项
无。所有 cell 都在本次环境跑过，没有沿用任何旧基线。

## 显式标记语义（防止把未知显示成已保存）
- `submitting`：按钮 busy + 输入 disabled，文案是"Saving..."，不是"Saved"。
- `error (422)`：`Not saved. 422 ...`，persisted 假，提供「Edit and retry」。
- `error (timeout)`：额外带 `[fallback=stable_path]` 与 `[state unconfirmed - nothing was written]`。
- `under_review` 超时：走 `stable_path` 升级到人工接管，不落 approver/reject 决策。
- 决策被拒：UI 显示 deny code 列表（`actor_role_not_approver` / `actor_is_applicant_self_approval`），状态不前进。

## 已知保留项（unknown，未被压空）
`bio_max_length` 取 200 并在界面展示剩余字数；`attachment_required` 保持 optional；
`timeout_budget_ms`（UI 用 600ms、审批用 30s）与 `approver_assignment`（页面写死 applicant/approver）仍为 unknown。
