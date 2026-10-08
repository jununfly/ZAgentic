# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

逐个判断 pstack-claude 58 个 skill 是否能作为 ZAgentic 的可复利、可治理能力单元吸收，并把宿主耦合与重复 owner 排除在直接 merge 之外。

- **R1** [关键] 能力可拆成一个可安装、可发现、可独立验收的 ZAgentic skill 单元 — 验收: 无需引入 pstack plugin runtime 即可被本仓库发现并运行
- **R2** [关键] 方法语义服务于科学、可复核、可复利的工具组合与能力组合 — 验收: 输出能进入本仓库既有 evidence/roadmap/docs 治理链
- **R3** [关键] 宿主工具、模型、路径、并发和任务状态契约可映射到 ZAgentic — 验收: 替换 Claude/Pi/Copilot 专属调用后仍保持同一用户可观察语义
- **R4** [want] references/scripts 等附属资产可在不复制整套 runtime 的情况下携带 — 验收: 依赖、脚本和生成物有明确白名单与运行方式
- **R5** [关键] 许可证、版权、NOTICE 与上游 provenance 可随 merge 保留 — 验收: 第三方可追溯来源并满足 MIT 与 Cursor team kit 通知义务
- **R6** [want] 维护、验证、升级与退出成本保持在可控薄层范围 — 验收: 有 owner、PoC、rollback/removal test 和重新评估触发条件
- **R7** [关键] 不与 ZAgentic 的 Human authority、安全规则、Git/documentation governance 冲突 — 验收: 不可逆操作、证据来源、工作区和文档生命周期仍由 ZAgentic 规则决定

## 候选 architect · architect (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/architect/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 arena · arena (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/arena/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 automate-me · automate-me (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/automate-me/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 babysit · babysit (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/babysit/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 benchmark-checklist · benchmark-checklist (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/benchmark-checklist/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 blast-radius · blast-radius (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/blast-radius/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 bro · bro (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/bro/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 correct · correct (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/correct/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 create-verification-skill · create-verification-skill (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/create-verification-skill/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 deslop · deslop (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/deslop/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 figure-it-out · figure-it-out (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/figure-it-out/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 fix-ci · fix-ci (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-ci/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 fix-merge-conflicts · fix-merge-conflicts (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/fix-merge-conflicts/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 get-pr-comments · get-pr-comments (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/get-pr-comments/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 how · how (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/how/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 interrogate · interrogate (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/interrogate/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 maintain-verification-skill · maintain-verification-skill (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/maintain-verification-skill/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 make-pr-easy-to-review · make-pr-easy-to-review (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/make-pr-easy-to-review/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 no-comments · no-comments (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/no-comments/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 poteto-help · poteto-help (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-help/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 poteto-mode · poteto-mode (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/poteto-mode/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 principle-attack-the-premise · principle-attack-the-premise (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-attack-the-premise/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-boundary-discipline · principle-boundary-discipline (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-boundary-discipline/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-build-the-lever · principle-build-the-lever (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-build-the-lever/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-encode-lessons-in-structure · principle-encode-lessons-in-structure (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-encode-lessons-in-structure/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-exhaust-the-design-space · principle-exhaust-the-design-space (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-exhaust-the-design-space/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-experience-first · principle-experience-first (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-experience-first/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-explain-the-number · principle-explain-the-number (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-explain-the-number/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-fix-root-causes · principle-fix-root-causes (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-fix-root-causes/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-foundational-thinking · principle-foundational-thinking (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-foundational-thinking/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-guard-the-context-window · principle-guard-the-context-window (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-guard-the-context-window/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-laziness-protocol · principle-laziness-protocol (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-laziness-protocol/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-make-operations-idempotent · principle-make-operations-idempotent (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-make-operations-idempotent/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-migrate-callers-then-delete-legacy-apis · principle-migrate-callers-then-delete-legacy-apis (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-minimize-reader-load · principle-minimize-reader-load (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-minimize-reader-load/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-model-the-domain · principle-model-the-domain (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-model-the-domain/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-never-block-on-the-human · principle-never-block-on-the-human (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 principle-outcome-oriented-execution · principle-outcome-oriented-execution (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-outcome-oriented-execution/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-prove-it-works · principle-prove-it-works (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-prove-it-works/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-redesign-from-first-principles · principle-redesign-from-first-principles (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-redesign-from-first-principles/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-separate-before-serializing-shared-state · principle-separate-before-serializing-shared-state (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-sequence-verifiable-units · principle-sequence-verifiable-units (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-subtract-before-you-add · principle-subtract-before-you-add (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-subtract-before-you-add/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 principle-test-behavior-not-implementation · principle-test-behavior-not-implementation (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-test-behavior-not-implementation/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 principle-type-system-discipline · principle-type-system-discipline (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/principle-type-system-discipline/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 recall · recall (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/recall/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 reflect · reflect (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/reflect/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 setup-pstack · setup-pstack (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/setup-pstack/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 show-me-your-work · show-me-your-work (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/show-me-your-work/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 swarm · swarm (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `D`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.71 · 总所有权成本 E: 175

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R3 | unsupported | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |
| R7 | unknown | 0.0 | 0.0 | 0.0 | 0.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/swarm/SKILL.md |

