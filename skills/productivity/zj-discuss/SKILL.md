---
name: zj-discuss
description: Decompose a complex problem that flat chat cannot fully resolve into a master doc + independent sub-documents (one issue, one doc); run multi-agent independent discussion per sub-problem, synthesize, and hand off to zj-docs-ontology for durable deposition. Solves the pain of thin chat failing to surface every facet of a hard problem.
argument-hint: "<complex problem description, or an existing discussions/<slug>/ path to resume>"
---

# zj-discuss

A **methodology**, not a single-turn chat. It turns a genuinely complex problem —
one that flat prompt-and-answer chat cannot resolve in full — into a **document
set** that becomes the complete solution. The set is preserved as in-progress
authority during solving, then disposed of via `zj-docs-ontology` after the
problem is solved.

## Mental model

```
complex problem
  └─ decompose (Human + lead AI, one issue at a time)
       ├─ one MASTER.md  : core problem + solution approach + doc index
       └─ N sub-documents: each = one independent sub-problem + its solution
            └─ each sub-doc resolved by independent multi-agent discussion
document set = complete solution (phase 1)
  └─ after solving → zj-docs-ontology deposits durable parts, then folder deleted (phase 2)
```

`zj-discuss` is the **lifecycle owner** of this set. Per-sub-document
independent discussion is handled by its companion `zj-discuss-view`
(parameterized by role), which is loaded in a *separate* Agent session.

> 角色定义以 `references/role-matrix.md` 为**唯一真源**——本文件只引用、不复述，避免
> 概念与其描述耦合漂移（SSOT 不变式）。凡涉及角色语义，一律指过去看 role-matrix。

## Two-phase lifecycle (critical — read before using)

- **Phase 1 — solving:** the folder `discussions/<slug>/` is retained as the
  problem's **process-authority basis before resolution** plus the in-progress
  complete solution. It is **NOT** a long-term document.
- **Phase 2 — after resolution:** invoke `zj-docs-ontology` to classify the
  set — durable content (decisions, constraints, conclusions) deposits into the
  project's long-term `docs/` authority pages; pure process noise becomes a
  deletion candidate. Only after **Human confirmation** is the folder deleted.

