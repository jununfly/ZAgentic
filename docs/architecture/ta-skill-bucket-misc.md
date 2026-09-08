---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.misc
---

# Misc bucket

## Question

What does the `skills/misc/` subsystem own, what does it expose, and how
does it fail?

## Scope

This page describes the misc bucket as an architecture subsystem. The
bucket holds skills that are kept around but rarely used: integration
shims, platform-specific safety wrappers, code-base utilities, and
information services that the rest of the repository does not depend on
for its main flow. It is **not** a place for new daily workflows (those go
to `engineering/` or `productivity/`) and it is **not** a place for
documentation governance (that is `codebase-docs/`).

## Boundaries

The misc bucket holds auxiliary skills the repository carries for
completeness without promoting them to a daily-work bucket. It is **not**
a place for new daily workflows (those go to `engineering/` or
`productivity/`) and it is **not** a place for documentation governance
(that is `codebase-docs/`).

## Responsibility

A small set of auxiliary skills the repository carries for completeness
without promoting them to a daily-work bucket. The bucket covers:

- external information services (for example `zj-aihot`),
- platform-specific safety wrappers (`zj-git-guardrails-claude-code`),
- ecosystem migration helpers (`zj-migrate-to-shoehorn`),
- scaffolding utilities (`zj-scaffold-exercises`,
  `zj-setup-pre-commit`),
- host-level analysis tools (`zj-storage-analyzer`).

## Owned state

- The skill folders under `skills/misc/` (6 entries) plus their per-skill
  `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- No state outside the bucket; no bucket-owned skill writes into another
  bucket, into `docs/`, or into `scripts/` outside its own bundle.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts that explicitly name a misc skill (the bucket is not in the daily routing path). |
| Outbound | Per-skill artefacts (AI news digests, storage reports, pre-commit configurations, scaffolded exercise directories). |
| Cross-bucket | Reads other buckets' skills for cross-reference; does not write into them. |
| External | Consumes external APIs or platform-specific tools; its dependencies are the skill's own `SKILL.md` and per-skill `scripts/`. |

## Failure behavior

- An external-API failure surfaces as an explicit non-zero exit and a
  Human-readable message; the skill never retries silently.
- A platform-specific wrapper (`zj-git-guardrails-claude-code`) defers to
  the platform's hook configuration rather than rewriting a hook silently.
- A scaffold utility produces a dry-run plan when its target directory is
  non-empty; it never overwrites a populated tree.

## Source map

- [Bucket README](../../skills/misc/README.md) — local index.
- [zj-aihot](../../skills/misc/zj-aihot/SKILL.md) — the external
  information service.
- [zj-git-guardrails-claude-code](../../skills/misc/zj-git-guardrails-claude-code/SKILL.md) —
  the platform hook wrapper.
- [zj-setup-pre-commit](../../skills/misc/zj-setup-pre-commit/SKILL.md) —
  the commit-time quality configuration.
- [zj-storage-analyzer](../../skills/misc/zj-storage-analyzer/SKILL.md) —
  the host-level analysis tool.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [Layers](ta-zagentic-layers.md) — layer-2 read scope with no write
  authority beyond layer 1.
