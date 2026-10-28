---
doc-kind: adr
authority: zj-composer
status: accepted
issue: "224"
---

# 文档质量契约落在治理层而非运行时；被拒默认值显式记录

## Context

`zj-docs-ontology` 的治理契约（governance-contract）原先只覆盖"地图正确性"——
`MAP_*` 机械检查（每个 `authority-id` 绑定唯一页面、绑定检测器不被散文链接带偏等）。
它完全不管"页面质量"与"文档健康度"：一篇被权威绑定的页面，内容可以是空的、过时的、
或把相邻 kind 的东西都吸收进来。

四源 `docs/`（chromium / deepseek-harness / semantica / openai-codex）的蒸馏
（Plan `docs-best-practices-distill-2026-10-28`，PR #224，merge `dc749a0`）识别出
一组可移植的最佳实践：one-home 归属不变量、kind→必写章节骨架、slop 审计清单、
freshness 边界、retirement 生命周期、以及"绿灯≠正确"的哲学。问题变成：这些条款
**落在哪一层**。

三个约束塑造了决策：

1. 本 skill 是**可安装到任意仓库**的便携式技能，运行时校验器 `docs_governance.py`
   属于 portability boundary——新增任何诊断码都会改变目标仓的门禁面，必须单独立项。
2. 本 skill 运行在它**不拥有**的仓库里，不可逆动作的默认值不能交给机器。
3. 拒绝一个主张不等于沉默它；否则下一轮 governance pass 会重新辩论、重新踩坑。

## Decision

1. **文档质量契约落在治理层，不落运行时。**
   蒸馏出的条款一律写成**契约文本（`references/*.md`）+ 审计清单 + 契约守卫测试**，
   **不新增诊断码、不改 `docs_governance.py`**。
   - `skills/codebase-docs/zj-docs-ontology/references/kind-templates.md`：17 个 `doc-kind`
     × 6 列（Job / Does NOT belong there / Must-write sections / Page form / Focused
     check）——把"装什么"的反边界写成一等公民，因为只说"持有什么"的 kind 会慢慢吸收旁边的东西。
   - `skills/codebase-docs/zj-docs-ontology/references/doc-slop-checklist.md`：9 类腐化的
     Detect/Fix/Scope。**审计清单不是门禁**——它加零诊断码、改零退出码、不被 `--validate`
     运行；命中是提案项，不是静默重写。
   - `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md` 扩展出 8 节
     （One home per fact / Page form / Page content contract / Evidence: run the facts /
     Generated regions / Retirement / What a green run does not mean / Rejected defaults）。
   - `skills/codebase-docs/zj-docs-ontology/tests/test_doc_quality_contract.py`（18 项）：
     契约守卫，验证模板覆盖、slop 类定义、以及 C-11 反回归——**独立于运行时校验器**，
     不污染 `MAP_*` 退出码。

2. **删除默认值保持 `preserve meaning by default`。**
   chromium 的"默认删死文档"**拒绝采纳**；其意图（少量新鲜准确的文档胜过大量破败文档）
   以 bonsai 修剪的形式**采纳**为生命周期规则，但手段（默认删）拒绝。理由见约束 2：
   把不可逆动作的默认值交给机器，在本 skill 的运行环境里不可接受。

3. **被拒主张写入 `## Rejected defaults` 并由测试反回归锁定。**
   拒绝 ≠ 沉默：判决与理由留在契约里，并断言"该节之前不得出现删除默认值表述"。
   `## Rejected defaults` 现记录三条（见 Consequences），每条自带理由，使后续
   governance pass 不必重新辩论。

## Consequences

- 质量条款现在可被机器守卫（契约测试），但**不扩大 portability boundary**：
  目标仓的 `docs_governance.py --validate` 退出码与诊断码集合在 PR #224 前后**完全一致**。
- `## Rejected defaults` 落地三条，每条带"为何拒绝"：
  - **Delete-dead-docs-by-default**（源自 chromium）：拒绝。意图以 bonsai 采纳，手段不采纳。
  - **A mechanical health-score gate**（页面尺寸预算、freshness 评分、孤儿评分）：暂拒。
    目标仓无 manifest、无统一 source-map 时间戳，分数将是凭空捏造——作为能力缺口保留，
    而非建在缺失的事实源上（即 E16 / 能力缺口二）。
  - **Banning metaphorical vocabulary**（gate / vocabulary / surface）：拒绝。这些词在
    本仓是承重词，改名会破坏每个引用它们的契约。
- 反回归已就位：契约测试断言"Rejected defaults 节不得出现删除默认值表述"，翻转该默认值
  即红灯。
- 实施落点：feature `77bc2e3` → PR #224 → merge `dc749a0`（5 files, +526 / −5）。
  `skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py` 本次零改动。
- `zj-neat-freak`（漂移对账）与 `zj-debrief`（复盘）仍负责过程层，本 ADR 不改其职责边界。
- 未决：9 个新术语尚未进 `docs/ontology/ONTOLOGY.md` 词汇表（本次 scope 不含 `docs/` 本体）；
  E16 健康度计量与另两个 required-skill 缺口（跨仓文档规范蒸馏器 / 文档退役与重定向策略器）
  单开一轮。
