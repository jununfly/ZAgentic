# 跨阶段 Skill 设计 (1-6)

## 背景

1 阶段 A↔B skill-pair 工作中, 35 节点 95 决策里有 **3 个 skill 不属于 A↔B 处理** — 它们是"跨阶段"的中性 skill, 是**任何 skill-pair 工作流本身**都需要的能力:

- **zj-debrief** — 完工后复盘, 把"做了什么 / 学到什么 / 下次怎么做"沉淀到仓
- **zj-steelman** — 方案早期, 帮方案找最强论据, 避免过早被否
- **zj-dry-run** — commit 前预演, 模拟执行 N 步, 标卡点/歧义/依赖

这 3 个 skill 是 A↔B 工作流本身所需的元能力, 不是 A 也不是 B 独有. 1-6 父决策把它们归为"跨阶段 skill 抽象", 1-6-1/2/3 实现.

## 互补关系矩阵

3 skill 之间 + 与已有 skill 的互补点:

```
时段轴:  开工前 ─────────── 开工中 ─────────── 完工后
              │                  │                  │
zj-steelman   ◆ (帮方案找强点)                    │
zj-grilling   ◆ (找方案弱点)                      │
zj-dry-run       ◆ (commit 前预演, 找卡点)        │
zj-debrief                                ◆ (复盘沉淀)
zj-handoff                       ◆ (会话交接)
zj-triage                                     ◆ (PR 评估)
zj-tdd                            ◆ (TDD 节奏)
```

## 3 skill 之间的关系

| skill | 路由失败到 | 路由成功到 |
|---|---|---|
| zj-steelman | zj-grilling (方案站不住) | 继续推进 (方案有底气) |
| zj-dry-run | zj-to-spec / zj-to-tickets (spec 错) + zj-grilling (决策瓶颈) | 继续 implement (plan 可执行) |
| zj-debrief | — (retro + Retros 段 + 调 zj-domain-modeling) | (闭环, 下一个 task) |

**关键差异**:

- zj-steelman 与 zj-grilling 方向互补 (辩护 vs 攻击), 混在一起 agent 角色冲突 — 独立
- zj-dry-run 与 zj-tdd 不冲突 (宏观预演 vs 微观节奏), 但都属于"commit 前" — 时段错开
- zj-debrief 与 zj-handoff 区别: handoff 是"forward transfer" (现状传给下个 agent), debrief 是"knowledge sink" (沉淀到 ZJ-CONTEXT)

## 元规则: 何时加新跨阶段 skill

1-6 父 Q3 决策 (见 ADR 0002 决策 3): 候选落地必须满足"对应 A 或 B 已有 skill 的互补关系". 用此规则判断是否立 skill:

```
候选 skill X
    ↓
X 互补哪个 A 或 B 已有 skill?
    ↓
明确互补点 (时段/方向/维度)?
    ├── 是 → 立 skill
    └── 否 → 不立, 理由: 与已有 skill 重复
```

3 个新 skill 的判定:

- zj-debrief: 互补 zj-grilling (前/后时段) ✓ 立
- zj-steelman: 互补 zj-grilling (方向) ✓ 立
- zj-dry-run: 互补 zj-triage + zj-to-spec + zj-to-tickets (时段) ✓ 立

## 与 A↔B skill-pair 流程的整合

A 仓 1 阶段工作流 (skill-pair 合并) 是**典型跨阶段场景**:

```
1. /zj-wayfinder → 规划阶段
2. /zj-grill-with-docs → 决策阶段
3. /zj-steelman → (新) 决策后帮方案找强点, 避免 grilling 过激
4. /zj-merge-skill-pair → 执行阶段
5. /zj-dry-run → (新) 合并前预演, 检查 skill-pair 边界
6. /zj-implement → 落地
7. /zj-debrief → (新) 完工后复盘, 沉淀 A↔B 处理动作进 ZJ-CONTEXT
```

**当前 (1 阶段闭环后)**: 3/5/7 三个 skill 已实现, 1 阶段工作流能直接用.

## 写给未来

- 加新跨阶段 skill 时, 用"互补关系矩阵"判断时段/方向/维度是否已被覆盖
- 不立与已有 skill 完全重叠的 (例"在 zj-grilling 里加个 flag 也能做 steelman 的事"——但混在一起角色冲突, 不立)
- 3 个 skill 的 SKILL.md 都有 user-only + 双平台 sidecar, 1-6 父决策统一风格
