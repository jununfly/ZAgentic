# quarantine 术语消歧（AdapterBoundary）

> 路线图节点 `1-7-5`（adapter 删除 / 断网 / 远程故障恢复）的术语风险项。
> 本文件是 **单一事实源**，澄清两个拼写相近但**完全不同**的概念，防止边界编排层（1-7-5）与评审者把二者混为一谈。

## 0. 一句话结论

| 维度 | A. spec `quarantine`（adapter 级） | B. `QUARANTINED`（receipt 级） |
|---|---|---|
| 层级 | **adapter / registry**（工具是否被允许调用） | **run / receipt**（这一次验证证据是否可信） |
| 载体 | adapter manifest 的 `lifecycle` 字段（枚举值） | `result.status` / gate `status` / skill `stop_conditions.next`（状态常量） |
| 触发 | capability-fit 失败、安全闸门失败 | 证据无法归因（fingerprint 缺失 / `bundle.quarantine[]` 非空） |
| 语义 | **管理隔离**：这个 adapter 整工具被停用，永不调用，待修复或移除 | **认知隔离**：这一次运行的结果被判不可信，不产出成功结论 |
| 持久性 | **持久**（声明式字段，落 manifest） | **瞬态**（每次运行独立判定，不写回 adapter） |
| 归属模块 | boundary 编排层（1-7-5） | `ui_skill_core` / `hard_gates` / verify 阶段 |
| 取值拼写 | 小写 `"quarantine"` | 大写带 D 的 `"QUARANTINED"` |

**二者只共享"set aside / 不要用"的直觉，机制、层级、触发、持久性全部不同。**

## 1. A — spec `quarantine`（adapter 生命周期状态）

来源：`adapter-boundary-v1.md` §6.1 四态生命周期 + `skills/ui/zj-ui-core/contracts/adapter-manifest.schema.json` 的
`lifecycle` 枚举 `["active","degraded","disabled","quarantine"]`。

- 含义：adapter 被**隔离**——安全闸门 / capability-fit 失败；**永不调用**，待修复或移除。
- 是 adapter manifest 的**声明式字段**，写进 registry；边界编排层（1-7-5）通过
  `set_lifecycle(adapter_id, "quarantine")` 来转移它（见
  `tests/ui_agent_skills_registry_fixture.py` 的 `VALID_LIFECYCLE`）。
- 是**管理动作**：针对"工具本身"的长生命周期状态。
- 与 `removal` 的关系：`removal` 是比 `quarantine` 更彻底的瞬态动作（adapter 从 registry
  消失，无 `removed` 状态位）；`quarantine` 是保留 entry 的停用态。二者都属于 adapter 级。

## 2. B — `QUARANTINED`（receipt / 验证结果状态）

来源：`ui_skill_core.py` 常量 `QUARANTINED = "QUARANTINED"`，位列
`STATUS_PRIORITY` 与 `result()` 信封；`hard_gates.py` 的
`STATUS_PRECEDENCE = ["FAIL","HUMAN_REVIEW_REQUIRED","QUARANTINED","WARNING","PASS"]`；
以及 `ui_registry.py` 中各 skill 的 `stop_conditions[].next`（如 direction /
design_system / visual_review 在 license unknown / fingerprint 缺失时 → `QUARANTINED`）。

- 含义：这一**次验证运行**的证据无法归因 / 来源不可信 → 该 receipt 被判 `QUARANTINED`，
  **绝不**产出成功结论，但也不等同于 hard `FAIL`（没断言某条失败，只是不信任）。
- 触发链（三件套，注意这是 B 内部的子概念）：
  1. `observation bundle.quarantine[]` 非空（adapter 标记某证据无法归因到具体
     fixture/维度）→
  2. `hard_gates._finish` 在该 gate `status != FAIL` 时把结果升为 `QUARANTINED` →
  3. 聚合进 verification receipt 的状态。
  同样地，`storybook_adapter.run` 在 `fingerprint` 缺失 / 不可归因时直接返回
  `status = core.QUARANTINED`（adapter **运行**被隔离，不是 adapter 本身）。
- 是**瞬态、每次运行独立**的判定；它**绝不**写回 adapter 的 `lifecycle`。

## 3. 为什么必须分清（1-7-5 的踩坑点）

1-7-5 的边界编排层会同时接触两个世界：它操作 registry（可能把某个 adapter 的
`lifecycle` 置为 `quarantine`），也消费 / 生成 verification receipt（可能看到
`QUARANTINED` 状态）。若把它们当成同一机制，会出现两类错误：

- **误把 receipt 的 `QUARANTINED` 当成 adapter 被隔离**：一次运行证据不可信
  （如该次 fingerprint 缺失），**不代表**这个 adapter 工具该被停用。admin 隔离是重决定，
  不能由单次验证结果自动触发。
- **误把 adapter `lifecycle=quarantine` 当成 receipt 状态**：被隔离的 adapter 根本不会被
  调用，因此**不会产生任何 receipt**；而处于 `active` 的 adapter 仍可能在某次运行产出
  `QUARANTINED` receipt（证据归因失败）。两者正交。

**1-7-5 约束**：
- registry 的 `lifecycle` 只允许 schema 枚举四值（`active/degraded/disabled/quarantine`），
  其中 `"quarantine"` 与 receipt 常量 `"QUARANTINED"` 拼写都不同，不能在代码里互换。
- 任何把 receipt `QUARANTINED` 自动升级为 adapter `lifecycle=quarantine` 的逻辑都须经
  显式人工 / owner 决策，不得隐式发生。
- 机器级防止混淆见 `tests/test_quarantine_disambiguation.py`（断言两 token 不同、
  schema 枚举不含 `"QUARANTINED"`、active adapter 仍可产出 QUARANTINED receipt、
  registry 置 quarantine 不影响 receipt 常量）。

## 4. 命名建议（非强制，供评审统一话术）

- 口述时用全称区分：**"adapter 隔离（quarantine 生命周期）"** vs
  **"receipt 隔离（QUARANTINED 验证状态）"**。
- 代码注释里提到本概念时，显式标注层级（adapter-lifecycle vs receipt-status），
  避免只用"quarantine"一个词。
