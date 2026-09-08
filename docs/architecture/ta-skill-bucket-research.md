---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.research
---

# Research bucket

## Question

What does the `skills/research/` subsystem own, what does it expose, and
how does it fail?

## Scope

This page describes the research bucket as an architecture subsystem. The
bucket holds skills that produce evidence, primary-source findings, sealed
ledgers, and bounded technical-solution research reports. It does **not**
own documentation governance (codebase-docs owns that) and does **not**
own code-change skills (engineering owns that).

## Boundaries

This page describes the research bucket as an architecture subsystem. The
bucket holds skills that produce evidence, primary-source findings, sealed
ledgers, and bounded technical-solution research reports. It does **not**
own documentation governance (codebase-docs owns that) and does **not**
own code-change skills (engineering owns that).

## Responsibility

Evidence production and domain-study skills used when a Human asks for a
research-shaped answer rather than a code change. The bucket covers:

- primary-source finding capture (`zj-research`),
- commit-scoped repository mapping (`zj-code-research`),
- technical-solution recommendation writing
  (`zj-tech-research-report`),
- end-to-end product/company/technology origin-to-present studies
  (`zj-systematic-research`).

The bucket produces artefacts that flow into `research/`; it does not
promote those artefacts into durable authority. Promotion is a separate
governance pass under `zj-docs-ontology`.

## Owned state

- The skill folders under `skills/research/` (4 entries) plus their
  per-skill `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- No state outside the bucket: research skills write to `research/` (the
  evidence surface) and never to `docs/` without explicit Human
  confirmation.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts asking for a research package, a recommendation, or a domain study. |
| Outbound | Research packages, sealed evidence ledgers, technical-solution recommendation reports, and end-to-end studies written into `research/`. |
| Cross-bucket | Reads `ZJ-CONTEXT.md` for vocabulary; reads `docs/designs/` and `docs/zj-adr/` for the historical decisions it must respect; reads but does not write into other buckets. |
| External | Connects to external information sources through the skill's own `scripts/` and per-skill `references/`; relies on `scripts/` for shared utilities. |

## Failure behavior

- A skill that cannot reach its primary sources stops and reports the gap;
  it does not invent findings.
- A sealed ledger (`zj-research`) is treated as immutable after sealing;
  amendments create a new ledger rather than rewriting the sealed one.
- A repository-mapping skill (`zj-code-research`) refuses to map a
  repository that lacks a recent commit hash for anchoring; it does not
  silently default to HEAD without flagging the default.
- A technical recommendation report (`zj-tech-research-report`) halts on
  unsupported claims; it labels inference, target architecture, and
  implemented behaviour separately rather than smoothing them into one
  recommendation.

## Source map

- [Bucket README](../../skills/research/README.md) — local index.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary the bucket respects.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  evidence-boundary contract that governs when research outputs become
  durable authority.
- [zj-research](../../skills/research/zj-research/SKILL.md) — the
  primary-source and sealed-ledger producer.
- [zj-code-research](../../skills/research/zj-code-research/SKILL.md) —
  the commit-scoped repository mapper.
- [zj-systematic-research](../../skills/research/zj-systematic-research/SKILL.md) —
  the origin-to-present domain study.
- [zj-tech-research-report](../../skills/research/zj-tech-research-report/SKILL.md) —
  the technical-solution recommendation writer.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [Layers](ta-zagentic-layers.md) — layer-8 evidence surface and the
  no-direct-promotion rule.