This resolves the tension between "keep the complete solution" (phase 1) and
"delete transient material" (policy's disposition discipline, phase 2).

## Workflow

### Phase 0 — Scope gate

Confirm this is a problem flat chat cannot handle. If it is a *single* issue,
use `zj-discuss-view` + `zj-steelman` directly; do not spin up the full set.

### Phase 1 — Decompose (Q-A, hybrid)

1. Dispatch a **SubAgent** (low-isolation is acceptable here) to draft a
   candidate decomposition: a master outline + a list of sub-documents. Each
   candidate sub-document has: one-line problem statement, independence
   rationale, success criteria, and suggested roles from `role-matrix.md`.
2. **Human + lead AI review and finalize** the decomposition. Lock it.
3. Create the folder `discussions/<self-explain-slug>/` — kebab-case,
   self-explanatory, **no** `discuss-` prefix (the parent dir already says it).
   Default base dir is the repo root; configurable.
4. Generate `MASTER.md` from `references/master-template.md` and each
   sub-document stub from `references/subdoc-template.md`.

### Phase 2 — Per-sub-document independent discussion (Q-C + Q-E)

For each sub-document:

1. `zj-discuss` 为每子文档的**独立视角（默认集 B/C/A，可按子问题增删）**各生成一份
   briefing（主力AI 为整合者，在主会话直接写整合立场，不走 briefing）。每份 briefing
   盖章角色立场 + **强制「Read `<sub-doc-path>` 原文」令**，落点约定
   `<讨论文件夹>/briefings/<sub-slug>-briefing-<role>.md`。**子文档不在磁盘则拒生成 briefing。**
2. Human copies each briefing into a **separate cross-session independent
   Agent**, loads `zj-discuss-view --role X <sub-doc-path>`; that Agent writes
   its independent viewpoint into `## Agent viewpoints`.
3. Every viewpoint header marks
   `视角来源: 跨会话独立Agent` or `同会话SubAgent(低权重)`.
4. The `## Human 拍板` table records each round; Human may challenge on
   evidence; technical deviations are **never** silently swallowed.
5. **跨会话启动包（默认输出，非可选开关）：** 在 Phase 2 产出末尾，追加一段可一键
   粘贴的文本——每个必需角色一行 `zj-discuss-view --role X <sub-doc-path>`（X ∈ 本次必需集），
   外加 sub-doc 路径与角色名。模板**只生成跨会话调用**，禁止任何「同会话内即可完成隔离」
   的捷径字样（见硬规则 3 承重警告）。这把「Human 手抄 briefing 易漏行/错路径」的出错率压到近零。
6. **Convergence:** once the **declared required set** (default B(执行)/C(产品·市场)/A(架构))
   is covered, stop adding roles and synthesize a conclusion. More views is a
   means, not a goal.

### Phase 3 — Synthesize & roll up (Q-D)

- **Incremental:** after each sub-doc's conclusion, update `MASTER.md`'s index
  status and append a sub-solution summary (link + 1–3 line essence +
  cross-cutting constraints).
- **Final:** when all sub-docs are concluded (or Human stops per convergence),
  run one final synthesis — rewrite `MASTER.md`'s "解决思路" as an integrated
  narrative. A SubAgent may draft it (low-risk); Human reviews.

### Phase 4 — Disposition contract (Q2')

`MASTER.md` already carries the fixed `## 本文件夹的性质与处置契约` section.
When the whole problem is resolved, invoke `zj-docs-ontology` to classify the
set and, after Human confirmation, delete the folder.

## Hard rules (Q-E — non-skippable)

1. **Read the original.** Every Agent viewpoint must come from an Agent that
   `Read` the file itself. No human-relayed summaries of A's stance to B. No
   "please refute A" adversarial instructions — assign structurally different
   roles instead.
2. **Structurally different roles.** The independent viewpoints are **B / C / A**
   from `role-matrix.md` — genuinely different structural stances, not the same
   lens relabeled. **主力AI is the integrator** (main session, low weight), not
   one of the isolated viewpoints. Role semantics are defined *only* in
   `role-matrix.md` (SSOT) — this file references it, never re-describes it.
3. **Anti-echo-chamber + load-bearing warning.** Same-session roleplay is *not*
   runtime isolation; mark it `同会话SubAgent(低权重)` and treat its weight
   accordingly. **This warning is load-bearing:** the SubAgent 预演 口子 may stay
   as a low-threshold onboarding entry, but (a) it must always be flagged
   "同会话 / 低权重 / 非隔离 / 不可作为结论依据"; (b) `conclusion` and cross-cutting
   constraints **must never cite SubAgent 预演 output as authority** — only
   cross-session B/C/A are trustworthy. If the 口子 is observed to systematically
   lure Humans into skipping real isolation, delete it.
4. **Convergence.** Cover the **declared required set** (default B(执行)/C(产品·市场)/A(架构)),
   then stop adding perspectives. More views is a means, not a goal.
5. **Conclusion must be executable.** A sub-doc conclusion must include
   deposition instructions (which PRD/ADR to change, which temp doc to delete)
   — otherwise it is not a closed loop.

## References

- `references/master-template.md` — MASTER.md skeleton (incl. disposition contract).
- `references/subdoc-template.md` — per-sub-problem discussion doc skeleton.
- `references/role-matrix.md` — reusable role matrix (编排者 + B/C/A 独立视角) + convergence rule.

## Integration with sibling skills

> 边界原则：**引用而非重做。** discuss 做薄编排层，凡兄弟技能已覆盖的能力一律调用，
> 不在 discuss 内重实现（防逻辑漂移）。

- **`zj-steelman`（辩护）vs `zj-discuss-view`（结构错位）—— 不变式互斥，禁止共享实现。**
  discuss-view 的 role 视角 = **协作式结构错位**（丰富讨论：B 问排期/风险、C 问用户/价值、
  A 问边界/不变式，互补而非对抗）；zj-steelman = **防御式辩护**（检验提案可辩护性，判
  Strong/Adequate/Weak）。前者永不攻击、后者专司辩护。故 **discuss-view 不得内置 defend 逻辑**；
  对「提案是否站得住」类子问题，discuss 改调 `zj-steelman` 取其判定。

- **`zj-handoff`（压缩契约）⊇ `discuss-briefing`（受控切片）。** briefing := handoff 输出契约
  （引用不重复 + suggested-skills + 落 temp 目录）＋ `[role-stance 章]` ＋ `[强制 Read 原文令]`。
  discuss **不重造压缩逻辑**，handoff 契约为其基础子集；仅追加 discuss 专属两行头。

- **`zj-docs-ontology`（Human-owned 治理）— discuss 阶段 2 只吐指针，绝不自行分类/迁移。**
  discuss 阶段 2 仅产出 `<conclusion>` + `<suggested-category>` + `<pointer>`，随即移交
  `zj-docs-ontology`；**分类、提案迁移、链接/权威校验一律由 docs-ontology 在其 Human 确认闭环内
  完成。discuss 不得运行 docs_governance.py，不得决定最终分类。**

- `zj-grilling` — use beforehand to sharpen the core problem framing.
