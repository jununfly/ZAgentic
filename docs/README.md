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
| What is the current technical architecture of ZAgentic? | [docs/architecture/](architecture/) | Long-lived architecture handbook; routing only — view pages own their bounded questions and link (not duplicate) design and ADR authorities. |
| Why was a hard-to-reverse decision accepted? | [docs/zj-adr/](zj-adr/) | Decision rationale; it does not replace current architecture or rules. |
| What is specified and ready for an Agent to build? | [docs/plans/](plans/) | Agent-grabbable specs produced by `zj-to-spec`; a spec records intent, decisions and test seams, it does not replace ADR rationale or current skill behavior. |

### Primary design authorities

| Authority ID | Bounded question | Page |
| --- | --- | --- |
| `design.cross-stage-checkpoints` | Which focused checkpoints complement a ticketed delivery flow? | [Cross-stage checkpoints](designs/zj-cross-stage-skills.md) |
| `design.skill-frontmatter-schema` | What frontmatter and sidecar rules make a skill mechanically discoverable? | [Skill frontmatter validation boundary](designs/zj-skill-frontmatter-schema.md) |
| `design.wayfinder-roadmap-carrier-seam` | How do wayfinding and roadmap tracking hand off across their carriers? | [Wayfinder and roadmap carrier seam](designs/zj-wayfinder-roadmap-dual-mode.md) |

### Primary architecture authorities

Each bullet below binds the page to its primary `authority-id`. The
architecture map itself links to these pages from the routing table; the
table here is the readable inventory. Source authority is held by
`docs/architecture/README.md` (the architecture map), which the validator
recognises as the routing surface rather than a primary view page.

- [System overview](architecture/ta-zagentic-overview.md) — What is ZAgentic, what is it not, and which view answers which question about it?; authority-id: `architecture.overview.zagentic`.
- [Layers](architecture/ta-zagentic-layers.md) — Which dependencies are allowed between the layers of this repository, and which ones are explicitly forbidden?; authority-id: `architecture.layers.zagentic`.
- [Pipelines](architecture/ta-zagentic-pipelines.md) — What are the install / validate flow and the documentation governance flow, end to end?; authority-id: `architecture.flow.install-and-docs-governance`.
- [Bucket discipline](architecture/ta-skill-bucket-boundary.md) — What single shared rule governs the public-bucket / personal-tree / authority boundary?; authority-id: `architecture.cross-cutting.bucket-discipline`.
- [Engineering bucket](architecture/ta-skill-bucket-engineering.md) — What does the `engineering/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.bucket.engineering`.
- [Codebase-docs bucket](architecture/ta-skill-bucket-codebase-docs.md) — What does the `codebase-docs/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.bucket.codebase-docs`.
- [Productivity bucket](architecture/ta-skill-bucket-productivity.md) — What does the `productivity/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.bucket.productivity`.
- [Misc bucket](architecture/ta-skill-bucket-misc.md) — What does the `misc/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.bucket.misc`.
- [Research bucket](architecture/ta-skill-bucket-research.md) — What does the `research/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.bucket.research`.
- [Personal skill tree](architecture/ta-zagentic-personal-tree.md) — What does the root-level `personal/` subsystem own, expose, and how does it fail?; authority-id: `architecture.subsystem.personal-tree`.

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
bounded question. The current empty categories are `methods/`,
`agreements/`, `testing/`, `benchmarks/`, `references/`, and `plans/`.
When created, each must state its lifecycle, bounded question, and authority
boundary here. New architecture pages also follow `zj-docs-architecture`'s
view contract.
