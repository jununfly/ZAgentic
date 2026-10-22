# UI-BRIEF · 用户资料编辑表单

stage: S1 INTAKE
source: ../raw-requirement.md (R1-pilot)
revision: 1

## goal

让已登录用户在本地 mock 环境下查看并修改自己的资料（昵称 / 邮箱 / 简介），
在实时校验与显式确认的保护下完成一次可恢复的保存。

## goal_users

已有账号、需要更新公开资料的个人用户；使用键盘或读屏的桌面端用户。

## tasks

1. 打开页面时加载并展示当前资料（昵称、邮箱、简介）。
2. 编辑任一字段时立即校验，错误就地展示且指明字段。
3. 校验不通过时禁止提交；提交中锁定全部输入。
4. 提交前必须由用户显式确认（二次确认），不得自动提交。
5. 提交成功给出成功反馈；失败给出可读原因，并允许用户修改后再次提交。

## constraints

- 数据源为本地 mock，禁止真实后端与网络请求。
- 实现为零依赖 ESM JavaScript + 静态 HTML（离线 pilot 栈约束）。
- 状态与校验逻辑必须可被 headless runner 驱动（F-1）。
- 提交失败必须可恢复：error 态 -> 编辑 -> 再确认 -> 再提交。

## success_criteria

- F-1 断言全绿：`final_state=success`、`persisted=true`、`error_fields=[]`、
  `submit_blocked=false`、`human_gates=[{role:user,signed:true,at_step:3}]`。
- 失败路径可复现：mock 返回 422/500 时进入 error 态，且不写入持久层。
- 用户确认是人类实签，不是系统代签。

## unknowns

```json
[]
```

> 需求四类必填齐全，本轮无 unknown。校验阈值取产品常规值：昵称 <= 24 字、简介 <= 160 字，
> 这些是 S1 的显式假设，记录在 UI-DESIGN.md 的 tokens 说明中，便于后续被用户覆盖。

## human_gate

- 方向选择：required，见 UI-DIRECTION.md 的签署记录。
- 提交动作：每次提交必须由 user 角色签署（F-1 step 3）。
