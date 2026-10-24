docs-map: docs/README.md

Public skills live under `skills/`; private skills live in root-level `personal/`:

- `engineering/` — daily code work
- `codebase-docs/` — documentation systems for one codebase
- `productivity/` — daily non-code workflows
- `ui/` — the UI delivery chain, one skill per lifecycle stage (contract-first)
- `misc/` — infrequent utilities
- `research/` — evidence production and domain-specific research methods
- `personal/` — installable personal setup, not promoted or plugin-registered

Keep reusable templates with their owning skill (normally `references/`); put
skill-produced artifacts in `skills-outputs/<skill>/<topic>/`.

**Skill runtime closure:** a skill is a self-contained published unit. Skills are
installed on arbitrary devices, and an install carries ONLY the skill directory —
files stored in any other directory (e.g. `docs/`) are NOT shipped with it.
Therefore every file a skill reads or references at runtime (via `open()` in
`scripts/`, or instructions in `SKILL.md`/`references/`) MUST be fully contained
in the skill's own implementation files. Do not depend on `ZAgentic/docs` or any
external path at runtime; an installed skill must run without the source repo.
Repo-level SSOT docs stay in `docs/`, not in a single skill — but anything the
skill actually consumes at runtime must still be inside the skill. See
`docs/designs/zj-skill-runtime-closure.md` (mechanical gate:
`scripts/check-skill-runtime-closure.py`).

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

**ADR / docs 事实治理：** ADR（`docs/zj-adr/`）是 docs 治理范围的一部分，不是一次性决策快照。每次 docs 改动需顺带核对 ADR 的事实陈述（技能名、commit、路径、计数断言）；语义性事实（桶归属、数量）由人工在改动时复核。可机械验证的部分由 CI 的 `docs-dangling-refs` job 自动覆盖：`scripts/check-docs-dangling-refs.py`（链接/路径）与 `scripts/check-adrs.py`（commit 与技能名引用）。
