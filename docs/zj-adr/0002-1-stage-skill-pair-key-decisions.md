# 1 阶段 A↔B skill-pair 处理: 4 个可重用决策

1 阶段 (35 节点 95 决策) 已闭环. 决策全量记录在 git 历史 + 已删除的 `docs/plans/roadmap-skillpairs.json` 中. 本 ADR 抽出 **4 个有未来可重用价值** 的元决策 — 当未来再遇到"A 仓要跟其他 skill 仓对齐"或"要加新 skill"时, 这些决策点可作为判断依据.

抽出标准: 该决策 (1) 决定未来工作方向, (2) 看似自明但实际是判断选择, (3) 未来读者会问"为什么这样".

## 决策 1 — 处理动作统一为 5 英文动词 + A-only

**1-3 父 Q4=D 决策** (roadmap 1-3 节点)。

A 仓处理每个 skill-pair 时, 用统一英文动词声明动作:

| 动词 | 含义 |
|---|---|
| `absorb` | 吸收 B 优点进 A 已有 skill (A 优先, B 是输入) |
| `adopt` | 整体采纳 B 替换 A 已有 skill (B 优先, A 是输入) |
| `replace` | 删除 A skill, 采纳 B 等价 skill |
| `reject` | A 与 B 不同, A 保留独立性, 不合并 |
| `strict-align` | A 已有 skill 与 B 几乎逐字对应, 严格对齐 B 原文 |
| `A-only` | A 仓环境私有化规则, 不属于 A↔B 处理, 但在 skill-pair 合并中需要补的 (例 1-3-3-1 PR 3 rule) |

**为什么统一**: 中文动作 (吸收/采纳/替换/拒绝) 在 commit msg + 文档 + review 注释里反复出现, 不统一会被误读; 英文动词简短、可 grep、可作 CLI flag.

## 决策 2 — A-only PR 标志 3 rule (1-3-3-1)

**1-3-3-1 决策** (用户选 1+5+7 三项)。

A 仓任何 skill 改动 PR 必查 3 项:

- **Rule 1**: `skills/` 改动必查 `.codex-plugin/plugin.json` 挂接 (新 skill 必须挂上, 否则不被 Claude/Codex 平台发现)
- **Rule 2**: git 操作必走 `./scripts/zj-git` 包装 (WorkBuddy shim 在 Windows Git Bash 上把 `rm -rf` 真删, 见 `skills/engineering/zj-git-bypass-safe-delete/`)
- **Rule 3**: 新术语必先更新 `ZJ-CONTEXT.md` 才合并 (术语是仓的共享语言, 改了 skill 但没改词汇表, 下游 skill 会"猜"或"编")

**为什么是 3 项**: A 仓"自给自足"需要 3 个 hook 守住 — 平台发现 (Rule 1), 工具安全 (Rule 2), 词汇一致 (Rule 3). 漏一项都会让仓变"分叉" (skill 与词汇表不同步 / skill 与 plugin 列表不同步).

落地形式: 写在每个 skill 的 PR review checklist + 仓根 `AGENTS.md` (如未写需补).

## 决策 3 — 跨阶段 skill 抽象的元规则 (1-6 Q3)

**1-6 父 Q3 决策** (A. 候选落地必须有对应 A 或 B 已有 skill 的互补关系).

加新 skill 之前必须回答:

- **互补对象**: 该 skill 拟互补 A 或 B 哪个已有 skill?
- **互补点**: 时段互补 (前/中/后)? 方向互补 (辩护/攻击)? 维度互补 (微/宏)?
- **无明确互补点 = 不立 skill** — 避免重复建设.

判定方式: 列出该 skill 拟互补的现有 skill + 写明互补点, 写进候选节点的 decision 数组. 例 1-6:
- zj-debrief ↔ zj-grilling (时段: 前/后)
- zj-steelman ↔ zj-grilling (方向: 辩护/攻击)
- zj-dry-run ↔ zj-triage + zj-to-spec + zj-to-tickets (时段: 中/前+中后)

**为什么是元规则**: 加 skill 的诱惑总是"看起来有用", 元规则强制加 skill 前先回答"互补什么已有 skill" — 这把"加 skill"从"品味决策"变成"关系网络判断", 更可衡量.

## 决策 4 — Grilling 节奏: 只问需用户拍板的问题 (1 问)

**1-6 阶段用户指示确立** (`docs/plans/handoff-2026-08-14.md` 101-107 行).

grilling 阶段 (写 SKILL.md 之前) 严格区分两类问题:

- **需用户拍板的问题** (例: 文件归置, 桶归属, 与 grilling 关系) — 必须 grill, 一次多问, 每问给推荐答案
- **复用原文的维度** (例: 触发时机, 核心动作, 触发频率) — 直接引用已有 skill 或 A↔B 原文, 不 grill

**为什么不是全 grill**: 全 grill 会让"何时停"模糊 — 用户每次都被卷进细节, 失去 grilling 的判断价值 (grill 是"关键岔路"而非"全遍历"). 1 阶段经验: 95 决策中真正"必须问"的不到 30 个.

实施: `/zj-grilling` 输出"Q1 决定文件归置, Q2-Q5 复用原文"格式, 让用户一眼看到 grill 边界.

## 写给未来

- 这 4 条不是"唯一正确答案", 是"1 阶段用过且验证有效". 2 阶段可重 grill.
- 这 4 条不写进 ZJ-CONTEXT (那是个 vocabulary, 不存过程), 写在这里 (设计决策 = ADR 职责).
- 这 4 条 + `AGENTS.md` (A 仓硬约定) + `ZJ-CONTEXT.md` (词汇) = 1 阶段沉淀的"最小可重建集". 任何下游仓复用 A 仓 skills 时, 这 4 条 + AGENTS + ZJ-CONTEXT 是"上下文包".
