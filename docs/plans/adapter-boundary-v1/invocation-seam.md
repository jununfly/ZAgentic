# Adapter 调用 seam — 测试主体分层与故障注入契约

> 配套 `1-7-5`（删除/断网/远程故障恢复）。实现原语：`tests/ui_agent_skills_adapter_seam.py`；
> 调用面索引：`tests/ui-agent-skills/fixtures/adapters/registry/invocation-surface.json`；
> 证据：`tests/test_ui_agent_skills_adapter_seam.py`（24 用例）。
> 前置：`1-7-2`（本规格）、`1-7-3`（Storybook 真实运行时 adapter）、`1-7-4`（golden fixtures + drift harness）。

## 1. 问题：一条被误诊的约束

原始风险项表述为：

> 测试主体受限：仅 Storybook 离线可用；json-render/A2UI 无运行时投影引擎 →
> 断网/远程只能走契约级注入。

这是一条**误诊**。它把两件正交的事混为一谈：

| | 被测对象 | 故障来源 |
|---|---|---|
| 是什么 | 「adapter 报 X 类故障 → boundary 执行 Y 回退 → 本地恢复不变量仍成立」这条**决策性质** | 故障由谁产生 |
| 依赖运行时吗 | **不依赖**——它是一条接口（seam）上的性质 | 依赖 |

结论：**「只有 Storybook 有运行时」不是障碍，而是资产**。真实运行时用来校验 seam
的保真度；没有运行时的 adapter 根本不该进入 invocation 测试面。

真正会走错的两条路（都要避开）：

- **(a) 给 json-render / A2UI 造运行时** —— 越界。它们是 opt-in 投影 / 公开协议，
  `1-7-1` capability-fit 已定性，本仓库没有也不需要投影引擎。
- **(b) 把整个回退矩阵降级成「契约级断言」** —— 丢机器证据。回退决策是行为，
  行为必须有可执行的断言，不能只写文档。

## 2. 解法：三层测试主体

| 层 | 主体 | 作用 | 证据强度 |
|---|---|---|---|
| **L1** | Storybook（真实运行时，`RealAdapterSeam`） | 产出真实成功/失败 outcome；为保真度提供基准 | 真实运行时 |
| **L2** | `SimulatedAdapterSeam`（可编程故障注入） | 穷举回退矩阵：3 类故障 × 四态生命周期 | seam 契约（保真度由 L1 背书） |
| **L3** | json-render / A2UI（`invocation_surface: none`） | **退出** invocation/回退执行测试面；仅参与 lifecycle + removal R1–R5 + manifest 契约 | 无运行时，不声称 |

### 2.1 seam 契约

Boundary 只看到 `AdapterOutcome`，不看 adapter 内部：

- `outcome_class ∈ {ok, failure, network_loss, remote_failure}` —— 严格对应本规格
  §6.2 的三类故障 + 成功。
- `receipt_status` —— **正交**透传，不折叠进 `outcome_class`。
- 成功调用**没有**回退动作（`fallback_key is None`）。

### 2.2 为什么 receipt 状态必须正交

`ok`（seam 级：调用完成）完全可能携带 `QUARANTINED`（receipt 级：证据不可归因）。
若把 receipt 的 `QUARANTINED` 折叠进 `outcome_class`，就会和 adapter 生命周期的
`quarantine` 三级混淆——正是 [`quarantine-disambiguation.md`](./quarantine-disambiguation.md)
要防的事。seam 上保持正交，两级语义自动不串。

## 3. 调用面索引（deny-first）

无运行时 adapter 的排除必须**声明式且被断言**，不允许静默 skip。索引落在测试侧
`invocation-surface.json`，**刻意不写进 adapter manifest**——manifest schema 是
`additionalProperties:false`，新增字段须 major bump + 存量 adapter 全部补字段并重过
capability-fit（§3），代价远大于收益。

规则：registry 里每个 id 必须在索引中声明 `invocation_surface ∈ {runtime, none}`
且附 `reason`；**未声明即报错**（`assert_invocation_surface_declared`）。新增 adapter
时会被强制回答「它有没有运行时」。

| adapter | invocation_surface | 说明 |
|---|---|---|
| `storybook-local-verify` | `runtime` | 唯一真实运行时（离线确定性） |
| `json-render-core` | `none` | opt-in 投影，无投影引擎 |
| `a2ui` | `none` | 公开协议，非运行时 |

## 4. 保真度护栏（防假绿核心）

L2 的故障是**编出来的**，最大假绿风险是「自说自话」。三条护栏：

1. **形状保真**：`assert_seam_fidelity()` 断言 simulated 成功包络与真实 Storybook
   包络的 `{key: type}` 形状完全一致。形状不对，注入的故障就没有意义。
2. **护栏非真空**：`test_fidelity_guard_is_not_vacuous` 主动抽掉一个 key、改一个
   类型，断言护栏**确实会抛错**。
3. **计数断言**：回退矩阵与 manifest 解析循环都断言 `checked == 期望值`。空集合会
   让门禁零次迭代却返回 PASS——这是最难发现的假绿。

## 5. 诚实账本：不声称已验证的东西

Storybook adapter 是**离线确定性**引擎（engine=deterministic），本仓库**无法真实观测**
`network_loss` 与 `remote_failure`。这两类是 seam 契约定义，**不是真实运行时证据**。

代码里写死：`REAL_RUNTIME_BACKED = {ok, failure}`，`SEAM_CONTRACT_ONLY =
{network_loss, remote_failure}`，并由 `test_network_and_remote_are_seam_contract_only`
断言。任何人不得依据 1-7-5 的测试结果声称「真实断网已验证」。

若将来需要真实证据，路径是：在 Storybook adapter 的 `storybook` engine seam
（已预留，见 `storybook_adapter.py` docstring 的 *reserved seam*）接真实 CLI，
用受控的网络命名空间/代理故障注入跑端到端。那是独立工作项，不在 1-7-5 范围内。

## 6. 1-7-5 落地约束

- 编排层的回退分发**只消费** `AdapterOutcome.outcome_class`，不得窥探 adapter 内部
  或按 adapter_id 分支（除 L3 排除逻辑）。
- 回退执行后必须过 `assert_local_recovery()`：canonical / static-preview /
  local-verify 三项可用 + resolver 为 `success` 或 `degraded`（对应 R1/R2/R3/R5）。
- 回退动作取值限于 §6.2 的五种；越界即 `ValueError`。
- L3 adapter 的 removal 测试走可重置 registry 夹具
  （`ResettableRegistryFixture`），删除永不污染主 registry。
