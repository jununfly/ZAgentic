---
name: zj-guide
description: Ask which skill or flow fits your situation. A router over the skills in this repo.
disable-model-invocation: true
---

# Choose a route

You do not need to remember every skill. Start from the situation, choose one
route, and let that skill own its detailed procedure.

A **flow** is a path through the skills. Most paths run along one **main flow**, and one of several **on-ramps** merges onto it. Everything else is standalone, or a vocabulary layer that runs underneath.

## Invocation boundary

`zj-guide` is user-only, so it chooses a route for the Human; it does not
silently invoke another user-only skill. The other user-only routes are
`zj-agents-init`, `zj-caveman`, `zj-debrief`, `zj-dry-run`,
`zj-grill-with-docs`, `zj-implement`, `zj-improve-codebase-architecture`,
`zj-merge-skill-pair`, `zj-merge-skills-wave`, `zj-steelman`, `zj-teach`,
`zj-to-questionnaire`, `zj-to-spec`, `zj-to-tickets`, `zj-triage`,
`zj-wayfinder`, and `zj-wait-what`.

All other public skills remain model-invoked or reference-capable: the agent
may reach them when their descriptions match, while the Human may still name
them directly. Root-level personal skills are intentionally outside this
public router.

## The main flow: idea → ship

The route most work travels. You have an idea and want it built.

1. **`/zj-grill-with-docs`** — sharpen the idea by interview. Start here whenever you are **working in a working directory**: it's stateful, retaining what it learns in `ZJ-CONTEXT.md` and ADRs. For a standalone session with no working directory, invoke **`/zj-grilling`** directly; it is the stateless primitive and leaves no paper trail.
2. **Branch — can you settle every question in conversation?** If a question needs a runnable answer (state, business logic, a UI you have to see), detour through a prototype, bridged by **`/zj-handoff`** in both directions (a prototype lives in its own directory, which is exactly what `/zj-handoff` is for — see Phase boundaries):
   - **`/zj-handoff`** out, then open a fresh session against that file,
   - **`/zj-prototype`** to answer the question with throwaway code,
   - **`/zj-handoff`** back what you learned, and reference it from the original idea thread.
3. **Branch — is this a multi-session build?**
   - **Yes** → **`/zj-to-spec`** (turn the thread into a spec), then **`/zj-to-tickets`** to split it into tracer-bullet tickets, each declaring its **blocking edges**. On a local tracker that's one file per ticket under `.scratch/<feature>/issues/`, worked blockers-first by hand; on a real tracker the edges become native blocking links, so any ticket whose blockers are done can be grabbed — kick off **`/zj-implement`** per ticket, **`/clear`ing context between each one**. Each ticket is self-contained, so the last one's context is disposable.
   - **No** → **`/zj-implement`** right here, in the same context window.

   Either way, **`/zj-implement`** builds each issue by driving **`/zj-tdd`** internally — one red-green slice at a time — then closes out by running **`/zj-code-review`**, a two-axis review (Standards + Spec) of the diff, before committing. Reach for **`/zj-tdd`** on its own when you just want to build a concrete behaviour test-first without a full spec, and **`/zj-code-review`** on its own whenever you want to review a branch or PR against a fixed point.

### Context hygiene

Keep steps 1–3 in **one unbroken context window** — don't compact or clear until after `/zj-to-tickets` — so the grilling, spec, and tickets all build on the same thinking. Each `/zj-implement` then starts fresh, working from the ticket.

