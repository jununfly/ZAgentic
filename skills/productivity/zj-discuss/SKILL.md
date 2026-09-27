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

1. `zj-discuss` 为每子文档的**独立视角（B/C/A）**各生成一份 briefing（主力AI 为
   整合者，在主会话直接写整合立场，不走 briefing）。每份 briefing 盖章角色立场 +
   **强制「Read `<sub-doc-path>` 原文」令**，落点约定
   `<讨论文件夹>/briefings/<sub-slug>-briefing-<role>.md`。**子文档不在磁盘则拒生成 briefing。**
2. Human copies each briefing into a **separate cross-session independent
   Agent**, loads `zj-discuss-view --role X <sub-doc-path>`; that Agent writes
   its independent viewpoint into `## Agent viewpoints`.
3. Every viewpoint header marks
   `视角来源: 跨会话独立Agent` or `同会话SubAgent(低权重)`.
4. The `## Human 拍板` table records each round; Human may challenge on
   evidence; technical deviations are **never** silently swallowed.
5. **Convergence:** once 执行 / 产品 / 市场 / 架构 are covered, stop adding
   roles and synthesize a conclusion.

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
   one of the isolated viewpoints.
3. **Anti-echo-chamber.** Same-session roleplay is *not* runtime isolation;
   mark it `同会话SubAgent(低权重)` and treat its weight accordingly.
4. **Convergence.** Cover 执行 / 产品 / 市场 / 架构, then stop adding
   perspectives. More views is a means, not a goal.
5. **Conclusion must be executable.** A sub-doc conclusion must include
   deposition instructions (which PRD/ADR to change, which temp doc to delete)
   — otherwise it is not a closed loop.

## References

- `references/master-template.md` — MASTER.md skeleton (incl. disposition contract).
- `references/subdoc-template.md` — per-sub-problem discussion doc skeleton.
- `references/role-matrix.md` — reusable 4-role matrix + convergence rule.

## Integration with sibling skills

- `zj-docs-ontology` — phase 2 disposition (durable deposition + deletion).
- `zj-steelman` / `zj-handoff` — referenced by `zj-discuss-view` for
  role-switching and briefing preparation.
- `zj-grilling` — use beforehand to sharpen the core problem framing.
