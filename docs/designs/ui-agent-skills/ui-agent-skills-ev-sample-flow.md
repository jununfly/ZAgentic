# Experience Version 样例流程冻结（EV-v0.1 / Wave 0 · 节点 1-8-1）

> **归属节点**：1-8-1（为表单/审批 Experience Version 固化 PRD、角色状态、canonical artifact 与 fixture manifest）
> **事实源**：ui-agent-skills 路线图（已收口，carrier 文件已清理）
> **对齐文档**：`ui-agent-skills-scope-manifest.md`（EV-v0.1 冻结）、`ui-agent-skills-ev-form-lock.md`、`ui-agent-skills-ev-metrics.md`、`ui-agent-skills-canonical-schema.md`、`ui-agent-skills-ui-flow-v1-contract.md`、`ui-agent-skills-fixture-manifest.md`、`ui-agent-skills-trust-chain-contract.md`、`ui-agent-skills-deny-fixtures-contract.md`、`ui-agent-skills-skill-capability-manifest.md`
> **状态**：sample flow 冻结版（**双样例：表单 + 审批**）。审批流于 **2026-10-21** 经 zj 决策从 Wave 1 候选提升为 Wave 0 **第二条独立 sample**（见 §0）。

---

## 0. 范围变更记录（2026-10-21，pre-run scope amendment）

- **决策**：zj 选择「第二条独立 sample」形态——Wave 0 从「单表单」扩为「**用户资料编辑表单 + 费用报销审批流**」两条并行 experience path，各自有角色 / 状态 / fixture。
- **与节点 1-8 标签一致**：节点 `1-8` 标签本就是「表单/审批 sample flow」；此前 1-8-1 因冻结 `scope-manifest`「审批归 Wave 1」而收窄为纯表单，属偏离。本次范围扩张使 `1-8` 标签与 scope 重新对齐，**不再需要改 1-8 标签**。
- **治理落点**：因 `1-9`（paired run）尚未执行，**无 run 作废**（`ev-metrics.md` §5/§6 的「旧三次 run 作废」当前 N/A）。但 scope 变更须留痕：本变更直接修订 `scope-manifest.md` / `ev-form-lock.md` 冻结文档，并**待 `1-10` 重评轨道正式归档**（`e18 = 1-9 → 1-10` 阻塞，1-9 毕业后解锁）。
- **1-8-1 重开**：因 scope 扩张，1-8-1 曾于表单-only 下标记 completed；现重开为 `in_progress`，扩写双样例后重新收口（本文件即扩写结果）。

---

## 1. Sample PRD

### 1.A User Profile Edit Form（表单样例，EV-v0.1 原主体）

#### 1.A.1 目标用户与任务（对齐 `UI-BRIEF.md` 字段）
- **goal_users**：已登录终端用户（个人资料 owner）。
- **goal_task**：在 Next.js 应用中查看并编辑个人资料（昵称、邮箱、简介等受控字段），提交后由本地 mock 持久化，得到成功/错误反馈并可恢复。

#### 1.A.2 约束（constraints）
- **框架锁**：Next.js 14（App Router）+ React 18 + TypeScript 5.x + 固定 major 的 Chromium（`ev-form-lock.md` §1；与 `env-fingerprint` 对齐）。
- **数据边界**：本地 mock / 内存态，无真实后端写回；远程写回仅作 `1-8-5` 演练项（`scope-manifest.md` §1）。
- **安全边界**：危险 action（真实网络写回、删除账号等）deny-first（`trust-chain-contract.md` / `deny-fixtures-contract.md`）。
- **确定性**：fixture + env fingerprint 固定（`fixture-manifest.md` / `env-fingerprint.md`）。

#### 1.A.3 成功标准（success_criteria）
- 成功路径 **F-1**：合法提交 → mock 200 + 本地持久化 + `success` 态。
- 边界路径 **F-2~F-6** 均可被确定性验证捕获且 **fail-closed**（绝不伪造成功，`golden-fixtures-spec` §8）。
- 同一 case 可由对话或 `UI-BRIEF.md` diff 进入同一 canonical revision 与 plan（`1-8` exit 判据）。
- 方向卡、tokens/catalog、flow/action/intent、prototype/preview、approval、receipt 全程可追溯。
- 远程服务/未知字段/素材 quarantine 等失败场景均有本地 fallback 且不伪造成功（`1-8` exit 判据）。