The limit on this is the **[smart zone](https://www.aihero.dev/ai-coding-dictionary/smart-zone)**: the window (~150k tokens on state-of-the-art models) within which the model still reasons sharply. If a session approaches it before `/zj-to-tickets`, don't push on degraded — `/compact` at the nearest phase boundary and carry on (see Phase boundaries).

## Cross-stage checkpoints

These are user-only guardrails around the main flow, not replacement flows:

- **Before grilling** — **`/zj-steelman`** tests whether an existing proposal has a strong case. It routes to `/zj-grilling` only when an assumption is weak.
- **After tickets, before implementation** — **`/zj-dry-run`** rehearses the ticket order, dependencies, and friction. Re-cut with `/zj-to-spec` or `/zj-grilling` if the plan cannot run as written.
- **After the task** — **`/zj-debrief`** checks drift against the plan, extracts durable vocabulary, and records the next actions.

Use these at their named phase; they complement `/zj-grill-with-docs`,
`/zj-to-tickets`, `/zj-implement`, and `/zj-code-review` rather than adding a
second implementation path.

## On-ramps

A starting situation that generates work, then merges onto the main flow.

- **Bugs and requests piling up** → **`/zj-triage`**. It moves issues through triage roles and produces agent-ready issues, which **`/zj-implement`** later picks up.

  Triage is only for issues **you didn't create** — bug reports, incoming feature requests, anything that arrives raw. Tickets that `/zj-to-tickets` produced are already agent-ready, so **don't triage them**.

- **Something's broken** → **`/zj-diagnosing-bugs`**. For the hard ones: the bug that resists a first glance, the intermittent flake, the regression that crept in between two known-good states. It refuses to theorise until it has a **tight feedback loop** — one command that already goes red on *this* bug — then fixes with a regression test. Its post-mortem hands off to **`/zj-improve-codebase-architecture`** when the real finding is that there's no good seam to lock the bug down.

- **A huge, foggy effort — a greenfield project or a huge feature build, too big for one session** → **`/zj-wayfinder`**, the most cognitively demanding flow here. When the way from here to the destination isn't visible yet, it charts a **shared map** of **decision tickets** on the issue tracker and resolves them one at a time — producing **decisions, not deliverables** — until the fog is pushed back and the way is clear. Where **`/zj-grill-with-docs`** sharpens an idea you can hold in one session, wayfinder is for the idea you can't — and it's slower and denser, so save it for exactly that, never a well-scoped feature.

  When the map clears, **it hands off, it doesn't build**: merge onto the main flow at **`/zj-to-spec`**, which collapses the map's linked decisions into a buildable plan, then `/zj-to-tickets` and `/zj-implement` as usual. Looping the map straight into `/zj-implement` skips that collapse and throws the linked detail away — go straight to `/zj-implement` only when the effort turned out genuinely small.

## Planning, tracking, and delegation

- **`/zj-leader`** — turn one sentence into a self-contained `/goal` brief when the desired next step is to delegate work to an agent. It is a task-brief route, not a substitute for the idea→ship flow.
- **`/zj-wayfinder`** — plan a foggy, multi-session effort and resolve decision tickets. When the map is clear, continue through `/zj-to-spec` → `/zj-to-tickets`.
- **`/zj-roadmap-driven`** — track an agreed route in a local JSON roadmap, record decisions, and keep the Human-facing Markdown view current. It tracks; it does not replace wayfinder planning or ticket slicing.
- **`/zj-initiative-registry`** — maintain cross-repository Initiative → Spec → Plan navigation, validation, drift checks, and closeout reminders. It is the control plane; the registered Plan still executes through its own roadmap.

If the work is already well-scoped, skip `/zj-leader` and `/zj-wayfinder` and
start at the main flow.

## Codebase health

Not feature work — upkeep.

- **`/zj-improve-codebase-architecture`** — run whenever you have a spare moment to keep the codebase good for agents to operate in. It surfaces **deepening opportunities**; picking one _generates an idea_ you can take into the main flow at `/zj-grill-with-docs`. It's the survey that finds the candidates; **`/zj-codebase-design`** (below) is the bench you design the chosen one on.

## Research and design

- **`/zj-systematic-research`** — research a product, company, concept, technology, or person systematically: reconstruct its evolution, compare its current competitive position, and form a judgment. Do not use it for a single fact, API/document reading, a local technical question, or a solution-selection report. It lives in the public `research` bucket.
- **`/zj-research`** — collect high-trust primary-source findings or compile commit-pinned evidence for a technical comparison. It stops at evidence and explicit unknowns.
- **`/zj-code-research`** — build a Repository Map, then perform a bounded Architecture Study of selected repository modules or flows.
- **`/zj-tech-research-report`** — turn technical findings into a technical-solution research report. Use it after `/zj-research` or `/zj-code-research`; technical comparisons use the sealed ledger and Report IR.
- **`/zj-tech-design-review`** — review a proposed technical design from problem framing through architecture, metrics, risk, rollout, testing, and follow-up.

Keep the distinction sharp: systematic research explains an object; research
collects evidence; research-report synthesizes evidence; design-review tests a
proposed solution.

## Vocabulary underneath

Two model-invoked references that run *beneath* the other skills — each the single source of truth for its vocabulary. Reach for them directly when the **words**, not the process, are the problem; or let the skills above pull them in.

- **`/zj-domain-modeling`** — sharpen the project's *domain* language: challenge a fuzzy term, resolve an overloaded word ("account" doing three jobs), record a hard-to-reverse decision as an ADR. It's the active discipline `/zj-grill-with-docs` drives to keep `ZJ-CONTEXT.md` a clean glossary.
- **`/zj-codebase-design`** — the deep-module vocabulary (module, interface, depth, seam, adapter, leverage, locality) for designing a module's *shape*: a lot of behaviour behind a small interface at a clean seam. `/zj-tdd` and `/zj-improve-codebase-architecture` both speak it.

## Skill maintenance and repository closeout

- **`/zj-write-a-skill`** — create a new skill or add its bundled resources. Pair it with **`/zj-writing-for-agents`**, the reference for editing skills, `AGENTS.md`, `CLAUDE.md`, or pointer-reached documents.
- **`/zj-merge-skills-wave`** — plan a multi-skill adoption from another collection; **`/zj-merge-skill-pair`** executes one approved pair as the atomic merge unit.
- **`/zj-neat-freak`** — close out knowledge drift by reconciling docs, rules, authorized memory, and workspace residue with actual code and runtime state.

These routes maintain the skill system itself; ordinary feature work stays on
the main flow.

## Phase boundaries

A **phase** is a chunk of work inside a session — the grilling, the implementation, the QA. At the **boundary** between two of them you have five options, and picking between them is the fuzziest decision in this whole map:

- **Continue** — stay put. Costs nothing, loses nothing.
- **`/clear`** — empty the window, when nothing here matters to what's next.
- **`/zj-handoff`** — write a portable markdown file. Narrow: only for a **new harness**, a **new directory**, a **colleague**, or forking a side task **mid-phase**. What it buys is portability.
- **Subagent** — send a tightly-scoped task to its own window and get a report back.
- **`/compact`** — compress this context and seed a fresh session with it. The **default**, at the bottom of the tree rather than the first reach.

Read PHASE-BOUNDARIES.md for the ordered tree — the five questions, the reasoning behind each branch, and why the primary-source cost makes **Continue** the one to rule out first. Make the decision **at** a boundary; mid-phase, continue or split the rest into subagents.

## Standalone

Off the main flow entirely.

- **`/zj-grilling`** — the interview primitive itself: rounds, the frontier, facts are the agent's job and decisions are yours. `/zj-grill-with-docs` is the repository-aware entry point; reach for `/zj-grilling` directly when you want a stateless interview with no wrapper around it. `/zj-triage`, `/zj-wayfinder` and `/zj-improve-codebase-architecture` all run it internally.
- **`/zj-resolving-merge-conflicts`** — work an in-progress merge or rebase conflict hunk by hunk, resolving by **intent** traced to each side's primary source rather than by picking lines, then finish the operation. It never runs `--abort`. Standalone and off every flow: reach for it when you are already mid-conflict.
- **`/zj-prototype`** — a small, throwaway program that answers one design question: does this state model feel right, or what should this UI look like. Throwaway is a constraint on how the code is written, not a promise to destroy it: the answer folds into the real code, and the prototype itself is kept as a **primary source** on a `prototype/<name>` branch out of main, pointed at from the implementation issue. It's the detour in step 2 of the main flow, but reach for it any time a design question is hard to settle on paper.
- **`/zj-research`** — delegate primary-source reading to a **background agent**, or compile commit-pinned evidence for a multi-repository technical comparison. It leaves cited findings and, for technical comparisons, a sealed ledger in the repo. Keep working while it reads. Take those facts into `/zj-grill-with-docs`; research feeds the thinking, it doesn't replace it.
- **`/zj-code-research`** — build a Repository Map and use it to select a bounded Architecture Study. Hand technical decision questions to `/zj-tech-research-report` rather than putting recommendations into the map.
- **`/zj-tech-research-report`** — turn technical findings into a cited solution research report. Technical comparisons compile through the sealed ledger and Report IR.
- **`/zj-to-questionnaire`** — when the thing blocking you isn't in your head or the codebase but in **someone else's**, this writes them a questionnaire to fill in. It's the inverse of `/zj-grilling`: instead of interviewing you about the subject, it interviews you about the **send** — who it's going to, what you need back — and aims the questions at the gap. What comes back is material for `/zj-grill-with-docs` or `/zj-to-spec`.
- **`/zj-wizard`** — for the steps only a **human** can take: provisioning infrastructure, setting up credentials or CI secrets, clicking through an unfamiliar third-party dashboard, running a one-off migration or cutover. It generates an interactive bash script that opens each URL, captures each value, and writes it into `.env` and GitHub secrets — so the procedure stops being something you re-explain to an agent every time. Model-invoked, so the agent reaches for it the moment it hits a wall only you can pass. If the agent could just do it itself, it should; this is for where a human is genuinely in the loop.
- **`/zj-wait-what`** — the corrective for a message that didn't land. Use it mid-conversation, inside any other skill, and the agent re-pitches what it just said with the context you were missing, in plain English, using the `ZJ-CONTEXT.md` vocabulary. It works after the fact; `/zj-grill-with-docs` is the upfront cure, because a shared language agreed early is what stops the jargon arriving at all.
- **`/zj-teach`** — learn a concept over multiple sessions, using the current directory as a stateful workspace.
- **`/zj-writing-for-agents`** — reference for writing documents agents consume: skills, AGENTS.md, pointed-at docs.
- **`/zj-caveman`** — switch to ultra-compressed communication when token-efficient replies are the goal.
- **`/zj-aihot`** — retrieve current Chinese AI news and highlights from AIHOT; use it instead of memory for time-sensitive AI news.
- **`/zj-storage-analyzer`** — inspect macOS/Windows storage usage and produce cleanup guidance; it is for storage, not RAM/process diagnosis.
- **`/zj-git-bypass-safe-delete`** — recover a Git repository corrupted by the WorkBuddy safe-delete shim; use it when the documented corruption symptoms appear.
- **`/zj-git-guardrails-claude-code`** — install Claude Code hooks that block dangerous Git operations.
- **`/zj-migrate-to-shoehorn`** — migrate test assertions to `@total-typescript/shoehorn`.
- **`/zj-scaffold-exercises`** — scaffold lintable exercise sections, problems, solutions, and explainers.
- **`/zj-setup-pre-commit`** — set up Husky, lint-staged, type checking, and tests at commit time.

## Precondition

**`/zj-agents-init`** — run before your first engineering flow to configure the issue tracker, triage labels, and doc layout the other skills assume. Custom issue trackers also work.
