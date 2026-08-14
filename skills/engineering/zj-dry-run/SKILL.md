---
name: zj-dry-run
description: Rehearse a plan before you commit to it — walk each ticket in order, flag the friction points you'll hit, and hand the decision log to grilling if the plan needs re-cutting. Use when tickets exist and you want a quick pre-flight check on whether the plan actually runs end-to-end, not as a general "trace through the code" prompt. User-invoked.
disable-model-invocation: true
---

# zj-dry-run

A pre-flight rehearsal of a ticketed plan. Walks the tickets in order, imagines executing each one, and surfaces the friction before you burn real time on it. Friction gets routed back to `/zj-to-spec` or `/zj-to-tickets` (as suggestions, not auto-edits) and the decision log gets routed to `/zj-grilling` for the ones that need a real answer.

## Quick start

```
/zj-dry-run
```

Pass the ticket list as an argument (path to a tickets file, a paste of the ticket titles, or a reference like `from /zj-to-tickets output`). The skill walks the rehearsal inline. No file is written.

## Workflow

### Step 1 — Confirm the ticket set

If no tickets are passed, or the tickets are too coarse to rehearse, say so and stop. Rehearsal needs concrete, ordered, named steps. If `/zj-to-tickets` hasn't been run, point there first.

### Step 2 — Walk each ticket

For each ticket, in order, simulate execution and answer four questions in one pass:

1. **What you actually do** — the concrete moves (read what, change what, run what command, depend on what).
2. **Likely friction** — where this will slow down, break, or surprise you. Mark each with one of: **blocker** (can't proceed without resolving), **ambiguity** (more than one reasonable interpretation), **dependency** (needs another ticket or external state first).
3. **Estimated cost** — rough size: small (under an hour), medium (a few hours), large (a day or more). Don't try to be precise; the goal is to spot the giant tickets, not to budget them.
4. **Worth doing as-is** — yes / recut / defer. Use recut if the friction is severe enough that the ticket boundaries are wrong; defer if external state blocks it.

### Step 3 — Output the decision log

Two inline tables, in this order:

1. **Per-ticket table** — one row per ticket, columns: Ticket | Friction | Cost | Verdict (yes / recut / defer).
2. **Decision bottlenecks** — the ambiguous or blocker items grouped together as questions, ready to feed into `/zj-grilling`. Each is a one-line question, not an essay.

Then a one-line route:

- All "yes" with only small friction → green-light the plan.
- Any "recut" or "blocker" → recommend either re-running `/zj-to-tickets` (with the friction list as input) or invoking `/zj-grilling` on the specific bottleneck.
- Any "defer" → just flag it; don't try to unblock external state from here.

## Output

**Single inline print.** No file is written. The friction table and decision log are process artifacts — useful for the next planning conversation, not as a permanent record. If you want to keep them, paste them into a handoff doc or a planning note yourself.

The skill does **not** auto-edit `/zj-to-spec` or `/zj-to-tickets` output, even if the friction list would let it. Auto-edits from a rehearsal risk baking rehearsal noise into the source spec. Suggestions only.

## Trigger

User-invoked, after `/zj-to-tickets` has produced an ordered ticket set and before `/zj-implement` starts running them. The point is to catch the giant tickets and the boundary mistakes while they're still cheap to change. One pass by design: if the plan needs more than one rehearsal, the plan probably needs to be re-cut rather than rehearsed again.

## See also

- `/zj-to-tickets` — produces the ticket set this skill rehearses. If dry-run finds recut-worthy friction, route back here.
- `/zj-to-spec` — produces the spec tickets are cut from. If dry-run finds the spec itself is wrong, route back here (suggestion, not auto-edit).
- `/zj-grilling` — picks up the decision bottlenecks dry-run surfaces. The friction list is the grilling queue.
- `/zj-triage` — runs later, at PR time. Dry-run is mid-plan, triage is end-of-plan.
- `/zj-implement` — runs the tickets. Dry-run is the gate before implement starts.
- `/zj-steelman` — checks whether the plan is defensible in theory. Dry-run checks whether it actually runs in practice. Different mental model: argue vs execute.
