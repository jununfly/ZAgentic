# 04 · S5 Flow — ui-flow/v1 六义与可达性

> 来源 skill：zj-ui-flow（S5 FLOW）。六义分义存续：screen / component / state / action /
> intent / acceptance；semantic round-trip 通过；unknown 保留；双写 owner 阻断。
> 冻结指令 #5：每个状态迁移都必须能从 UI 触发（S1 可达性）。

## screen（界面）
- S1 资料编辑页；S2 费用报销审批页（tab 切换，各自独立状态机实例）。

## state（状态）
- 表单：`idle → validating → submitting → success | error`（error → validating via recover）。
- 审批：`draft → submitted → under_review → approved | rejected`（rejected → draft via revise）。

## component → action（每迁移都有可达控件，observer 可查）
### 表单
| 迁移 | UI 控件 |
|---|---|
| idle→validating | 「加载当前资料」按钮 + 输入框 input 事件 |
| validating（实时校验） | 输入框 oninput 触发 validate |
| validating→submitting | 「提交资料（需确认）」按钮（校验通过才可点） |
| submitting→success | 模拟服务端 200（transport 解析） |
| submitting→error(422) | scenario=422 单选 + 提交 |
| submitting→error(0) | scenario=超时 单选 + 提交 |
| error→validating | 「恢复并重新编辑」按钮（recover） |

### 审批
| 迁移 | UI 控件 |
|---|---|
| draft→submitted | 「提交报销单（需确认）」按钮 |
| submitted→under_review | 「路由到审批中」按钮（system） |
| under_review→approved | 「通过（需确认）」按钮（仅 approver 可用） |
| under_review→rejected | 「驳回（需确认）」按钮（仅 approver，理由必填） |
| under_review（超时） | 「模拟超时 / 升级」按钮（状态保持，可升级） |
| rejected→draft | 「修改并重新提交（新一版）」按钮（revise） |

## intent（意图）
- 表单：用户显式确认后才保存；失败可恢复；超时不伪造成功。
- 审批：申请人显式提交；审批人独占决定权；驳回留痕；改完重提交成新版。

## acceptance（验收，映射到 fixture）
- F-1 成功 200；F-2 必填拦截；F-3 邮箱格式；F-4 重复提交抑制+单次写入；F-5 422 可恢复；
  F-6 超时 fallback+显式标记；A-1 双 gate 通过；A-2 驳回留理由；A-3 非法金额/空事由拦截；
  A-4 重复提交忽略；A-5 超时升级不前进；A-6 越权 deny-first 不前进。

## round-trip 自检
- 状态机 export 名称与驱动严格一致；snapshot 键集覆盖 expected.json 全部键；
  stableStringify 排序键保证可比较。unknown 四元组已在 01 保留，未丢弃。
