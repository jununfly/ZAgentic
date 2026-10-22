# Experience Version 表单 + 审批样例锁定（EV-v0.1 / Wave 0）

> 归属路线图节点：1-1-2（锁定 React/Next.js 表单样例的角色、状态、关键任务、框架版本、浏览器、数据边界）
> 配套：scope manifest `ui-agent-skills-scope-manifest.md`（EV-v0.1 冻结版）
> 状态：参数锁定版，可由 Human 复核；责任人项待 zj 确认。

## 1. 样例定位
- 类型：**用户资料编辑表单（User Profile Edit Form）+ 费用报销审批流（Expense Reimbursement Approval）**（两条并行；2026-10-21 zj 决策将审批从 Wave 1 候选提升为 Wave 0 第二条样例）
- 框架版本（固定组合，避免 15/19 的 breaking change 引入基线噪声）：
  - **Next.js 14（App Router）**
  - **React 18**
  - **TypeScript 5.x**
- 浏览器：**Chromium**（major 版本固定；与 1-5 确定性验证指纹对齐，含渲染引擎与字体基线）
- 数据边界：**本地 mock / 内存态，无真实后端写回**；持久化以本地 fixture 模拟，远程写回仅作 1-5/1-8 演练项

## 2. 角色（roles）

### 2.1 表单
| 角色 | 职责 |
| --- | --- |
| 用户（User） | 查看资料、编辑字段、触发提交、处理成功/错误反馈与恢复 |
| 系统 / 表单（System） | 字段级校验、提交态管理、调用 mock 持久化、返回成功/错误 |

### 2.2 审批（2026-10-21 新增第二条 sample）
| 角色 | 职责 |
| --- | --- |
| 申请人（Applicant） | 填写报销单（金额/事由/附件 mock）、提交、处理驳回重提交 |
| 审批人（Approver） | 查看申请、通过/驳回（附理由）、触发 approved/rejected |
| 系统 / 审批（System） | 字段级校验、审批态管理、mock 持久化、返回成功/错误 |

## 3. 状态机（states）

### 3.1 表单
```
idle
  → validating        (字段级实时校验)
  → submitting        (提交中，输入锁定)
  → success | error
error ──(用户修正)──> editable (回到 idle/validating)
```
- 字段级子状态：`valid` / `invalid`（附 error message）
- 提交级子状态：`submitting` / `success` / `error`

### 3.2 审批（2026-10-21 新增）
```
draft
  → submitted         (提交，输入锁定)
  → under_review      (审批中)
  → approved | rejected
rejected ──(修改重提)──> draft
```
- 审批子状态：`draft` / `submitted` / `under_review` / `approved` / `rejected`
- 审批 action 须 `role=approver`（deny-first；非审批人调用 = 越权）

## 4. 关键任务（key tasks）

### 4.1 表单
1. 加载并展示当前资料（mock 数据源）
2. 编辑字段（受控输入组件）
3. 客户端实时校验（必填、格式、长度）
4. 提交（valid 前 disabled；submitting 期间锁输入）
5. 服务端校验模拟（mock 返回 200 / 422）
6. 持久化（mock 写入本地 fixture）
7. 成功 / 错误反馈与错误恢复（回到 editable）

### 4.2 审批（2026-10-21 新增）
1. 申请人填写报销单（金额、事由、附件 mock）
2. 客户端校验（金额 > 0、事由必填）
3. 提交（submitted 期间锁输入）
4. 审批人查看并 通过 / 驳回（附理由）
5. 驳回 → 申请人修改重提交（回 draft，生成新 revision）
6. 通过 → 标记 approved，mock 持久化
7. 成功 / 失败反馈与错误恢复

## 5. 责任人（owner）— 已确认（2026-10-19）
- **产品 / 验收负责人：zj**（人类决策者，负责 scope 与 graduation 判定）
- **实现负责人：zjj**（AI 搭档，负责样例与 fixture 落地）
- 注：zj 已于 2026-10-19 确认此责任分配；后续如需调整为一处归属或引入其他 owner，单独告知即可。
