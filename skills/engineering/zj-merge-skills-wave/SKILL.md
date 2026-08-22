---
name: zj-merge-skills-wave
description: >-
  Plan a multi-skill merge wave from a source skills collection (local path or github URL) into this repo. Discovers source skills, compares to base, produces a skill-pair plan as a roadmap tree, and routes each pair to zj-merge-skill-pair for execution. Use when you want to absorb/borrow skills from an upstream skills collection, another skills collection, or any directory of SKILL.md files. Triggers on "merge skills from", "absorb from source-name", "import skills from". Pair: zj-merge-skill-pair executes one pair; this one plans a whole wave.
disable-model-invocation: true
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
- Tracking merged skills' state → use `zj-roadmap-driven`

## Pair-planning reference

Before comparing candidates or proposing a merge strategy, read the [skill-pair forms and strategy reference](references/pair-planning.md).

## Source preservation gate

When a candidate comes from an open-source skills collection, preserve its
source instructions by default. During comparison, distinguish mechanical
conformance work (valid YAML, `zj-` naming, indexes, registrations) from a
change to the source skill's logic or semantics. If an improvement would
rewrite logic or meaning and the source has no concrete error or omission,
stop and route that proposed change through `/zj-grilling` before putting it
in a merge strategy. Record the agreed change in the roadmap decision.

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

Use the forms and strategy enum in the [pair-planning reference](references/pair-planning.md), then record one strategy as a roadmap decision for each pair.

### 6. Lay out as roadmap tree

For each skill-pair, create a roadmap node under the appropriate parent (e.g. `1-4-x` for B-unique, `1-3-x` for A↔B pairs). The decision (strategy + reasoning) goes into the node's `decisions` list via `zj-roadmap-driven`'s `decide` command.

This is the **handoff point** to `zj-roadmap-driven`. The plan IS a roadmap subtree.

### 7. Hand off to zj-merge-skill-pair

For each skill-pair node, the human invokes `zj-merge-skill-pair` (or this skill calls it on their behalf once approved) to execute the merge against the roadmap node. The execution reads the `decisions` recorded in step 6.

## Relationship to other skills

```
zj-merge-skills-wave  (this skill — plan layer for a whole wave)
   ├─ uses zj-grilling        for strategy decisions (absorb vs adopt vs strict-align)
   ├─ uses zj-roadmap-driven  for plan layout (each pair = 1 node + N decisions)
   └─ calls zj-merge-skill-pair   for execution (per skill-pair)
```

Do NOT conflate with:
- `zj-grilling` — decision helper, not a plan layer
- `zj-roadmap-driven` — state tracker, not a merger
- `zj-merge-skill-pair` — execution unit, not planning

## Files this skill touches (planning only)

- `source-skills-list` (transient report — no commit)
- `base-skills-list` (transient report — no commit)
- `docs/plans/roadmap-<wave>.json` (the per-wave plan, persisted via zj-roadmap-driven; e.g. `roadmap-khazix-wave.json` — past waves live in git history after close-out)

## Output

A roadmap subtree where every node has:
- `label` describing the skill-pair
- `decisions` containing the strategy + reasoning
- `notes` pointing to source paths and the base path

Ready for `zj-merge-skill-pair` to consume one node at a time.
