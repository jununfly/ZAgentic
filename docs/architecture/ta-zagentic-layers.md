---
doc-kind: architecture-layers
authority: primary
authority-id: architecture.layers.zagentic
---

# ZAgentic layers and allowed dependencies

## Question

Which dependencies are allowed between the layers of this repository, and
which ones are explicitly forbidden?

## Scope

This page describes the layered shape of the ZAgentic repository from the
skill instructions at the top to the authoritative documentation at the
bottom. It covers the public `skills/` tree, the root-level `personal/` tree,
the `scripts/` pipeline, and the `docs/` documentation system. It does not
restate the validation scripts' internal logic (each validator is its own
source of truth) or the per-bucket ownership (the bucket subsystem pages own
those).

## Boundaries

- The layering is a **dependency rule**, not a deployment topology. Each
  layer names what it may call into and what it must not. Concrete callers
  must add a `source-map` reference on the page that needs them.
- A layer may **link** to a lower layer; a layer must **not modify** the
  layer it links into. The only write boundaries are the bucket README
  index, the top-level README index, the Git history, the generated
  `scripts/zagentic-skills-list`, and the documentation system under explicit
  Human confirmation.
- The `research/` and `skills-outputs/` directories are evidence surfaces,
  not documentation layers. Skills may consume them as supported evidence but
  must not promote their contents into a durable authority without a Human
  confirmation.

## Layers

Top to bottom. A higher layer may link, read, or invoke a lower layer. A
lower layer must not reach upward. The middle column names the write
boundary; everything else is read-only from above.

| # | Layer | Location | Owner responsibility | May read | Must not write |
| --- | --- | --- | --- | --- | --- |
| 1 | Skill index | top-level [README.md](../../README.md) and each [bucket README](../../skills/) | Catalog and entry points | layer 2 (its own bucket) | nothing (index only) |
| 2 | Skill instructions | `skills/<bucket>/<skill>/SKILL.md` | Workflow description, frontmatter | layer 3 to 6, plus shared scripts when documented | layer 1 (no index edits) |
| 3 | Skill resources | `skills/<bucket>/<skill>/references/`, `agents/` | Load-on-demand detail | local filesystem; shared scripts | layer 2 body |
| 4 | Skill helpers | `skills/<bucket>/<skill>/scripts/` | Executable helpers owned by one skill | shared scripts; skill resources | anything outside its own directory |
| 5 | Validator fixtures | `skills/<bucket>/<skill>/tests/` | Self-contained test payloads | shared scripts | anything outside its own directory |
| 6 | Installer and validator pipeline | `scripts/` | Repository-wide installation and contract enforcement | layer 2 to 5 (with explicit paths) | layer 2 body; bucket README; top-level README; `docs/`; `personal/README.md` |
| 7 | Documentation authority | `docs/` plus root `ZJ-CONTEXT.md`, `ZJ-CONTEXT-MAP.md`, `AGENTS.md`, `CLAUDE.md` | Long-lived durability | evidence surfaces `research/`, `skills-outputs/` | itself without explicit Human confirmation (via `zj-docs-ontology`) |
| 8 | Evidence surfaces | `research/`, `skills-outputs/` | Per-session and per-research outputs | own contents | layer 7 (no claim promotion) |

The installer and validator pipeline (`scripts/`) is a special layer: it may
read every other layer to install or validate, and it is the only layer that
may write to itself (regenerating `scripts/zagentic-skills-list`,
refreshing `.codex-plugin/plugin.json`, and so on) as long as the write is
declared in its own source-map.

## Personal-tree specialisation

The root-level `personal/` tree follows the same layer stack as a public skill
on the **deployment** side, but it has a separate **discovery** path:

- A skill under `personal/` has identical layer-2 to layer-5 internal layout
  as a public skill.
- It is excluded from `scripts/validate-zagentic-plugin.py`'s recursive
  `skills/` discovery, from the top-level `README.md`, and from the bucket
  `README.md` indexes.
- Its own `README.md` serves as a local index; the link script still
  installs it into the same target directories because installation is
  independent of plugin discovery.
- Documentation authority (`docs/`) may describe the personal tree (this
  architecture does) but must not modify any file inside it.

## Allowed dependencies

These are the dependency patterns each layer may legally use. They are
non-binding names; any layer that adopts one must reference this page so the
adoption is auditable.

- **Skill references shared script**: `SKILL.md` instructs "run
  `scripts/validate-plugin.sh`"; the validator lives at layer 6 and the
  skill does not bundle a duplicate. Documented in the skill's
  `source-map` section if the skill has one.
- **Skill references skill helper**: A skill's `SKILL.md` instructs "run
  `scripts/<own-skill>/do-thing.py`"; the helper lives at layer 4 within
  that skill. Cross-skill calls between layer 4 helpers must go through
  layer 2 narration; they do not import each other directly.
- **Skill references design or ADR**: A skill's `SKILL.md` or
  `references/` cites a `docs/designs/` or `docs/zj-adr/` page as its
  normative source. The skill does not restate the rule.
- **Documentation references skill**: An architecture or design page cites
  a `SKILL.md` as its implementation source. The documentation does not
  copy the skill's prose.

## Forbidden patterns

- **Skill writing to `docs/`**: A skill must not create, modify, or delete
  documentation pages. Governance flows live under `zj-docs-ontology` and
  require explicit Human confirmation.
- **Skill writing to `scripts/` outside its own bundle**: A skill may ship
  helpers under `skills/<bucket>/<skill>/scripts/` and may invoke shared
  scripts at layer 6; it must not add new files into `scripts/`.
- **Bucket README referencing personal-skill content**: Public bucket
  indexes must not list skills from `personal/`. The visibility split is
  contractual.
- **Documentation restating design or ADR**: The architecture handbook
  links to design and ADR pages; it does not duplicate their normative
  prose.
- **Evidence surface promoted to authority**: A research output in
  `research/` or a session artifact in `skills-outputs/` is not a
  documentation page. Its durable value reaches a long-lived authority
  only after an explicit extraction pass.

## Source map

- [AGENTS.md](../../AGENTS.md) — bucket policy, plugin-discovery rule, and
  Git safety requirement that the index layer relies on.
- [CLAUDE.md](../../CLAUDE.md) — Claude-side companion to the same rules.
- [recursive plugin validator](../../scripts/validate-zagentic-plugin.py) —
  discovery target and one of the two top-of-stack entry points.
- [skill frontmatter validator](../../scripts/validate-skill-frontmatter.py) —
  the second top-of-stack entry point.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  authority for the layer-7 mutation rule.

## Related authority

- [System overview](ta-zagentic-overview.md) — the 5 + 1 model this page
  rests on.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the single shared
  rule that enforces the public vs personal-tree separation.
- [Pipelines](ta-zagentic-pipelines.md) — install, validation, and
  governance flow that crosses these layers.
- The six per-bucket subsystem pages linked from the [architecture
  map](README.md).
