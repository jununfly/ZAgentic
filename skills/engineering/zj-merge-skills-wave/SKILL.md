---
name: zj-merge-skills-wave
description: >-
  Plan a multi-skill merge wave from a source skills collection (local path or github URL) into this repo. Discovers source skills, compares to base, produces a skill-pair plan as zj-dp-driven tasks (one task per pair, strategy recorded in the task's context-md Decision entry), and routes each pair to zj-merge-skill-pair for execution. Use when you want to absorb/borrow skills from an upstream skills collection, another skills collection, or any directory of SKILL.md files. Triggers on "merge skills from", "absorb from source-name", "import skills from". Pair: zj-merge-skill-pair executes one pair; this one plans a whole wave.
disable-model-invocation: true
source: zagentic

---

# Merge Skills From a Source Collection (Wave Planner)

Plan and orchestrate a **whole wave** of skill merges into this repo's `skills/` tree. Each individual skill-pair execution is delegated to `zj-merge-skill-pair`; this skill only handles **discovery, comparison, and plan layout** for an entire wave.

## When to use

- You want to absorb skills from another skills collection (for example, an upstream collection) into this repo
- You have a local directory of `SKILL.md` files you want to merge in
- You're starting a new A↔B skill-pair absorption wave (e.g. "do 1-4-x next")

## When NOT to use

- Merging a single known skill → use `zj-merge-skill-pair` directly
- Comparing two skills to decide strategy → use `zj-grilling`
- Tracking merged skills' state → read the dp-driven carrier (`dp_driven_cli.py status` / `viz`)

## Pair-planning reference

Before comparing candidates or proposing a merge strategy, read the [skill-pair forms and strategy reference](references/pair-planning.md).

## Source preservation gate

When a candidate comes from an open-source skills collection, preserve its
source instructions by default. During comparison, distinguish mechanical
conformance work (valid YAML, `zj-` naming, indexes, registrations) from a
change to the source skill's logic or semantics. If an improvement would
rewrite logic or meaning and the source has no concrete error or omission,
stop and route that proposed change through `/zj-grilling` before putting it
in a merge strategy. Record the agreed change in the pair task's Decision entry.

## Process

### 1. Resolve source

Human provides one of:
- **Local path** (absolute, e.g. `~/.workbuddy/skills/some-collection/`)
- **GitHub URL** (e.g. `https://github.com/your-org/skills`)

If GitHub URL: clone to a scratch dir (e.g. `C:/tmp/skill-source-<random>/`) using `git clone --depth 1 <url> <scratch>`. Clean the scratch dir after the merge is done.

### 2. Discover source skills

Traverse the resolved source directory. For every file matching `**/SKILL.md`, extract:
- `name` (from frontmatter)
- `bucket` (parent dir's first-level under `skills/`, e.g. `engineering/`)
- `relative path` (from source root, for unambiguous identification when names collide)
- `description` (one-line summary from frontmatter)

Write to a `source-skills-list` report. Do NOT dedupe by name — two skills with the same name in different paths are different skills. The path is the disambiguator.

Show the report to the human in a table: `name | bucket | path | description`.

### 3. Discover base skills

Same procedure, but rooted at this repo's `skills/`. Write to `base-skills-list`.

### 4. Human selects scope

Ask the human to choose:
- **Merge all** — every source skill becomes a candidate
- **Merge subset** — human picks by name / bucket
- **Cancel** — stop, no changes

### 5. Plan skill-pairs

For each candidate source skill, compare against `base-skills-list` using name + description similarity. Produce skill-pairs in one of these forms:

Use the forms and strategy enum in the [pair-planning reference](references/pair-planning.md), then record one strategy per pair (step 6).

### 6. Lay out as dp-driven tasks

Initialize the wave's dp-driven carrier (`dp_driven_cli.py init docs/plans/dp-driven/<wave>/...`) and for each skill-pair create one task **plus one execute ticket** on that task:

Set up the CLI variable once (adjust the path to the installed skill location):

```
DP="python3 <zj-dp-driven-skill-dir>/scripts/dp_driven_cli.py"
```

Then per pair:

```
$DP init docs/plans/dp-driven/<wave>/carrier.db --destination docs/plans/dp-driven/<wave>
$DP task add docs/plans/dp-driven/<wave>/carrier.db --name "<strategy> <dst> ← <src>" --context-md docs/plans/dp-driven/<wave>/pairs/<pair>.md
$DP ticket add docs/plans/dp-driven/<wave>/carrier.db --task <task-id>
```

Task ids are 0-based and printed by `task add`; capture the printed `task_id` and the printed `ticket_id` — both are consumed downstream.

Each pair's context-md holds a `## Decision` entry (strategy + reasoning) plus pointers to the source path and base path. This is the **handoff point** to `zj-merge-skill-pair`: the plan IS the set of tasks, and each task's Decision is what execution reads.

### 7. Hand off to zj-merge-skill-pair

For each pair task, the human invokes `zj-merge-skill-pair` (or this skill calls it on their behalf once approved) to execute the merge against that task. The execution reads the `## Decision` recorded in step 6.

## Relationship to other skills

```
zj-merge-skills-wave  (this skill — plan layer for a whole wave)
   ├─ uses zj-grilling        for strategy decisions (absorb vs adopt vs strict-align)
   ├─ uses zj-dp-driven       for plan layout (each pair = 1 task + a Decision entry)
   └─ calls zj-merge-skill-pair   for execution (per skill-pair)
```

Do NOT conflate with:
- `zj-grilling` — decision helper, not a plan layer
- `zj-dp-driven` — orchestration carrier, not a merger
- `zj-merge-skill-pair` — execution unit, not planning

## Files this skill touches (planning only)

- `source-skills-list` (transient report — no commit)
- `base-skills-list` (transient report — no commit)
- `docs/plans/dp-driven/<wave>/` (the per-wave dp-driven carrier + pair context-md corpus, per zj-dp-driven; e.g. `dp-driven/khazix-wave/` — past waves live in git history after close-out)

## Output

A set of dp-driven tasks where every task has:
- `name` describing the skill-pair
- a context-md `## Decision` entry containing the strategy + reasoning
- pointers to source paths and the base path

Ready for `zj-merge-skill-pair` to consume one task at a time.
