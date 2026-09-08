---
doc-kind: architecture-overview
authority: primary
authority-id: architecture.overview.zagentic
---

# ZAgentic system overview

## Question

What is `jununfly/ZAgentic`, what is it not, and which architecture view
answers which question about it?

## Scope

This overview describes the ZAgentic repository's current architectural shape:
the skills collection, its installer and validator pipelines, and the
documentation governance that makes the collection cohere. It names the
5 + 1 model (five public skill buckets plus one root-level personal tree) and
points each reader at the right view. It deliberately does not restate the
individual skill workflows, the bucket-selection rules, or the historical
decisions behind the bucket layout.

## Boundaries

- The ZAgentic repository is a **skills collection**, not an application. The
  delivered artefact is a set of `SKILL.md` files plus the helpers that make
  them discoverable, installable, and validatable on Agent platforms. There
  is no product runtime, no shipped binary, and no runtime service.
- The exterior boundary is the supported Agent platforms it ships to:
  `claude`, `codex`, and `workbuddy`. Beyond those, the recursive plugin
  discovery, the frontmatter contract, and the installer preset all assume
  the platform resolves `SKILL.md` through standard scanning.
- The 5 + 1 skill model is the deliberate shape of the collection, not a
  side effect of file layout. Reorganising buckets is an ADR-bearing change.

## System boundary

The exterior boundary is the supported Agent platforms it ships to:
`claude`, `codex`, and `workbuddy`. Beyond those, the recursive plugin
discovery, the frontmatter contract, and the installer preset all assume
the platform resolves `SKILL.md` through standard scanning. The
repository holds three kinds of source — skills, scripts, documentation —
and each kind has its own authority boundary; this section lists them.

| Direction | Boundary |
| --- | --- |
| Inbound | Human prompts on supported Agent platforms; the recursive `skills/` discovery; installable skills via `skills.sh` and the local `scripts/link-skills.sh`. |
| Outbound | Skill instructions installed into `~/.claude/skills`, `~/.codex/skills`, `~/.workbuddy/skills`; documentation under `docs/`; evidence surfaces under `research/` and `skills-outputs/`. |

## Major parts

- **Five public skill buckets** under `skills/`, each with its own
  `README.md` index and a one-line registration in the top-level
  `README.md`:

  | Bucket | Count | Responsibility (held by the bucket page, restated here for routing) |
  | --- | --- | --- |
  | `engineering/` | 21 | Daily code work; daily engineering decisions. |
  | `codebase-docs/` | 8 | One-codebase documentation governance; documentation architecture. |
  | `productivity/` | 8 | Daily non-code workflow skills. |
  | `misc/` | 6 | Kept around but infrequently used. |
  | `research/` | 4 | Evidence production and domain-study methods. |

- **One root-level skill tree** at `personal/`. It contains two skills,
  installs through the same link script, but is explicitly excluded from
  plugin discovery, from the top-level `README.md`, and from the bucket
  indexes. Its boundary is the architectural counterpart to the public
  buckets.

- **Installer and validator pipeline** under `scripts/`. It includes the
  recursive plugin validator (`validate-zagentic-plugin.py`), the skill
  frontmatter validator (`validate-skill-frontmatter.py`), the link
  installer (`link-skills.sh`), and the Git safety wrapper (`zj-git`)
  that bypasses the WorkBuddy safe-delete shim on Windows Git Bash.

- **Documentation system** under `docs/` plus root-level context entries
  (`ZJ-CONTEXT.md`, `ZJ-CONTEXT-MAP.md`, `AGENTS.md`, `CLAUDE.md`). It owns
  the document map, the design authorities, the ADR history, the process
  material, and now the architecture handbook routed from this map.

## Reader routing

| Reader question | Route |
| --- | --- |
| Where do I start? | [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) for vocabulary; the top-level [README.md](../../README.md) and [zj-guide](../../skills/engineering/zj-guide/SKILL.md) for skill selection. |
| What does each bucket own? | The six subsystem pages linked from the [architecture map](README.md). |
| How is the repository built? | The [layers](ta-zagentic-layers.md) page for the layered dependency rules, and the [pipelines](ta-zagentic-pipelines.md) page for install, validation, and governance flows. |
| Which shared rule applies to every view? | The [bucket-discipline](ta-skill-bucket-boundary.md) cross-cutting page. |
| Why is something the way it is? | The [designs](../designs/) directory and the [ADR](../zj-adr/) directory; this overview does not duplicate them. |

## Source map

- [Top-level README](../../README.md) — public skill catalog and
  installation entry points.
- [AGENTS.md](../../AGENTS.md) — bucket policy, plugin-discovery rule, and
  Git safety requirement that the layers page relies on.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary used by every view.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  accepted capability boundary for the codebase-docs bucket and the
  governance flow.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Layers and allowed dependencies](ta-zagentic-layers.md) —
  `architecture.layers.zagentic`.
- [Pipelines](ta-zagentic-pipelines.md) —
  `architecture.flow.install-and-docs-governance`.
- [Bucket discipline](ta-skill-bucket-boundary.md) —
  `architecture.cross-cutting.bucket-discipline`.
- The six per-bucket subsystem pages linked from the architecture map.
