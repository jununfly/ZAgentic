---
name: zj-triage-a-only
description: ZAgentic-only triage rules. Read this when triaging PRs in the ZAgentic repo, on top of the B triage flow.
---

# A-only PR flag rules (ZAgentic)

These three rules extend the B triage PR handling for the ZAgentic repository. They are not in the B original — they cover ZAgentic-specific project invariants that B does not have to worry about.

Read this file **before** triaging any PR. If the PR touches `skills/` or `docs/`, all three rules apply. If the PR only touches a single `.md` outside those paths, the rules still apply but at lower strictness (note them, don't reject).

## Rule 1 — `skills/` diff must be paired with `.codex-plugin/plugin.json`

**Source:** `AGENTS.md` — "Every skill in `engineering/`, `productivity/`, or `misc/` must have a reference in the top-level `README.md` and an entry in `.codex-plugin/plugin.json`."

**Check:** if the PR diff contains any of:
- new directory under `skills/<bucket>/<name>/` with `SKILL.md` → must add an entry in `.codex-plugin/plugin.json` `skills` array
- deleted directory under `skills/<bucket>/<name>/` → must remove its entry
- renamed directory (git rename detection) → must update the entry's `path`
- changed bucket (`engineering/` ↔ `productivity/`) → must update the entry

**Outcome if missing:** wontfix (`enhancement` if reasoning is documented) + comment listing missing entries + ask author to run `/zj-agents-init` to fix.

**Note:** do **not** accept the PR on the promise that the author will fix it later — that's how marketplace publishing breaks silently.

## Rule 2 — git operations must use `./scripts/zj-git`

**Source:** `MEMORY.md` (user-level) + `skills/engineering/zj-git-bypass-safe-delete/SKILL.md` — the WorkBuddy `genie-safe-delete.cjs` shim corrupts `.git/` state on Windows Git Bash; bare `rm -rf` or `git` invocations under the shim can destroy refs.

**Check:** if the PR introduces or modifies:
- shell scripts that call `rm`, `rm -rf`, `git commit`, `git fetch`, `git pull`, `git stash`, `git rebase`, `git branch -D`, `git reset`
- CI workflows doing the above
- documentation saying "just run `rm ...`" or "just run `git ...`"

Then the script or doc must either:

- use `./scripts/zj-git` (in-repo wrapper that strips `NODE_OPTIONS` before exec), **or**
- explicitly call out the shim and document the safe pattern

**Outcome if missing:** wontfix (`enhancement`) + cite the memory rule + ask author to use the wrapper or update the doc.

**Workaround for `rm`:** use `mv <target> <backup>/` instead of `rm -rf`. If the user explicitly asks for `rm`, escalate first; the shim makes it destructive on this host.

## Rule 3 — new terms must update `ZJ-CONTEXT.md` before merge

**Source:** ZAgentic's `ZJ-CONTEXT.md` is the project glossary that all downstream skills (`/zj-grilling`, `/zj-domain-modeling`, `/zj-teach`, `/zj-grill-me`, `/zj-grill-with-docs`) read to align vocabulary. Drift here breaks every cross-session reference.

**Check:** if the PR introduces any of:
- a new domain concept (noun not yet in ZJ-CONTEXT.md)
- a new acronym / abbreviation used in ≥2 skills
- a renamed / re-purposed existing term
- a new bucket of work (e.g. new stage in roadmap)

Then the PR must also include a `ZJ-CONTEXT.md` diff adding the term under the right section.

**Outcome if missing:** wontfix (`enhancement`) — the PR is not ready to merge even if code is correct.

**Workflow to fix:** author runs `/zj-domain-modeling` to surface the new term, adds it to the right section, commits the ZJ-CONTEXT.md diff in the same PR.

## Priority

All three rules are hard requirements, not preferences. PRs that pass B's flow but fail any of these are wontfix until fixed. Triage output must call out which rule(s) tripped.

## What is *not* covered here

- **WorkBuddy mcp tools** (70+ connectors like agent-mail / mcp__weixinpay / mcp__sheetagent) — triage should be aware they exist but doesn't need to refuse PRs that ignore them. Note in the brief; let the maintainer decide.
- **Roadmap JSON edits** — that's governed by `roadmap_cli.py`; if a PR touches a roadmap JSON (`docs/plans/roadmap-*.json`), note that `roadmap_cli.py` should be used (mention, don't reject).
- **Personal/ bucket skills** — `personal/` skills don't appear in `plugin.json` per `AGENTS.md`; Rule 1 doesn't apply to them. But Rule 2 and Rule 3 still do.
