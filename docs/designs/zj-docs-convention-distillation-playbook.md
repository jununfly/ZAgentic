---
doc-kind: design
authority: primary
authority-id: design.docs-convention-distillation
---

# Docs convention distillation playbook (跨仓文档规范蒸馏)

## Question

How do we turn the docs/ conventions of N external repositories into an
auditable, portable practice matrix — without building a skill for a
workflow that has run exactly once?

Decision (2026-10-28, N-5): **do not build a "cross-repo distiller" skill**.
The composition below uses installed capabilities that already exist, and a
dedicated skill would pay permanent maintenance tax (three-copy sync, index
entries, closure gates) for speculative reuse. This playbook is the recorded
method; upgrade it to a skill when a **second real use case** appears.

## Method

Five stages, each with an installed owner and a verifiable output:

1. **Evidence (zj-research).** One source = one file path inside one
   repository. Every practice claim needs the three-part receipt: source
   URL + commit pin + verbatim quotation. Pin via the hosting API (GitHub
   commits API works; gitiles may not). If a mirror is used instead of the
   upstream host, record the mirror and its time lag.
2. **Term convergence (zj-domain-modeling).** A table of new terms, each
   with a definition, an owning layer, and — equally important — an explicit
   **not-introduced list**: terms that collide with load-bearing words
   (e.g. `seam`, `gate`, `vocabulary`) or are host-specific (e.g. Mintlify
   navigation names) are rejected by name, not silently dropped.
3. **Adoption matrix (zj-open-source-capability-fit).** One row per
   practice, verdict on a fixed scale: adopt / parameterize-then-adopt /
   selective-reuse / defer / **reject (key capability missing)**. A
   `reject` row must name what is missing — that is where required-skill
   gaps come from. Guard against host-specific contracts crossing over.
4. **Change design (zj-tech-design-review).** For every non-reject row: a
   file-level diff plan, affected diagnostics, fixtures, risks, rollback.
   Value conflicts (e.g. "delete dead docs by default") are settled here by
   the Human, and rejections get a recorded verdict — a `Rejected defaults`
   section, not silence.
5. **Red-green landing (zj-tdd + zj-implement).** Contract-guard tests in
   the defect state first, then the change, then mutation checks proving
   the tests can fail. New prose goes into `references/`, not SKILL.md;
   pointer and budget discipline applies (zj-writing-for-agents rules).

## Worked example

The 2026-10-28 round ran this exact chain over chromium /
deepseek-harness / semantica / openai-codex and produced: 12 pinned
sources, 40 evidence rows, a 16-row adoption matrix (A6/B1-3/B2-3/C-3/D-1),
the `zj-docs-ontology` quality contract, and ADR 0011. Composer plan and
evidence live in the zj-composer skills-outputs workspace of that date.

## Source map

- [zj-research](../../skills/research/zj-research/SKILL.md)
- [zj-domain-modeling](../../skills/codebase-docs/zj-domain-modeling/SKILL.md)
- [zj-open-source-capability-fit](../../skills/research/zj-open-source-capability-fit/SKILL.md)
- [zj-tech-design-review](../../skills/engineering/zj-tech-design-review/SKILL.md)
- [zj-tdd](../../skills/engineering/zj-tdd/SKILL.md)
- [governance-contract](../../skills/codebase-docs/zj-docs-ontology/references/governance-contract.md)