### 依据
- 关键需求 R3 状态=unsupported -> 继续搜索(D)
- 关键需求 R7 状态=unknown -> 继续搜索(D)

## 候选 tdd · tdd (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/tdd/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 teach · teach (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/teach/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 technical-writing · technical-writing (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/technical-writing/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 thermo-nuclear-code-quality-review · thermo-nuclear-code-quality-review (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/thermo-nuclear-code-quality-review/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 typescript-best-practices · typescript-best-practices (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/typescript-best-practices/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 候选 unslop · unslop (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/unslop/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 what-did-i-get-done · what-did-i-get-done (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `B1`
- 关键需求覆盖率: 100% · 平均有效拟合度: 0.93 · 总所有权成本 E: 30

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R2 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R3 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R4 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R6 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |
| R7 | native | 1.0 | 1.0 | 1.0 | 1.00 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/what-did-i-get-done/SKILL.md |

### 依据
- 外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1

## 候选 why · why (3b0bc62e13f507c426997ba472e3430dd3e4ef05)

- **推荐分类**: `C`
- 关键需求覆盖率: 60% · 平均有效拟合度: 0.75 · 总所有权成本 E: 96

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R2 | adapted | 0.8 | 0.8 | 0.8 | 0.51 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R3 | adapted | 0.9 | 0.95 | 0.95 | 0.81 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R4 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R5 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R6 | adapted | 0.5 | 0.8 | 0.8 | 0.32 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |
| R7 | adapted | 1.0 | 0.95 | 0.95 | 0.90 | https://github.com/michael-denyer/pstack-claude/blob/3b0bc62e13f507c426997ba472e3430dd3e4ef05/plugins/pstack/skills/why/SKILL.md |

### 依据
- 关键需求缺口且 E=96>E_MID -> C

## 最终拍板 (Human/Agent 填)

- 选定组合 C 与能力缺口 G: 采用 `O-principles`、`O-writing`、`O-verification` 与 `O-research` 中经去重后的窄能力；保留 ZAgentic 的 skill discovery、evidence、roadmap、docs governance 和 Human authority 为 C 的原生责任。关键缺口 G 是 Claude/Pi/Copilot runtime glue、pstack 全局 router、模型 sheet、transcript 读取、PR shipping/watch-pr 与第二套自治政策。
- 自有责任 E 及成本估计: B1 单元按 E=30 的相对成本档执行；C 单元按 E=96 的相对成本档执行；D 单元不进入实现，避免承担 E=175 的 runtime/治理责任。所有成本是同一模型下的比较单位，不是工时承诺。
- PoC 结论: 先为 B1 候选做 trigger/discovery smoke test、一个代表性工作流、license/provenance 检查和 removal test；为 C 候选先做语义 delta 与现有 owner 对照，再决定吸收规则还是原生重写；D 候选必须先证明 host-neutral adapter 和明确 authority mapping，当前不进入 merge。
- 最终分类 (A/B1/B2/B3/C/D): `B1`（29 个可移植窄单元），`C`（20 个需要原生去重或承担较高 owner 成本的单元），`D`（9 个宿主/政策强耦合单元）；没有任何单元达到 A。
- 采用理由: pstack 的主要可复利价值在于“调查→设计→并行候选→对抗评审→验证→复盘”的组合协议和小型原则，而不是其 Claude/Pi runtime。逐 skill 矩阵显示 29 个单元可通过薄适配进入，20 个与 ZAgentic 现有 owner 重叠或需要较高维护责任，9 个关键宿主契约不满足。
- 主要风险: 触发器冲突与重复 owner；`poteto-mode` 将全局路由、回复格式和自治策略带入本仓库；PR skills 可能执行 `gh`、push、merge 或 queue；references/scripts 的平台假设被误当作 native；Cursor 与 cursor-team-kit 的 NOTICE/provenance 丢失；未运行真实多宿主 smoke test。
- 退出路径: 每个 B1/C 单元必须有可删除的目录或规则片段、保留原生 ZAgentic 路径的 conformance fixture，以及 removal test；任何单元若需要复制 pstack runtime、第二 authority、不可逆写操作或长期 fork，则回退到 D/仅参考资料。
- 重新评估触发条件: pstack commit 或 NOTICE/license 变化；ZAgentic 同名 skill 的 owner/语义变化；Codex skill discovery 或协作 API 变化；PoC 出现 trigger 漂移、evidence 不闭合、authority bypass、版本错配或 removal failure；需要引入 `watch-pr`、hooks、Pi extension 或模型 sheet 时另开技术决策。

**完成标准自检**: 是。固定 commit、58 个候选、7 项需求、R×O 矩阵、成本分档、适配边界、机械闸门输出和最终分类均已落盘；上游事实由固定 URL 支撑，merge 分类与成本是明确标注的拟合判断和待执行 PoC，不冒充运行时实测。
