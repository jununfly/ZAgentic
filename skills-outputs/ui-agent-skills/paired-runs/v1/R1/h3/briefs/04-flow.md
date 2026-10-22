# ui-flow/v1 — 六义（S5）

六义分义存放，互不合并：screen / component / state / action / intent / acceptance。

## 1. screen
| id | 路由 | 说明 |
| --- | --- | --- |
| `hub` | index.html | 两个流程的入口与状态摘要 |
| `profile` | form.html | 用户资料编辑表单 |
| `expense` | approval.html | 费用报销审批（申请人视图 + 审批人视图同页分栏） |

## 2. component
只引用 catalog 内组件：`Field`、`PrimaryButton`、`ConfirmGate`、`StatusBanner`、`Timeline`、`RoleSwitch`。
页面不新增组件；状态展示全部由这六个组合而成。

## 3. state
form：`idle → validating → submitting → success | error → validating`（error 可恢复）。
approval：`draft → submitted → under_review → approved | rejected`；`rejected → draft`（新版本，旧版本保留）。

不变量：
- `submitting` 期间输入锁定，重复 submit 被忽略（不产生第二次写）。
- `error` 永不写盘，永不显示成功文案；超时额外落到稳定路径并打显式"结果未知"标记。
- `under_review` 只接受 `role=approver` 的 approve/reject；其余角色 deny-first，状态不前进。

## 4. action
| action | 发起方 | 守卫 | 效果 |
| --- | --- | --- | --- |
| `edit(field,value)` | user/applicant | state ∈ {idle,validating,error,draft,rejected} | 重算校验，进入 validating |
| `validate()` | system | — | 返回 `{result, errorFields}` |
| `submit({confirmed})` | user/applicant | 校验通过 且 confirmed 且未锁定 | 记 human gate，进入 submitting / submitted |
| `persist(response_code)` | system | state=submitting | 200 写盘→success；422→error(可恢复)；0/timeout→error+稳定路径 |
| `recover()` | user | state=error | 回 validating，保留输入 |
| `route()` | system | state=submitted | → under_review |
| `approve({confirmed,reason})` / `reject({confirmed,reason})` | approver | state=under_review 且 role=approver 且 actor≠applicant | 记 gate；驳回需 reason |
| `timeout()` | system | state=under_review | 保持 under_review，置升级标记 |
| `revise()` | applicant | state=rejected | → draft，version+1 |

## 5. intent
- 用户提交资料时想确认"这次真的存进去了"：success 才说成功，超时只说"结果未知，可重试"。
- 申请人提交时想确认"这一版已经交出去，且只有一版在途"。
- 审批人驳回时想留下可追溯的理由；申请人想看到被驳的是哪一版、改了之后是新一版。
- 任何角色越界时，系统要明确说"你没有这个权限"，而不是静默失败。

## 6. acceptance
| 断言 | 判定方式 |
| --- | --- |
| 合法提交落盘 | final_state=success 且 persisted=true，human_gates 含 signed 的 user gate |
| 必填/格式拦截 | error_fields 精确到字段，submit_blocked=true，无 gate |
| 重复提交 | duplicate_suppressed=true 且 writes=1 |
| 422 | final_state=error，persisted=false，可 recover |
| 超时 | final_state=error，fallback=stable_path，explicit_marker=true |
| 审批通过/驳回 | decided 态 + persisted=true + 双 gate 实签 |
| 越权 | final_state 不前进，human_gates 为空 |
| 审批超时 | 状态不变，无 gate，升级标记可被人工接管 |

unknown 四元组：空（本轮无缺口），round-trip 后仍为空数组，不压成 null。
