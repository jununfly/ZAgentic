# verification receipt — 两个流程的实现验证

| 字段 | 值 |
| --- | --- |
| claim | 12 条冻结 fixture（form 6 / approval 6）由真实状态机驱动，全部 match；页面在提交/审批前均要求显式确认 |
| threshold | 12/12 match，driver 退出码 0；one mismatch = FAIL |
| command | `node run-fixtures.mjs <fixtures-root>`（cwd=`artifact/`） |
| artifact | `artifact/index.html`、`artifact/form.html`、`artifact/approval.html`、`artifact/src/**/*.mjs` |
| oracle | `tests/ui-agent-skills/fixtures/{form,approval}/*/expected.json`（只读） |
| environment | darwin arm64；node v22.22.2；零依赖 ESM，无网络 |
| commit | 不可用：本轮禁止任何 git 命令，因此不提供 commit，也不以 baseline 冒充本次通过 |
| checked | 12 fixtures（F-1..F-6, A-1..A-6） |
| status | PASS |

## 逐格结果

| fixture | 结果 | 关键观测 |
| --- | --- | --- |
| F-1 | PASS | success；persisted=true；gate user@3 实签 |
| F-2 | PASS | validating；error_fields=[nickname]；submit_blocked；无 gate |
| F-3 | PASS | validating；error_fields=[email]；submit_blocked |
| F-4 | PASS | submitting 二次提交被忽略；writes=1；human gate 仅 1 次 |
| F-5 | PASS | error；recoverable；未写盘 |
| F-6 | PASS | error；fallback=stable_path；explicit_marker=true |
| A-1 | PASS | approved；persisted；applicant@1 + approver@3 双签 |
| A-2 | PASS | rejected；persisted；驳回理由在 timeline |
| A-3 | PASS | draft；金额负数与空事由字段级拦截；gate 未签 |
| A-4 | PASS | submitted 保持；重复提交被忽略；未重复建单 |
| A-5 | PASS | under_review 保持；升级标记；不伪造通过/驳回 |
| A-6 | PASS | 非 approver 调用被拒；状态不前进；无 gate |

## 未覆盖与已知边界

- 浏览器交互（DOM/focus/aria）未做自动化断言：本机离线，无浏览器驱动；页面按 catalog 实现
  label/aria-invalid/aria-describedby/role=status，仅做了静态审查，不能算作 PASS 证据。
- localStorage 持久化在 driver 中替换为内存 store，语义一致（同 commit/writes 计数）。
- 撤回（撤回申请）不在需求内，未实现，也未声称覆盖。

空证据不放行：以上 12 条由命令实跑产出，`.run-fixtures-result.json` 为落盘凭证。
