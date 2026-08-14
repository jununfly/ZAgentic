---
name: zj-debrief
description: Reflect on a finished task — walk through drift, surface new concepts, and capture concrete actions to do better next time. Use when a task wraps up and you want to close the loop with the planning step, not as a generic post-mortem or notes dump. User-invoked.
disable-model-invocation: true
---

# zj-debrief

A short, structured close-out for a finished task. Reads the prior `/zj-grilling` output (if any) as the plan baseline, walks the actual path you took, surfaces any new domain terms, and writes one retro entry per task into `docs/zj-retros/YYYY-MM-DD-retro.md` plus a 7-slot pointer index in `ZJ-CONTEXT.md` (Retros section).

## Quick start

```
/zj-debrief
```

The skill reads the prior grilling output (if any), today's retro file, and the Retros pointer index in `ZJ-CONTEXT.md`, then walks the three steps below.

## Workflow

### Step 1 — Drift walkthrough

Compare what you planned to do (from the most recent `/zj-grilling` output) against what you actually did. Record divergences in a 4-column table: **Plan / Actual / Drift / Verdict** (acceptable / needs adjustment). If no grilling output exists, **skip this step entirely** — don't fabricate a baseline. The other two steps still run.

### Step 2 — Concept extraction

Invoke `/zj-domain-modeling` to surface any new domain terms, metaphors, or renamed concepts that emerged during the task. Add them to the relevant section of `ZJ-CONTEXT.md` (Language / Issue-Triage / etc.). Rule 3 of the triage A-only policy already forces this on PRs that introduce new terms; debrief is its batch, after-the-fact form.

### Step 3 — Actions

Write 1-3 concrete "next time, do this" actions in the retro file. The Retros pointer index in `ZJ-CONTEXT.md` (see template below) is the agent's morning-reading path: it shows the active actions without opening any retro file. Capped at 7 entries, with `🔄` pinning the ones that recurred across multiple tasks.

## Outputs

**Two writes per invocation, in this order:**

1. `docs/zj-retros/YYYY-MM-DD-retro.md` — append a new H2 section (with timestamp, e.g. `## 14:30`) containing Drift / Concepts / Actions sub-headings. The file is permanent history; git tracks it.
2. `ZJ-CONTEXT.md` → `## Retros` section — update the pointer index. Remove any pointer whose Action is now done; append new pointers; if the index exceeds 7, drop the oldest non-`🔄` entry. The `🔄` tag marks actions that have recurred and stay pinned at the top.

## Retro section template

```markdown
## HH:MM — Task: <one-line summary>

**计划基线**: /zj-grilling 产出 — <one sentence>  (or "无 /zj-grilling 产出 → drift 步骤跳过")

### Drift

| 计划 | 实际 | 偏差 |
|------|------|------|
| ... | ... | ... |

**Drift 判定**: <可接受 / 需调整>  <reason>

### Concepts

调 /zj-domain-modeling 提取本次工作新出现的概念：

- **<term>** — <one-line def>  (write into ZJ-CONTEXT.md too)

### Actions

- ⚠️ <one specific thing to do differently next time>
```

## Retros pointer index template (in ZJ-CONTEXT.md)

```markdown
## Retros

🔄 <action that recurs>  — docs/zj-retros/YYYY-MM-DD.md#HH:MM
- <active action 1>  — docs/zj-retros/YYYY-MM-DD.md#HH:MM
- <active action 2>  — docs/zj-retros/YYYY-MM-DD.md#HH:MM
- ...

(cap: 7 entries. Done actions removed. Recurring actions pinned with 🔄 at the top.)
```

## Trigger

User-invoked, at the end of each task. Lightweight by design: the goal is to make closing the loop cheaper than skipping it. Most invocations should complete in under 5 minutes; if a single task warrants more, split the task rather than expand the retro.

## See also

- `/zj-grilling` — the front half of the loop. Provides the drift baseline.
- `/zj-domain-modeling` — invoked from Step 2 to extract new concepts.
- `/zj-handoff` — for transferring the current session to a fresh agent. Different goal: handoff is forward transfer; debrief is knowledge sink.
