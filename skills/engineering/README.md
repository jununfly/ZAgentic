# Engineering

Skills I use daily for code work.

- **[zj-guide](./zj-guide/SKILL.md)** — User-only router over all public skills: picks the main flow, cross-stage checkpoints, on-ramps, planning/tracking, research/design, skill maintenance, vocabulary, and standalone utilities. PHASE-BOUNDARIES.md covers context-window decisions.
- **[zj-diagnosing-bugs](./zj-diagnosing-bugs/SKILL.md)** — Disciplined diagnosis loop for hard bugs and performance regressions: reproduce → minimise → hypothesise → instrument → fix → regression-test.
- **[zj-triage](./zj-triage/SKILL.md)** — Triage issues through a state machine of triage roles.
- **[zj-codebase-design](./zj-codebase-design/SKILL.md)** — Shared discipline and vocabulary for designing deep modules: small interfaces, clean seams, testable through the interface.
- **[zj-git-bypass-safe-delete](./zj-git-bypass-safe-delete/SKILL.md)** — Diagnose and recover from WorkBuddy's safe-delete shim corrupting Git repositories on Windows Git Bash.
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
- **[zj-initiative-registry](./zj-initiative-registry/SKILL.md)** — Manage a GitHub-hosted Initiative → Spec → Plan registry across devices and Agents, with deterministic validation and safe Git handoff.
- **[zj-leader](./zj-leader/SKILL.md)** — 把一句话想法拆成 agent 能独立跑完的 /goal 任务书：先实测调研、一轮 ≤5 问、产出含验收与断点续跑的任务书，跑完由管理者角色验收（源自 khazix-skills）。
- **[zj-neat-freak](./zj-neat-freak/SKILL.md)** — 知识/治理收尾：把项目文档、规则文件、Agent 记忆和工作区残留与代码实际运行态对齐，让下一次会话从唯一现役答案开始（源自 khazix-skills，含 evals/）。
- **[zj-agents-init](./zj-agents-init/SKILL.md)** — Initialize the per-repo agent context (issue tracker, triage label vocabulary, domain doc layout) that the other engineering skills consume.
- **[zj-tdd](./zj-tdd/SKILL.md)** — Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[zj-wayfinder](./zj-wayfinder/SKILL.md)** — Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on the issue tracker, resolving them one at a time until the way to the destination is clear.
- **[zj-wizard](./zj-wizard/SKILL.md)** — Generate an interactive bash script that walks a human through steps only they can perform (provisioning, CI secrets, third-party dashboards, one-off migrations). Bundles a `scripts/template.sh` library for the consistent UX.
- **[zj-code-review](./zj-code-review/SKILL.md)** — Two-axis review of a diff since a fixed point — Standards (does the code follow this repo's documented coding standards, plus a fixed code-smell baseline?) and Spec (does it faithfully implement the originating issue/spec?). Runs both reviews as parallel sub-agents and reports them side by side.
- **[zj-tech-design-review](./zj-tech-design-review/SKILL.md)** — Guide an evidence-backed technical design review from problem framing through architecture, metrics, risk, rollout, testing, and follow-up.
- **[zj-to-tickets](./zj-to-tickets/SKILL.md)** — Break any plan, spec, or the current conversation into tracer-bullet tickets (vertical slices), each declaring its blocking edges, published to the configured tracker — one file per ticket locally or native blocking links on a real tracker.
- **[zj-to-spec](./zj-to-spec/SKILL.md)** — Turn the current conversation context into a spec and submit it as an issue.
- **[zj-prototype](./zj-prototype/SKILL.md)** — Build a throwaway prototype to answer a design question — a single shareable HTML file for logic/state-model questions, or several radically different UI variations on one route.