#### 1.A.4 In / Out of scope（本 sample）
- **In**：表单六类 fixture（F-1~F-6）、六类 canonical artifact 全链路、本地 Human gate、静态 preview fallback。
- **Out**：审批流（见 1.B）、真实后端、多 EV 并行、adapter 完整治理（仅 `1-7-5`/`1-8-5` 局部演练，正式治理归 `1-10`）。

### 1.B Expense Reimbursement Approval（审批样例，2026-10-21 新增第二条 sample）

#### 1.B.1 目标用户与任务
- **goal_users**：已登录终端用户（报销**申请人 Applicant**）+ 审批人（**Approver / reviewer**）。
- **goal_task**：申请人填写费用报销单（金额、事由、附件 mock），提交后进入审批；审批人查看并 **通过 / 驳回**；驳回后申请人可修改重提交；通过则标记 `approved` 并 mock 持久化。

#### 1.B.2 约束（constraints）
- **框架锁**：同表单（Next.js 14 + React 18 + TS 5.x + 固定 major Chromium）。
- **数据边界**：本地 mock / 内存态；审批状态本地模拟，无真实后端写回。
- **安全边界**：审批 action 必须 `role=approver`（deny-first；非审批人调用审批 = 越权，阻断）。
- **确定性**：fixture + env fingerprint 固定。

#### 1.B.3 成功标准（success_criteria）
- 成功路径 **A-1**：合法提交 → `under_review` → approver `approve` → `approved` + 持久化。
- 边界路径 **A-2~A-6** 均可被确定性验证捕获且 **fail-closed**。
- **双 Human gate**（申请人提交 + 审批人决定）全程可追溯，互不替代。

#### 1.B.4 In / Out of scope（本 sample）
- **In**：审批六类 fixture（A-1~A-6）、双角色 + 双 Human gate、canonical artifact 全链路（approval 复用 `review record` 的 `APPROVED/REJECTED/NEEDS_CHANGES`）。
- **Out**：真实后端、第三个 EV、审批链多级 / 会签（归 Wave 1）。

---

## 2. 角色与状态（固化，引用 `ev-form-lock.md` §2/§3）

### 2.1 角色（roles）
| 角色 | 职责 |
| --- | --- |
| 用户 / 申请人（User / Applicant） | 表单：查看资料、编辑字段、触发提交、处理成功/错误反馈与恢复；审批：填写报销单、提交、处理驳回重提交 |
| 审批人（Approver） | 审批：查看申请、通过/驳回（附理由）、触发 `approved`/`rejected` |
| 系统 / 表单（System） | 字段级校验、提交/审批态管理、调用 mock 持久化、返回成功/错误 |

### 2.2 状态机（states）
```
[Form]      idle
              → validating      (字段级实时校验)
              → submitting      (提交中，输入锁定)
              → success | error
            error ──(用户修正)──> validating   (回到 editable)

[Approval]  draft
              → submitted       (提交，输入锁定)
              → under_review    (审批中)
              → approved | rejected
            rejected ──(修改重提)──> draft
```
- 表单子状态：字段级 `valid`/`invalid`；提交级 `submitting`/`success`/`error`。
- 审批子状态：`draft` / `submitted` / `under_review` / `approved` / `rejected`。
- **审批态（pending/approved/rejected）现纳入 EV-v0.1**（2026-10-21 决策；此前 §1 不锁项已移除）。

---

## 3. Canonical artifact 映射（双样例共用）

六类 artifact 的生产 skill / 消费下游 / sample 关键点（依据 `canonical-schema.md` + `skill-capability-manifest.md`）：

| # | Artifact | 生产 skill | 消费 / 下游 | sample 关键点 |
| --- | --- | --- | --- | --- |
| 1 | `UI-BRIEF.md` | `zj-ui-brief` | `zj-ui-flow` / `zj-ui-direction` | `goal_users`/`goal_task`/`constraints`/`success_criteria` 齐备；缺 `success_criteria` → `NEEDS_CONTEXT`（FF-BRIEF-02） |
| 2 | `UI-DESIGN.md` | `zj-ui-direction` + `zj-ui-design-system` | `zj-ui-flow` | `direction_choice` 必须 Human 签（FF-DIR-02）；`license: unknown` → quarantine（FF-DIR-03）；contrast 不达标阻断（FF-DS-02/03） |
| 3 | `ui-flow/v1` | `zj-ui-flow` | `zj-ui-prototype` / `zj-ui-verify` | `screen/component/state/action/intent/acceptance` 六义齐全；未注册组件阻断；危险 action deny |
| 4 | `review record` | `zj-ui-visual-review` | `zj-ui-handoff` | Human gate `APPROVED/REJECTED/NEEDS_CHANGES`；未签 → `HUMAN_REVIEW_REQUIRED` |
| 5 | `verification receipt` | `zj-ui-verify` | `1-9` graduation | `fixture_hash` + `environment_fingerprint` 绑定；缺失 env → `BLOCKED`；fail-closed |
| 6 | `handoff` | `zj-ui-handoff` | 维护 / `1-10` | `change_summary`/`run_commands`/`risks`/`fallback`/`owner` 齐备 |

