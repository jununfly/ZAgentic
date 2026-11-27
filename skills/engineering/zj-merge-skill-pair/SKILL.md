---
name: zj-merge-skill-pair
description: Execute a single skill-pair merge as one atomic commit. Reads the strategy from a zj-dp-driven task's decision record (context-md), applies 12 classes of side effects (skill files, README sync, bucket README, setup-skills templates, ZJ-CONTEXT.md, ADR cross-refs, git mv for renames, deletion of replaced skills), closes the pair's ticket, and commits. Triggers on "merge this skill", "execute the plan for X", "absorb B into A". Pair with zj-merge-skills-wave — that one plans a whole wave, this one executes one pair.
disable-model-invocation: true
source: zagentic

---

# Merge One Skill-Pair

Execute a single skill-pair merge as **one atomic commit**. This skill is the **execution unit** that `zj-merge-skills-wave` delegates to.

## Pre-condition

A zj-dp-driven carrier must already exist with a task whose context-md contains a `## Decision` entry recording:
- the strategy (`strict-align` / `absorb` / `adopt` / `replace` / `reject`)
- the source path (or URL → scratch path)
- the base path (or `null` if source is new to base)

If no carrier/task exists, route to `zj-merge-skills-wave` first.

## Side-effect checklist

Before writing the file-level plan, read the [side-effect checklist](references/side-effects.md). A correct merge touches **whichever subset is in scope**, never just `SKILL.md`.

## Source preservation gate

For an open-source source skill, keep the source body intact by default. YAML,
name/path coupling, index, and registration repairs are mechanical and may be
applied during the merge. If the execution plan would rewrite the source
skill's logic or semantics without a concrete error or omission, stop before
editing and route the proposed change through `/zj-grilling`; continue only
after the Human's agreed change is recorded in the task's decision entry.

**Read the source dir tree first**. If `git ls-tree` on the source shows N files, plan all N, not just SKILL.md.

## Process

### 1. Resolve strategy

Read the task's context-md `## Decision` entry. The strategy MUST be one of:
- `strict-align` — copy source files, change `name` to `zj-<basename>` only
- `absorb` — keep base, cherry-pick from source (changes are surgical, listed in decision note)
- `adopt` — rename base skill to source's name; body is source verbatim
- `replace` — delete base, install source as new
- `reject` — record decision, do nothing else, close the pair's ticket and task (step 7)

If the strategy is `reject`, the entire merge reduces to step 7 (close the ticket and the task).

### 2. File-level plan

Using the side-effect checklist, list every file that will change. Show the list to the human and get confirmation before touching anything. This is the **only** human-in-the-loop checkpoint inside one merge.

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
feat(<bucket>): <strategy> <dst> — <one-line summary> (dp-driven task <task-id>)

- side effect 1
- side effect 2
- ...

ZJ-CONTEXT.md entry: <term or N/A>
ADR cross-ref: <id or N/A>
```

Push only on explicit human request. Default: leave committed locally.

### 7. Close the ticket and the task

After the human confirms the commit, record completion in the dp-driven carrier (two steps — task status is NOT auto-derived from ticket status, both must be set explicitly):

```
python3 <zj-dp-driven-skill-dir>/scripts/dp_driven_cli.py ticket status <db> <ticket-id> --set 已完成 --agent <agent>
python3 <zj-dp-driven-skill-dir>/scripts/dp_driven_cli.py task status <db> <task-id> --set 已完成
```

The `<ticket-id>` and `<task-id>` come from the wave planner's step 6 (ids are printed at creation, 0-based); if they were not recorded, look them up in the carrier before closing. The pair is done when its ticket reaches a terminal state **and** the task is set to `已完成`.

## When to abort

- The strategy decision is missing or ambiguous → stop, ask human
- The source has more files than the decision note enumerates (e.g. 5 sub-files when decision said "just SKILL.md") → stop, ask human
- The cross-reference grep finds 10+ files that need updating → stop, ask human
- A `ZJ-CONTEXT.md` term change conflicts with an existing `_Avoid_` rule → stop, ask human

## Relationship

```
zj-merge-skills-wave  (plan layer for a whole wave)
   └─ produces dp-driven tasks with Decision entries ─→ zj-merge-skill-pair (this skill, execution)
                                   ├─ reads the task's Decision
                                   ├─ executes 12 side effects
                                   └─ closes the pair's ticket after human confirmation
```

The complete per-merge touch list is maintained in the [side-effect checklist](references/side-effects.md).
