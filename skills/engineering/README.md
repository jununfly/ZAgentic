# Engineering

Skills I use daily for code work.

- **[zj-guide](./zj-guide/SKILL.md)** — User-only router over all skills: "you don't remember every skill, so ask" — picks the right flow (main flow idea→ship, on-ramps for bugs/big-effort/codebase-health, vocabulary underneath, standalone). PHASE-BOUNDARIES.md for context-window decisions.
- **[zj-diagnosing-bugs](./zj-diagnosing-bugs/SKILL.md)** — Disciplined diagnosis loop for hard bugs and performance regressions: reproduce → minimise → hypothesise → instrument → fix → regression-test.
- **[zj-triage](./zj-triage/SKILL.md)** — Triage issues through a state machine of triage roles.
- **[zj-codebase-design](./zj-codebase-design/SKILL.md)** — Shared discipline and vocabulary for designing deep modules: small interfaces, clean seams, testable through the interface.
- **[zj-debrief](./zj-debrief/SKILL.md)** — User-only close-out for a finished task: drift walkthrough vs the prior `/zj-grilling` plan, new-term extraction into `ZJ-CONTEXT.md`, and 1-3 actions written to `docs/zj-retros/YYYY-MM-DD.md` with a 7-slot pointer index in ZJ-CONTEXT.md.
- **[zj-steelman](./zj-steelman/SKILL.md)** — User-only one-shot reality check on a plan: extract 2-5 core assumptions, write the strongest case for each, judge Strong/Adequate/Weak, route to `/zj-grilling` only if a case is Weak. No file written.
- **[zj-dry-run](./zj-dry-run/SKILL.md)** — User-only pre-flight rehearsal of a ticketed plan: walk each ticket, flag friction (blocker/ambiguity/dependency), output a per-ticket table + decision bottlenecks, route to `/zj-to-spec` or `/zj-grilling` if recut-worthy. No file written.
- **[zj-domain-modeling](./zj-domain-modeling/SKILL.md)** — Actively build and sharpen a project's domain model — challenge terms, stress-test with scenarios, update `ZJ-CONTEXT.md` and ADRs inline.
- **[zj-grill-with-docs](./zj-grill-with-docs/SKILL.md)** — User-only entry point: run a `/zj-grilling` session, using `/zj-domain-modeling` (writes ADR's and glossary as it goes).
- **[zj-implement](./zj-implement/SKILL.md)** — User-only total commander: implement a piece of work from a spec or tickets. Drives `/zj-tdd` internally at pre-agreed seams, ends with `/zj-code-review`, commits to the current branch.
- **[zj-improve-codebase-architecture](./zj-improve-codebase-architecture/SKILL.md)** — Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
- **[zj-merge-skill-pair](./zj-merge-skill-pair/SKILL.md)** — Execute one skill-pair merge as an atomic commit. Reads strategy from a zj-roadmap-driven node, applies 12 classes of side effects, commits, leaves roadmap update to human. Pair with zj-merge-skills-wave.
- **[zj-merge-skills-wave](./zj-merge-skills-wave/SKILL.md)** — Plan a whole merge wave from a source skills collection (local path or github URL) into this repo. Discovers source skills, compares to base, lays out a skill-pair plan as a roadmap subtree, delegates each pair to zj-merge-skill-pair.
- **[zj-resolving-merge-conflicts](./zj-resolving-merge-conflicts/SKILL.md)** — Resolve in-progress git merge/rebase conflicts hunk by hunk, by intent traced to each side's primary source. Never `--abort`.
- **[zj-roadmap-driven](./zj-roadmap-driven/SKILL.md)** — 路线图驱动开发：以树形 roadmap 和决策记录帮助 Human 和 Agent 保持共享地图。
- **[zj-research](./zj-research/SKILL.md)** — Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo.
- **[zj-setup-skills](./zj-setup-skills/SKILL.md)** — Scaffold the per-repo config (issue tracker, triage label vocabulary, domain doc layout) that the other engineering skills consume.
- **[zj-tdd](./zj-tdd/SKILL.md)** — Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[zj-wayfinder](./zj-wayfinder/SKILL.md)** — Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on the issue tracker, resolving them one at a time until the way to the destination is clear.
- **[zj-wizard](./zj-wizard/SKILL.md)** — Generate an interactive bash script that walks a human through steps only they can perform (provisioning, CI secrets, third-party dashboards, one-off migrations). Bundles a `scripts/template.sh` library for the consistent UX.
- **[zj-code-review](./zj-code-review/SKILL.md)** — Two-axis review of a diff since a fixed point — Standards (does the code follow this repo's documented coding standards, plus a fixed code-smell baseline?) and Spec (does it faithfully implement the originating issue/spec?). Runs both reviews as parallel sub-agents and reports them side by side.
- **[zj-to-tickets](./zj-to-tickets/SKILL.md)** — Break any plan, spec, or the current conversation into tracer-bullet tickets (vertical slices), each declaring its blocking edges, published to the configured tracker — one file per ticket locally or native blocking links on a real tracker.
- **[zj-to-spec](./zj-to-spec/SKILL.md)** — Turn the current conversation context into a spec and submit it as an issue.
- **[zj-zoom-out](./zj-zoom-out/SKILL.md)** — Tell the agent to zoom out and give broader context or a higher-level perspective on an unfamiliar section of code.
- **[zj-prototype](./zj-prototype/SKILL.md)** — Build a throwaway prototype to answer a design question — a single shareable HTML file for logic/state-model questions, or several radically different UI variations on one route.