**审批样例差异说明**：审批在 `review record` 上引入**第二个 Human gate**（approver，对应 `role=approver`），与表单的 user-submit gate 区分；`APPROVED/REJECTED` 须由 approver 实签，不可系统自动（`GF-A2`）。其余 artifact 生产 skill 完全复用。

**辅助 skill**（非直接产出 canonical，但 sample 链路必经）：
- `zj-ui-discover`：从 catalog 发现已注册组件（`component` 字段来源；未注册 → 阻断）。
- `zj-ui-prototype`：从 `ui-flow/v1` 生成本地 prototype/preview（`1-8-4`）。
- `zj-ui-break`：演练失败/边界并修复（F-2~F-6、A-2~A-6、`1-8-5`）。
- `zj-ui-verify`：硬门禁聚合（`1-5-3`）。

**sample 链路顺序（建议）**：
`zj-ui-brief`（UI-BRIEF）→ `zj-ui-discover`（catalog）→ `zj-ui-direction` + `zj-ui-design-system`（UI-DESIGN）→ `zj-ui-flow`（ui-flow/v1）→ `zj-ui-prototype`（preview）→ `zj-ui-visual-review`（review）→ `zj-ui-verify`（receipt）→ `zj-ui-handoff`。`zj-ui-break` 在任意出错点介入。审批样例在 `zj-ui-visual-review` 阶段叠加 approver gate。

---

## 4. Fixture manifest（sample 选择，复用全局冻结清单 + 新增审批类）

本 sample **直接复用** `ui-agent-skills-fixture-manifest.md`（`1-5-1` 冻结）中的 **form 六类 F-1~F-6** 与 **contract GF-01~GF-11**（sample 全链路必过），并**新增 approval 六类 A-1~A-6 + approval 专属 contract GF-A1~GF-A3**。新增项须在 `1-5-1` 正式登记（经 `decide` 落盘并重算 `manifest_hash`）后方可进入 `1-9` paired run；本节点只冻结**选择口径**，不落地数据。

### 4.1 form 六类（sample 主路径，已冻结）
| ID | 内容 | 触发路径 | 预期结果 | 落地点 |
| --- | --- | --- | --- | --- |
| F-1 | 成功路径（合法 profile） | `idle→validating→submitting→success` | mock 200 + 本地持久化 | `tests/ui-agent-skills/fixtures/form/F-1` |
| F-2 | 空提交 | 必填校验 | 字段级 error，禁止提交 | `tests/ui-agent-skills/fixtures/form/F-2` |
| F-3 | 非法格式（邮箱/长度） | 实时校验 | 字段级 error message | `tests/ui-agent-skills/fixtures/form/F-3` |
| F-4 | 重复提交（提交中再触发） | `submitting` 锁输入 | 第二次提交被拒/忽略 | `tests/ui-agent-skills/fixtures/form/F-4` |
| F-5 | 服务端 422 | 模拟 mock 422 | `error` 态 + 可恢复回 editable | `tests/ui-agent-skills/fixtures/form/F-5` |
| F-6 | 超时 | 模拟服务端超时 | fallback 到稳定路径 / 显式标记 | `tests/ui-agent-skills/fixtures/form/F-6` |

### 4.2 approval 六类（已登记，2026-10-21 追溯登记，见 `fixture-manifest.md` §2.5）
| ID | 内容 | 触发路径 | 预期结果 | 落地点 |
| --- | --- | --- | --- | --- |
| A-1 | 成功审批（合法申请 → approver 通过） | `draft→submitted→under_review→approved` | mock 持久化 + approved | `tests/ui-agent-skills/fixtures/approval/A-1` |
| A-2 | 审批驳回（附理由） | `under_review→rejected` | 申请人可修改重提交（回 draft） | `tests/ui-agent-skills/fixtures/approval/A-2` |
| A-3 | 非法金额 / 空事由（客户端校验） | `draft` 校验 | 字段级 error，禁止提交 | `tests/ui-agent-skills/fixtures/approval/A-3` |
| A-4 | 重复提交（submitted 期间再触发） | `submitted` 锁 | 第二次被拒/忽略 | `tests/ui-agent-skills/fixtures/approval/A-4` |
| A-5 | 审批超时 / 升级 | `under_review` 超时 | fallback 稳定路径 / 显式标记 | `tests/ui-agent-skills/fixtures/approval/A-5` |
| A-6 | 越权审批（非 approver 调用审批） | 任意 | deny-first 阻断 + 报路径 | `tests/ui-agent-skills/fixtures/approval/A-6` |

