# ZAgentic documentation map

This map routes readers to the maintained documentation for this repository.
It distinguishes long-lived authority from process material and evidence
surfaces; navigation order does not establish global truth precedence.

## Start here

| Question | Entry | Boundary |
| --- | --- | --- |
| What vocabulary does ZAgentic use? | [ZJ-CONTEXT.md](../ZJ-CONTEXT.md) | Root-level external documentation entry; its glossary owns terminology. |
| Which skill or workflow fits? | [root README](../README.md) and [`zj-guide`](../skills/engineering/zj-guide/SKILL.md) | Public skill catalog and routing, not architecture authority. |
| How must an Agent work in this repository? | [AGENTS.md](../AGENTS.md) | Immediate repository rules; agreements are created lazily when concrete collaboration configuration needs them. |

## Long-lived documentation

| Question | Location | Authority boundary |
| --- | --- | --- |
| What capability boundary governs one codebase's documentation system? | [Codebase Docs capability spec](prds/codebase-docs-capability.md) | Approved product and delivery boundary; current skill behavior remains authoritative. |
| Why and how does a bounded design work? | [docs/designs/](designs/) | Design rationale and implementation-facing explanations. |
| Why was a hard-to-reverse decision accepted? | [docs/zj-adr/](zj-adr/) | Decision rationale; it does not replace current architecture or rules. |

### Primary design authorities

| Authority ID | Bounded question | Page |
| --- | --- | --- |
| `design.cross-stage-checkpoints` | Which focused checkpoints complement a ticketed delivery flow? | [Cross-stage checkpoints](designs/zj-cross-stage-skills.md) |
| `design.skill-frontmatter-schema` | What frontmatter and sidecar rules make a skill mechanically discoverable? | [Skill frontmatter validation boundary](designs/zj-skill-frontmatter-schema.md) |
| `design.wayfinder-roadmap-carrier-seam` | How do wayfinding and roadmap tracking hand off across their carriers? | [Wayfinder and roadmap carrier seam](designs/zj-wayfinder-roadmap-dual-mode.md) |

## Process material

| Question | Location | Lifecycle |
| --- | --- | --- |
| What did a completed session reveal? | `docs/zj-retros/` (created lazily by `zj-debrief`) | Process material pending durable extraction, authority audit, and separately confirmed deletion. |

## Evidence boundaries

[research/](../research/) and [skills-outputs/](../skills-outputs/) are evidence
surfaces. They may support a documented claim but are not long-lived
documentation pages, and this map neither moves nor governs their storage.

## Lazy categories

Create a category only when the repository has a concrete document for its
bounded question. The current empty categories are `methods/`, `architecture/`,
`agreements/`, `testing/`, `benchmarks/`, `references/`, and `plans/`.
When created, each must state its lifecycle, bounded question, and authority
boundary here. New architecture pages also follow `zj-docs-architecture`'s
view contract.
