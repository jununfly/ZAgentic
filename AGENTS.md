Public skills live under `skills/`; private skills live in root-level `personal/`:

- `engineering/` — daily code work
- `codebase-docs/` — documentation systems for one codebase
- `productivity/` — daily non-code workflows
- `misc/` — infrequent utilities
- `research/` — evidence production and domain-specific research methods
- `personal/` — installable personal setup, not promoted or plugin-registered

Keep reusable templates with their owning skill (normally `references/`); put
skill-produced artifacts in `skills-outputs/<skill>/<topic>/`.

Every public skill must participate in recursive `./skills/` discovery and have
a name-linked, one-line entry in both its bucket `README.md` and the top-level
`README.md`. `personal/README.md` is its local index and stays out of public
indexes. `.codex-plugin/plugin.json` is legacy and not required.

Use `./scripts/zj-git` (or `env -u NODE_OPTIONS git`) for every Git operation;
the WorkBuddy safe-delete shim can corrupt `.git/` on Windows Git Bash. Add each
new domain term to `ZJ-CONTEXT.md` before merge.

For a skill-pair workflow, use `zj-steelman` before grilling, `zj-dry-run`
before commit, and `zj-debrief` after completion (`codebase-docs/`). See
`docs/designs/zj-cross-stage-skills.md` for their complementarity matrix.