### 4.3 contract（sample 必过的确定性断言，源自 GF-01~GF-11）
- GF-01 正常 flow round-trip（canonical→projection→canonical 语义集合等价）
- GF-02 缺 required 字段必须阻断（hard fail）
- GF-03 未知字段保留 `unknown` 四元组并生成 warning（静默丢弃 = fail）
- GF-04 adapter 越权修改 owned 字段必须失败并报路径
- GF-05 `unknown` 不得压成空值/null
- GF-06 重复/冲突 action 拒绝提交
- GF-07 并发转换幂等（同幂等键不产生重复/半套结果）
- GF-08 迁移向后兼容；破坏性变更升主版本 + 迁移器
- GF-09 schema lock 重跑（修改后重跑全套，失败保留旧 artifact）
- GF-10 离线恢复（服务关闭仅凭本地 canonical 重建 flow/恢复状态/重放动作）
- GF-11 adapter 删除恢复（删 adapter 后仍可从最后完整 canonical revision 恢复）

### 4.4 approval 专属 contract（已登记，2026-10-21 追溯登记，见 `fixture-manifest.md` §2.3）
- **GF-A1** 审批 action 必须 `role=approver`，否则 deny-first 阻断（role separation）。
- **GF-A2** approver 决定的 `APPROVED`/`REJECTED` 必须由 Human 实签，不可系统自动生成。
- **GF-A3** `rejected` 后申请人重提交生成**新 revision**，旧 `approved` 状态不污染新链路。

### 4.5 fixture 选择约束
- sample 的 paired run（`1-9`）fixture 必须取自本清单 F-1~F-6 + A-1~A-6 + 相关 GF / GF-A*；任何未列 fixture → 该 run 按 invalid 处理（`fixture-manifest.md` §5）。
- 数据文件落地：F-1~F-6 与 A-1~A-6 的 `input.json`+`expected.json` 已于 **2026-10-21** 经独立 chore 落盘（见 `fixture-manifest.md` §2.1 / §2.5），状态均 `ready`；本节点仍只冻结**选择口径**与契约，不编写可执行断言（可执行断言待 1-5-2 runner 与 1-6 技能实现后跑）。
- A-* 与 GF-A* 已于 2026-10-21 登记（见 `fixture-manifest.md` §2.5 / §2.3）；paired run 取用须按本清单，未登记 fixture 不得使用。

---

## 5. 退出判据对齐（1-8-1）

> 退出判据原文：「sample PRD、artifact、角色状态和 fixture manifest 固定且与 scope 一致」

- ✅ **固定**：本文件 §1 PRD（双样例）、§2 角色状态、§3 canonical artifact 映射、§4 fixture 选择均已冻结为单一 spec。
- ✅ **与 scope 一致**：全部对齐扩张后的 `scope-manifest`（表单 + 审批双样例）、`canonical-schema`（六类 artifact）、`fixture-manifest`（F-* + A-* + GF-* / GF-A*）；范围冲突已在 §0 显式消解。
- ⏭️ **不在本节点**：真实 fixture 数据落地（`1-5-2`/`1-6`，含 A-* 登记）、对话↔UI-BRIEF diff（`1-8-2`）、direction/prototype/verify/handoff 演练（`1-8-3`~`1-8-5`）。

---

## 6. 引用
`ui-agent-skills-scope-manifest.md` · `ui-agent-skills-ev-form-lock.md` · `ui-agent-skills-ev-metrics.md` · `ui-agent-skills-canonical-schema.md` · `ui-agent-skills-ui-flow-v1-contract.md` · `ui-agent-skills-fixture-manifest.md` · `ui-agent-skills-env-fingerprint.md` · `ui-agent-skills-trust-chain-contract.md` · `ui-agent-skills-deny-fixtures-contract.md` · `ui-agent-skills-golden-fixtures-spec.md` · `ui-agent-skills-skill-capability-manifest.md`
