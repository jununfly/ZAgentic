---
name: zj-merge-skill-pair
description: Execute a single skill-pair merge as one atomic commit. Reads the strategy from a zj-roadmap-driven node's decisions, applies 12 classes of side effects (skill files, README sync, bucket README, setup-skills templates, ZJ-CONTEXT.md, ADR cross-refs, git mv for renames, deletion of replaced skills), updates the roadmap node to completed, and commits. Triggers on "merge this skill", "execute the plan for X", "absorb B into A". Pair with zj-merge-skills-wave — that one plans a whole wave, this one executes one pair.
disable-model-invocation: true
---

# Merge One Skill-Pair

Execute a single skill-pair merge as **one atomic commit**. This skill is the **execution unit** that `zj-merge-skills-wave` delegates to.

## Pre-condition

A roadmap node must already exist with a `decisions` entry containing:
- the strategy (`strict-align` / `absorb` / `adopt` / `replace` / `reject`)
- the source path (or URL → scratch path)
- the base path (or `null` if source is new to base)

If no node exists, route to `zj-merge-skills-wave` first.

## 12 classes of side effects (must cover all that apply)

Reverse-engineered from 1-3 commits `8fbf5c5` through `a895f47`. A correct merge touches **whichever subset of these is in scope**, never just "the SKILL.md file".

| # | side effect | when to apply |
|---|---|---|
| 1 | Add new skill SKILL.md (verbatim from source) | `adopt`, `replace`, `strict-align` |
| 2 | Add `agents/openai.yaml` if source has it | when B has sidecar |
| 3 | Delete old skill directory | `replace`, `reject` |
| 4 | `git mv` old → new path for renames | `adopt` where A is renamed to B's name |
| 5 | Cross-skill reference updates (other skills' SKILL.md referring to old name) | any name change |
| 6 | Top-level `README.md` skill list update | any add/remove/rename |
| 7 | `skills/engineering/README.md` or `skills/productivity/README.md` update | any add/remove/rename in that bucket |
| 8 | `zj-setup-skills/issue-tracker-*.md` and `domain.md` template update | when hard-dependency list changes |
| 9 | `ZJ-CONTEXT.md` term table update | when new domain terms are introduced or renamed |
| 10 | `docs/zj-adr/*.md` cross-reference update | when ADR text mentions old skill name |
| 11 | Copy supporting source files (CONTEXT-FORMAT.md, ADR-FORMAT.md, sub-skill docs...) | when source dir has them |
| 12 | Delete supporting old files | when old skill had them and they don't survive rename |

**Read the source dir tree first**. If `git ls-tree` on the source shows N files, plan all N, not just SKILL.md.

## Process

### 1. Resolve strategy

Read the roadmap node's `decisions`. The first decision's `answer` MUST be one of:
- `strict-align` — copy source files, change `name` to `zj-<basename>` only
- `absorb` — keep base, cherry-pick from source (changes are surgical, listed in decision note)
- `adopt` — rename base skill to source's name; body is source verbatim
- `replace` — delete base, install source as new
- `reject` — record decision, do nothing else, mark node completed

If the strategy is `reject`, the entire merge reduces to step 7 (update roadmap).

### 2. File-level plan

Using side-effect table above, list every file that will change. Show the list to the human and get confirmation before touching anything. This is the **only** human-in-the-loop checkpoint inside one merge.

### 3. Copy / modify source files

For each source file:
- copy to target path under `skills/<bucket>/zj-<name>/`
- modify frontmatter `name` to `zj-<basename>` (only the `name` field; `display_name` if present)
- modify any internal references that conflict with A's naming

For `absorb`: open base, surgically add features from source per the decision note, do NOT replace wholesale.

### 4. Update bucket and repo metadata

Apply side effects 5–10 in order. Use `grep` to find every cross-reference before changing.

### 5. Delete old skill (if `replace` or `reject`)

`git rm` the old skill directory. The `safe-delete` shim applies — use `scripts/zj-git rm` not plain `rm -rf`.

### 6. Commit (one atomic commit)

One commit per skill-pair. Commit message format:

```
feat(<bucket>): <strategy> <dst> — <one-line summary> (<roadmap-node-id>)

- side effect 1
- side effect 2
- ...

ZJ-CONTEXT.md entry: <term or N/A>
ADR cross-ref: <id or N/A>
```

Push only on explicit human request. Default: leave committed locally.

### 7. Update roadmap

```
scripts/zj-merge-skill-pair completed <roadmap-node-id>
```

This is the human's call. The agent must NOT auto-update — the merge is done but the human owns the roadmap.

## When to abort

- The strategy decision is missing or ambiguous → stop, ask human
- The source has more files than the decision note enumerates (e.g. 5 sub-files when decision said "just SKILL.md") → stop, ask human
- The cross-reference grep finds 10+ files that need updating → stop, ask human
- A `ZJ-CONTEXT.md` term change conflicts with an existing `_Avoid_` rule → stop, ask human

## Relationship

```
zj-merge-skills-wave  (plan layer for a whole wave)
   └─ produces roadmap nodes ─→ zj-merge-skill-pair (this skill, execution)
                                  ├─ reads decision
                                  ├─ executes 12 side effects
                                  └─ leaves roadmap update to human
```

## Files this skill touches (per merge)

- `skills/<bucket>/zj-<name>/...` (the skill body)
- `README.md` (top-level)
- `skills/engineering/README.md` or `skills/productivity/README.md`
- `skills/engineering/zj-setup-skills/issue-tracker-*.md` (if hard-deps changed)
- `skills/engineering/zj-setup-skills/domain.md` (if domain terms changed)
- `ZJ-CONTEXT.md` (if domain terms changed)
- `docs/zj-adr/*.md` (if ADR refs old name)
- `docs/plans/roadmap-skillpairs.json` (when human runs `update` after)

Never touches: scratch dirs, source dirs (read-only), `~/.workbuddy/` (out of repo).
