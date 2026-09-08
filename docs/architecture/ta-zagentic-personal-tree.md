---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.personal-tree
---

# Personal skill tree

## Question

What does the root-level `personal/` subsystem own, what does it expose,
and how does it fail? Why is it a separate subsystem instead of another
public bucket?

## Scope

This page describes the root-level `personal/` tree as an architecture
subsystem. The tree has the same internal layer stack as a public skill
(see [layers](ta-zagentic-layers.md)) but a different discovery and
registration path. It is **not** a sixth public bucket; it is a parallel
path. This page names that distinction, the responsibilities the tree
takes, and the responsibilities it explicitly declines.

## Boundaries

The root-level `personal/` tree is a parallel installable path, not a
sixth public bucket. It is excluded from plugin discovery, from the
top-level `README.md`, and from any bucket `README.md`, but it still
follows the same internal layer stack as a public skill and still
participates in the same link script and validators.

## Responsibility

The personal tree hosts skills tied to the user's own setup. It is
installable through the same link script and participates in the same Git
safety rules, but it is excluded from plugin discovery, from the
top-level `README.md`, and from any bucket `README.md`. The tree publishes
its own local index (`personal/README.md`) and names its own skills
through it.

Responsibilities the tree takes:

- shipping setup-specific skills that the maintainer installs locally but
  does not want promoted as a public catalogue entry,
- preserving the "personal" visibility boundary through explicit
  exclusion from public indexes,
- reading the same `ZJ-CONTEXT.md` and `AGENTS.md` so personal-skill
  authors and public-skill authors share vocabulary.

Responsibilities the tree explicitly declines:

- being a sixth public bucket,
- being indexed from the top-level `README.md` or any public bucket
  `README.md`,
- being a sink for skills that the maintainer has not yet decided to
  promote (a personal skill that becomes a public skill moves through
  `zj-docs-ontology` with explicit Human confirmation),
- bypassing validation; personal skills still go through
  `validate-skill-frontmatter.py` and `validate-zagentic-plugin.py`'s
  personal-tree pass.

## Owned state

- The skill folders under `personal/` (currently 2 entries) plus their
  per-skill `references/` and `scripts/` directories.
- The `personal/README.md` local index.
- No state outside `personal/`: a personal skill does not modify public
  skills, the top-level `README.md`, any bucket `README.md`, or `docs/`.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts that explicitly name a personal skill (the personal tree is not in the public routing path; routing skills such as `zj-guide` will not surface it). |
| Outbound | Per-skill artefacts produced on the maintainer's own machine. |
| Cross-bucket | Reads public skills as needed; never writes into them. |
| External | Installed through `scripts/link-skills.sh` exactly like a public skill, but the installer treats the personal tree as one source among many. |

## Failure behavior

- An install-time conflict (a same-named target folder already exists)
  prompts the maintainer before overwriting. The default is "replace" but
  the prompt is explicit; the flow never silently overwrites.
- A personal skill that stops meeting the frontmatter contract fails
  validation; the maintainer decides whether to fix, rename, or move it.
- A personal skill that grows into public-skill scope is migrated through
  `zj-docs-ontology` with explicit Human confirmation; it is not promoted
  by editing the top-level `README.md`.

## Why a parallel path, not a sixth bucket

Buckets are public entries. The repository policy (`AGENTS.md`) requires
every skill under `engineering/`, `codebase-docs/`, `productivity/`,
`misc/`, or `research/` to participate in plugin discovery and to appear
in both the bucket and top-level indexes. Promoting a personal skill
without that readiness would force the promotion before the maintainer is
ready; withholding it indefinitely would erase it from the catalog. The
personal tree is the middle path: installable, governed, and discoverable
on the maintainer's machine, without burning a public index entry. The
boundary is held by the validation script
(`scripts/validate-zagentic-plugin.py`) that excludes `personal/` from the
recursive public walk.

## Source map

- [personal/README.md](../../personal/README.md) — local index of the
  personal tree.
- [AGENTS.md](../../AGENTS.md) — public-registration rule that excludes
  the personal tree.
- [scripts/validate-zagentic-plugin.py](../../scripts/validate-zagentic-plugin.py) —
  the recursive validator that excludes the personal tree while still
  validating it through its dedicated pass.
- [scripts/link-skills.sh](../../scripts/link-skills.sh) — the installer
  that treats both trees uniformly.
- [zj-edit-article](../../personal/zj-edit-article/SKILL.md) — a personal
  skill carrying a platform sidecar under its own
  `personal/zj-edit-article/agents` directory, illustrating the tree's
  internal layout.
- [zj-obsidian-vault](../../personal/zj-obsidian-vault/SKILL.md) — the
  second personal skill, same layout.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [System overview](ta-zagentic-overview.md) — the 5 + 1 model this
  subsystem completes.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule that establishes "parallel path, not duplicate path".
- [Layers](ta-zagentic-layers.md) — the personal-tree layer
  specialisation.
