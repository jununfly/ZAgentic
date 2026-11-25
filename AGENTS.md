docs-map: docs/README.md

Public skills live under `skills/`; private skills live in root-level `personal/`:

- `engineering/` — daily code work
- `codebase-docs/` — documentation systems for one codebase
- `productivity/` — daily non-code workflows
- `ui/` — the UI delivery chain, one skill per lifecycle stage (contract-first)
- `misc/` — infrequent utilities
- `research/` — evidence production and domain-specific research methods
- `personal/` — installable personal setup, not promoted or plugin-registered

**Local file persistence (ADR 0010):** every skill that writes durable local
artifacts stores only *relative* paths and lands them in an isolated zone. By
usage scenario: project-output artifacts go to
`<project-root>/tmp/skills-outputs/<skill>/<topic>/` (gitignored); process/plan
artifacts (roadmap, wayfinder map) go to `docs/plans/<skill>/...` (tracked,
cleaned after close-out); non-project-output artifacts must prompt the Human for a
path — never default to `~/`, `~/Desktop`, `cwd`, or the repo root. Never store
absolute paths in git-tracked files. The `closure-lint` gate enforces this.

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

**Cross-boundary shared facts (DRY × runtime closure):** when several skills need
the *same* vocabulary, value-domain, or rule, DRY (one authoritative source) and
runtime closure (an install carries only the skill's own directory) are in tension.
Resolve it with a generic four-layer pipeline — **centralized authority → declarative
consumption → generate-time inlining → runtime reads only itself**:

1. A single repo-side authority file (under `docs/`) holds the canonical values and
   declares its own scope: what is shared (a fact a second skill uses to constrain
   its output) vs private (a fact only the owner consumes — e.g. diagnostic codes).
2. Each consuming skill writes a human-authored *declaration* in its `SKILL.md`:
   which shared keys it `consumes`, plus its own `extensions` terms that must never
   leak into the shared source or another skill's block.
3. A build-time generator inlines the consumed slice into a delimited, generated
   block *inside each skill's own files*, so it ships with the install. The
   declaration is hand-edited; the block is machine-written and never hand-edited.
4. At runtime the skill reads only its own inlined block — never `docs/`, never a
   sibling skill. A missing or malformed block fails loud with no hardcoded fallback
   (a silent fallback is exactly the "enum still in force" fake-green this avoids).

Enforce mechanically: byte-equal re-render (block == fresh generator output),
closed-schema (no extension leaks), and a canary (inject a value into the source and
prove the consumer's behavior flips, confirming it reads the block not a hardcoded
enum). The rule: **copy at build-time, never reference at runtime.**

This shape is for facts a skill *acts on*. For a fact a skill only *cites* (an
argument or authority claim it does not enforce), do not inline an unguarded copy —
address it by `authority-id` (a named reference the doc-map can resolve) rather than
a cross-directory path, or inline the full quote with a provenance note. Read
`docs/skill-conventions/` (+ `scripts/generate-shared-conventions.py`,
`scripts/check-shared-conventions.py`) as a worked instance of this pattern.

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
