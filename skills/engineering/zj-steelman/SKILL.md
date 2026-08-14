---
name: zj-steelman
description: Steelman a proposal before you let it get torn down — extract its core assumptions, write the strongest case for each, judge how strong that case actually is, and route to grilling only if it fails. Use when you have a plan or decision in front of you and want a quick reality check on whether it's worth defending, not as a generic "argue both sides" prompt. User-invoked.
disable-model-invocation: true
---

# zj-steelman

A fast, one-shot reality check on a plan: assume the plan is worth defending, find its strongest case, and judge whether that case holds. If it does, the plan moves forward. If it doesn't, route to `/zj-grilling` — don't try to fix it from here.

## Quick start

```
/zj-steelman
```

Pass the proposal as an argument (or paste it after invoking). The skill runs the four steps below in a single pass and prints the result inline. No file is written.

## Workflow

### Step 1 — List the core assumptions

Pull out the 2–5 assumptions the proposal leans on. If you can't name them, the proposal isn't concrete enough for steelmanning — say so and stop. (Don't fabricate assumptions to fill the slot.)

### Step 2 — Write the strongest case for each

For each assumption, write the **strongest** support you can: a real argument, with the strongest evidence you actually have. Steelmanning means you argue for the plan, not against it. If the strongest case requires a stretch or a hand-wave, note that explicitly — don't paper over it.

### Step 3 — Judge how strong the case actually is

For each assumption, label the case as **Strong / Adequate / Weak**. Strong = would convince a skeptic who isn't invested. Weak = the case only holds if you already believe the conclusion.

### Step 4 — Route

- All Strong or Adequate → the plan has a defensible floor. Print a one-line green-light summary.
- Any Weak → don't try to fix the weak spot from here. Print a one-line recommendation to invoke `/zj-grilling` on the specific weak assumption, then stop. (Grilling and steelmanning have opposite mental models — attack vs defend. Mixing them in one skill makes the agent role-confused; routing is cleaner than merging.)

## Output

**Single inline print, in this order:**

1. **Assumptions** — 2–5 bullets, one per assumption
2. **Strongest case** — for each assumption, the strongest support you can give (with a one-line note if it required a stretch)
3. **Verdict** — Strong / Adequate / Weak per assumption, in the same order
4. **Route** — green-light summary, **or** a one-line recommendation to invoke `/zj-grilling` on the specific weak spot

No file is written. The output is a process artifact, not a persistent record. If you want to keep it, paste it into a handoff doc or a prototype note yourself.

## Trigger

User-invoked, early in a plan's life — before it's been torn down by review or by `/zj-grilling`. The point is to check whether the plan has a defensible floor before spending time stress-testing it. One-shot by design: if the user wants a multi-round exchange, they should switch to `/zj-grilling` directly.

## See also

- `/zj-grilling` — the attack-side counterpart. Use when steelmanning fails or when you want to skip straight to questioning.
- `/zj-handoff` — if you want to save the steelmanned case as part of a handoff to another agent (manual paste; this skill doesn't write).
- `/zj-debrief` — runs at task close, looks back. Steelman looks forward, before commit.
