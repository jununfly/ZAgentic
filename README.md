# ZAgentic Skills

[![skills.sh](https://skills.sh/b/jununfly/ZAgentic)](https://skills.sh/jununfly/ZAgentic)

ZAgentic is a collection of composable skills for human-guided engineering,
codebase documentation, research, and everyday agent workflows. Public skills
live in five purpose-based buckets under `skills/`; setup-specific skills live
in root-level `personal/` and are deliberately excluded from this catalog.

Start with [`/zj-guide`](./skills/engineering/zj-guide/SKILL.md) when you do
not know which route fits your situation.

## Quick start

Install selected public skills through skills.sh:

```bash
npx skills@latest add jununfly/ZAgentic
```

Then choose the entry point that matches the repository's state:

- Use [`/zj-docs-ontology`](./skills/codebase-docs/zj-docs-ontology/SKILL.md)
  to establish, migrate, or govern a documentation system, including when no
  document map has been selected.
- Use [`/zj-repo-init`](./skills/engineering/zj-repo-init/SKILL.md) after a
  document map is selected to configure tracker, triage vocabulary, and concise
  Agent entrypoints.
- Use [`/zj-guide`](./skills/engineering/zj-guide/SKILL.md) for every other
  route, including implementation, research, maintenance, and standalone work.

## Local installation

From a local clone, [`scripts/link-skills.sh`](./scripts/link-skills.sh)
installs every public and personal skill into detected supported agent skill
directories:

| Platform | Skill directory |
| --- | --- |
| `claude` | `~/.claude/skills` |
| `codex` | `~/.codex/skills` |
| `workbuddy` | `~/.workbuddy/skills` |

```bash
# Install into every detected platform.
scripts/link-skills.sh

# Limit installation and preview it first.
scripts/link-skills.sh --platform codex --dry-run

# Copy is the default snapshot; symlink keeps a local checkout live.
scripts/link-skills.sh --platform codex --method copy
scripts/link-skills.sh --platform codex --method symlink
```

The installer replaces a same-named target skill folder; use `--dry-run` before
overwriting an existing installation. Reload WorkBuddy plugins (or restart it)
after installation so its scanner sees the new skills.

### Refresh or remove a local installation

[`scripts/zagentic-skills-list`](./scripts/zagentic-skills-list) is the
generated inventory for uninstalling the locally installed collection. Regenerate
it after adding or removing a public or personal skill:

```bash
scripts/list-skills.sh > scripts/zagentic-skills-list
```

Review that inventory before removing the matching directories from an agent's
skills folder. The installer itself only installs or replaces skills.

### Validate the repository layout

Run the validation entry point before distributing a local clone:

```bash
scripts/validate-plugin.sh
```

It runs the official plugin validator first. If that validator is unavailable
or returns non-zero, it runs ZAgentic's recursive layout validator, which checks
the five public buckets, root-level `personal/`, skill frontmatter, README
registration, and public coverage in `zj-guide`.

## Recommended paths

- **Documentation system** — `/zj-docs-ontology` discovers and proposes;
  `/zj-docs-architecture` owns architecture views. Migrations and deletions
  require explicit Human confirmation.
- **Feature delivery** — use `/zj-grill-with-docs` or `/zj-grilling` to align,
  then `/zj-to-spec` → `/zj-to-tickets` → `/zj-implement` as the work needs.
  `/zj-steelman`, `/zj-dry-run`, and `/zj-debrief` are the pre-plan,
  pre-implementation, and post-task checkpoints.
- **Long-running uncertainty** — `/zj-wayfinder` carries decisions and
  blockers until the work is ready for a spec and tickets; `/zj-roadmap-driven`
  tracks an agreed execution route.
- **Research and design** — `/zj-research` produces evidence,
  `/zj-code-research` maps a repository, `/zj-tech-research-report` makes a
  technical recommendation, and `/zj-tech-design-review` tests a proposed
  design.
- **Closeout** — `/zj-debrief` records process material after work;
  `/zj-docs-ontology` later governs durable extraction and proposed deletion.
  `/zj-neat-freak` reconciles broader docs, rules, memory, and workspace drift.

## Public skills

### Engineering

- [zj-guide](./skills/engineering/zj-guide/SKILL.md) — Route a request to the skill or flow that fits it.
- [zj-diagnosing-bugs](./skills/engineering/zj-diagnosing-bugs/SKILL.md) — Diagnose hard bugs and performance regressions through a disciplined feedback loop.
- [zj-triage](./skills/engineering/zj-triage/SKILL.md) — Move incoming issues through explicit triage roles.
- [zj-codebase-design](./skills/engineering/zj-codebase-design/SKILL.md) — Design deeper modules, clear seams, and small interfaces.
- [zj-git-bypass-safe-delete](./skills/engineering/zj-git-bypass-safe-delete/SKILL.md) — Diagnose and recover from WorkBuddy safe-delete Git corruption.
- [zj-steelman](./skills/engineering/zj-steelman/SKILL.md) — Reality-check a plan before grilling it.
- [zj-dry-run](./skills/engineering/zj-dry-run/SKILL.md) — Rehearse a ticketed plan before implementation.
- [zj-implement](./skills/engineering/zj-implement/SKILL.md) — Implement a spec or ticket with TDD and review checkpoints.
- [zj-improve-codebase-architecture](./skills/engineering/zj-improve-codebase-architecture/SKILL.md) — Find codebase-deepening opportunities and turn a chosen one into work.
- [zj-merge-skill-pair](./skills/engineering/zj-merge-skill-pair/SKILL.md) — Execute one approved skill-pair merge as an atomic commit.
- [zj-merge-skills-wave](./skills/engineering/zj-merge-skills-wave/SKILL.md) — Plan a multi-skill merge wave from another collection.
- [zj-resolving-merge-conflicts](./skills/engineering/zj-resolving-merge-conflicts/SKILL.md) — Resolve an in-progress merge or rebase by each side's intent.
- [zj-leader](./skills/engineering/zj-leader/SKILL.md) — Turn a one-line idea into an agent-runnable `/goal` brief.
- [zj-repo-init](./skills/engineering/zj-repo-init/SKILL.md) — Configure tracker, triage vocabulary, and Agent entrypoints after a document map is selected.
- [zj-tdd](./skills/engineering/zj-tdd/SKILL.md) — Build a feature or fix test-first with red-green-refactor.
- [zj-wizard](./skills/engineering/zj-wizard/SKILL.md) — Generate a guided Bash workflow for steps only a Human can perform.
- [zj-code-review](./skills/engineering/zj-code-review/SKILL.md) — Review a change against repository standards and its originating spec.
- [zj-tech-design-review](./skills/engineering/zj-tech-design-review/SKILL.md) — Review a technical design from framing through rollout and validation.
- [zj-to-tickets](./skills/engineering/zj-to-tickets/SKILL.md) — Slice a plan or spec into blocking-aware tracer-bullet tickets.
- [zj-to-spec](./skills/engineering/zj-to-spec/SKILL.md) — Turn the current conversation into a spec and issue.
- [zj-prototype](./skills/engineering/zj-prototype/SKILL.md) — Build a throwaway prototype to answer a design question.

### Codebase Docs

- [zj-docs-architecture](./skills/codebase-docs/zj-docs-architecture/SKILL.md) — Maintain and validate complementary architecture handbook views.
- [zj-docs-ontology](./skills/codebase-docs/zj-docs-ontology/SKILL.md) — Discover, govern, validate, and report on one codebase's documentation system.
- [zj-debrief](./skills/codebase-docs/zj-debrief/SKILL.md) — Close out a task as process material and route durable conclusions for later synthesis.
- [zj-domain-modeling](./skills/codebase-docs/zj-domain-modeling/SKILL.md) — Maintain a project's domain language and glossary.
- [zj-grill-with-docs](./skills/codebase-docs/zj-grill-with-docs/SKILL.md) — Conduct repository-aware grilling with documentation updates.
- [zj-neat-freak](./skills/codebase-docs/zj-neat-freak/SKILL.md) — Reconcile codebase knowledge and governance drift.
- [zj-roadmap-driven](./skills/codebase-docs/zj-roadmap-driven/SKILL.md) — Maintain a decision-carrying execution roadmap.
- [zj-wayfinder](./skills/codebase-docs/zj-wayfinder/SKILL.md) — Maintain a shared map of large-work planning decisions.

### Productivity

- [zj-caveman](./skills/productivity/zj-caveman/SKILL.md) — Switch to ultra-compressed communication mode.
- [zj-grilling](./skills/productivity/zj-grilling/SKILL.md) — Stress-test a plan, decision, or idea through structured questions.
- [zj-handoff](./skills/productivity/zj-handoff/SKILL.md) — Create a compact handoff for another human or agent.
- [zj-wait-what](./skills/productivity/zj-wait-what/SKILL.md) — Re-pitch the last message when it did not land.
- [zj-write-a-skill](./skills/productivity/zj-write-a-skill/SKILL.md) — Create a skill with progressive disclosure and bundled resources.
- [zj-writing-for-agents](./skills/productivity/zj-writing-for-agents/SKILL.md) — Write skills, rules, and agent-consumed documents clearly.
- [zj-teach](./skills/productivity/zj-teach/SKILL.md) — Teach a concept across multiple sessions in a stateful workspace.
- [zj-to-questionnaire](./skills/productivity/zj-to-questionnaire/SKILL.md) — Turn an unresolved decision into a questionnaire for another person.

### Misc

- [zj-git-guardrails-claude-code](./skills/misc/zj-git-guardrails-claude-code/SKILL.md) — Add Claude Code hooks that block dangerous Git operations.
- [zj-migrate-to-shoehorn](./skills/misc/zj-migrate-to-shoehorn/SKILL.md) — Migrate test assertions to `@total-typescript/shoehorn`.
- [zj-scaffold-exercises](./skills/misc/zj-scaffold-exercises/SKILL.md) — Scaffold lintable exercises, problems, solutions, and explainers.
- [zj-setup-pre-commit](./skills/misc/zj-setup-pre-commit/SKILL.md) — Set up Husky, lint-staged, type checks, and tests at commit time.
- [zj-aihot](./skills/misc/zj-aihot/SKILL.md) — Retrieve current Chinese AI news and highlights from AIHOT's read-only API.
- [zj-storage-analyzer](./skills/misc/zj-storage-analyzer/SKILL.md) — Analyze macOS or Windows storage usage and produce an actionable cleanup report.

### Research

- [zj-research](./skills/research/zj-research/SKILL.md) — Produce cited primary-source findings or a sealed evidence ledger.
- [zj-code-research](./skills/research/zj-code-research/SKILL.md) — Build a commit-scoped repository map and bounded architecture study.
- [zj-tech-research-report](./skills/research/zj-tech-research-report/SKILL.md) — Turn findings and sealed ledgers into a technical-solution research report.
- [zj-systematic-research](./skills/research/zj-systematic-research/SKILL.md) — Systematically study a product, company, concept, technology, or person.
