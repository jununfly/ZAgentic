# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

为 zj-discuss 引入「角色 = 带闸门的过程」能力：评估是否从 gstack 借用其角色范式（forced-workflow + gate + status），而不是继续维护 thin prompt 角色。

- **R1** [关键] 角色能定义强制工作流 + 机械闸门 (forced workflow + gate) — 验收: 每个视角角色都有可执行 method + 闸门，闸门不过拒绝结论
- **R2** [关键] 跨 provider 独立评审能力 — 验收: 能在不同 model/provider 独立会话跑独立评审
- **R3** [want] learnings 经验持久化回路 — 验收: 评审/失败经验可落库并被后续复用
- **R4** [nice] 引导式安装 / Quick start — 验收: 新用户可快速启用

## 候选 O1 · gstack (garrytan/gstack) (v1.2.0)

- **推荐分类**: `B`
- 关键需求覆盖率: 50% · 平均有效拟合度: 0.85 · 总所有权成本 E: 18

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | gstack /review,/qa,/ship 等强制工作流范式 (演示用，非正式取证) |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | gstack /codex 跨 provider 外部评审 (演示用) |
| R3 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | gstack learnings 持久化机制 (演示用) |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | gstack setup 引导式安装 (演示用) |

### 依据
- 关键需求存在部分缺口但 E=18<=E_MID -> B

## 候选 O2 · 某一体化 agent 运行时(自研基座) (v0.9.0)

- **推荐分类**: `C`
- 关键需求覆盖率: 50% · 平均有效拟合度: 0.95 · 总所有权成本 E: 135

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.9 | 1.0 | 0.9 | 0.81 | 运行时内置角色执行器 (演示用) |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | 运行时原生多 agent (演示用) |
| R3 | native | 1.0 | 1.0 | 1.0 | 1.00 | 运行时内置 memory (演示用) |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | 自带 onboarding (演示用) |

### 依据
- 适配层触碰主体能力(禁止类目): storage-sync-infra(存储和同步基础设施), full-retrieval-memory(完整检索或记忆流水线) -> 至少降为 C
- 主体能力建设但责任可控 -> C

## 最终拍板 (Human/Agent 填)

- 选定组合 C 与能力缺口 G: ___
- 自有责任 E 及成本估计: ___
- PoC 结论: ___
- 最终分类 (A/B1/B2/B3/C/D): ___
- 采用理由: ___
- 主要风险: ___
- 退出路径: ___
- 重新评估触发条件: ___

**完成标准自检**: 第三方 Agent 仅凭本记录能否复核分类依据，并区分证据 vs 假设？