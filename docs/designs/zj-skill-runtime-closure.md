---
doc-kind: design
authority: primary
authority-id: design.skill-runtime-closure
---

# Skill runtime closure (运行期闭包自包含)

## Question

Skills are published units: they are copied into `~/.codex/skills`,
`~/.workbuddy/skills`, `~/.claude/skills` and run **without the `ZAgentic`
source repo present**. What must hold so an installed skill never breaks because
it reached back into `ZAgentic/docs` at runtime?

## Scope

This page is a **repo-level skill-authoring convention** for the `ZAgentic`
source repo. It governs how *we* write skills here. It is deliberately **not**
part of `zj-docs-ontology` (the portable Module G), because that skill must stay
installable into *any* repo — embedding a ZAgentic-specific closure rule would
break its portability and is a category error (skill-authoring hygiene vs
documentation governance). The companion guardrail is
[`scripts/check-skill-runtime-closure.py`](../../scripts/check-skill-runtime-closure.py).

## Rule

**A skill is a self-contained published unit. Everything it reads at runtime
must live inside its own directory (`SKILL.md`, `references/`, `scripts/`).**

- "At runtime" = any file the skill `open()`s in `scripts/`, or any file its
  `SKILL.md` / `references/` instruct the Agent to follow.
- `ZAgentic/docs/` is the **source repo's meta-knowledge layer** (ADRs,
  architecture, roadmap, the ontology system itself). It is *not* a dependency of
  the published artifact and is absent wherever the skill is installed.
- The `docs/` tree is for ZAgentic maintainers and humans, not for shipped skill
  logic. Do not migrate project meta-docs into a skill just to satisfy a link.

## Three derived lessons

### 1. Source-repo docs must not be a runtime dependency — but target-repo docs reads are fine

The distinction is **which repo's `docs/`** the skill touches:

- ❌ **Bad** — a skill references the *ZAgentic source* `docs/` via a relative
  escape (`../../../docs/...`) or a ZAgentic-specific path (`docs/ontology/...`).
  Those resolve to a non-existent location once the skill is installed elsewhere.
- ✅ **Fine** — a skill operates on the *repo it is currently running in* (the
  cwd / target). `zj-docs-ontology`, `zj-docs-architecture`, `zj-domain-modeling`,
  `zj-code-review`, `zj-repo-init` all legitimately *create or read* a target
  repo's `docs/zj-adr`, `docs/agreements/agent-workflow/*`, `docs/architecture`.
  That is the skill's job; it uses bare `docs/...` relative to the target root,
  never an upward escape out of the skill.

Rule of thumb: a *bare* `docs/...` (no `../` prefix) in a skill usually means
"the target repo's docs" and is intended. A `../`-prefixed `docs/...` means "my
source repo's docs" and is a closure violation.

### 2. Cross-cutting SSOT docs must not be moved into a single skill

A doc that is referenced by *many* pages across the repo (e.g.
`docs/agreements/open-source-capability-fit-decision-model.md`, referenced by
`zj-discuss`, `zj-composer`, `ui-agent-skills`, `ZJ-CONTEXT.md`, the doc-map)
is a **repo-level protocol**, not one skill's spec.

- Do **not** copy it into one skill's `references/`. That fragments the single
  source of truth and breaks every other page that links to it.
- Do **not** assume the skill's runtime logic reads it. In the
  `zj-open-source-capability-fit` case the decision logic is *hardcoded* in
  `capability_fit.py`; the script never `open()`s the SSOT at runtime.
- The correct fix for a skill that mentions such a doc is to make the pointer
  **honest**: state that the doc is source-repo-only and not installed with the
  skill, and remove the dead relative link. No content migration.

### 3. The scan must use precise fingerprints, not a broad string match

A naive "flag every `ZAgentic` mention" is wrong — it false-positives on brand
strings (`User-Agent: ZAgentic-zj-research`), target-repo operations, and
intentional "run this skill inside the ZAgentic repo" rules (`zj-triage/A-ONLY.md`,
`zj-git`). The guardrail uses only these high-signal patterns:

- `(?:\.\./){1,}docs` — relative escape **upward** out of the skill into a repo
  `docs/` (the exact signature of our real violations).
- `docs/ontology` — the ZAgentic-specific ontology path (not a generic target
  path).
- absolute source paths (`/Users/.../ZAgentic/`, `/home/.../jununfly/`, `C:\...`)
  as an advisory "review" signal.

It scans `skills/` (excluding `tests/`, `fixtures/`, `artifacts/`,
`__pycache__`, `evals/`, binaries) and supports an inline `# closure-allow`
suppression for documented exceptions. See the script for the authoritative
pattern list.

## Enforcement

- This rule is stated once in `AGENTS.md` (repo-level discipline).
- `scripts/check-skill-runtime-closure.py` is the mechanical gate. Run it in CI
  or pre-commit **without** a `paths` filter (a path-filtered required check
  would block every PR that does not touch `skills/` — see the ui-skills gate
  post-mortem). If gating, make the job report success on a no-op diff rather
  than skipping.
- Treat an ERROR from the script as a merge blocker; WARN is advisory review.
