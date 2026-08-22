Public skills are organized into bucket folders under `skills/`; private skills
live in the separate root-level `personal/` tree:

- `engineering/` — daily code work
- `productivity/` — daily non-code workflow tools
- `misc/` — kept around but rarely used
- `personal/` — tied to my own setup, installable but not promoted or plugin-registered

Before adding, moving, or removing an Initiative, spec, or roadmap plan in `docs/plans/global-initiative-roadmap.json`, read [its maintenance rules](docs/plans/global-initiative-roadmap.agent.md); the global index uses a fixed three-level model that differs from `zj-roadmap-driven` execution roadmaps.

Material placement is purpose-based: put shared input material in
`skills-inputs/<topic>/`; put artifacts produced by a skill in
`skills-outputs/<skill>/<topic>/`.

Every skill in `engineering/`, `productivity/`, or `misc/` must have a reference in the top-level `README.md` and an entry in `.codex-plugin/plugin.json`. Skills in the root-level `personal/` tree must not appear in either.

Each skill entry in the top-level `README.md` must link the skill name to its `SKILL.md`.

Each public bucket folder has a `README.md` that lists every skill in the bucket with a one-line description, with the skill name linked to its `SKILL.md`. The root-level `personal/` tree has the same local index but is excluded from public indexes.

## PR checklist (1-3-3-1 A-only 3 rule)

Every skill-touching PR must satisfy all three:

1. **Plugin registration** — if `skills/` changed, verify the new/changed skill is listed in `.codex-plugin/plugin.json` (or the bucket `README.md`, which is what Claude reads). Skills not registered are invisible to the harness.
2. **Safe git operations** — all git operations go through `./scripts/zj-git` (or `env -u NODE_OPTIONS git`). The WorkBuddy safe-delete shim corrupts `.git/` on Windows Git Bash; see `skills/engineering/zj-git-bypass-safe-delete/`.
3. **Vocabulary sync** — any new domain term introduced in the PR must be added to `ZJ-CONTEXT.md` before merge. Skills that "make up" vocabulary break downstream skills that consume it.

## Cross-stage skills (1-6)

Three skills live in `engineering/` but are not A↔B-specific — they are the meta-capabilities of any skill-pair workflow:

- `zj-steelman` — pre-plan defense (before grilling)
- `zj-dry-run` — pre-commit rehearsal (mid-plan)
- `zj-debrief` — post-task close-out (after completion)

Use them. See `docs/designs/zj-cross-stage-skills.md` for the complementarity matrix.
