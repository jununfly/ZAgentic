
# ZAgentic Skills

[![skills.sh](https://skills.sh/b/jununfly/ZAgentic)](https://skills.sh/jununfly/ZAgentic)

Jununfly's agent skills for real engineering - not vibe coding.

Developing real applications is hard. Approaches like GSD, BMAD, and Spec-Kit try to help by owning the process. But while doing so, they take away your control and make bugs in the process hard to resolve.

These skills are designed to be small, easy to adapt, and composable. They work with any model. They're based on decades of engineering experience. Hack around with them. Make them your own. Enjoy.

If you want to keep up with changes to these skills, follow the ZAgentic repository updates.

## Quickstart (30-second setup)

1. Run the skills.sh installer:

```bash
npx skills@latest add jununfly/ZAgentic
```

2. Pick the skills you want, and which coding agents you want to install them on. **Make sure you select `/zj-setup-skills`**.

3. Run `/zj-setup-skills` in your agent. It will:
   - Ask you which issue tracker you want to use (GitHub, Linear, or local files)
   - Ask you what labels you apply to tickets when you triage them (`/zj-triage` uses labels)
   - Ask you where you want to save any docs we create

4. Bam - you're ready to go.

## Human-Agent Workflow

These skills are meant to be used as a loop, not as isolated commands. Humans keep judgment; agents handle repeatable execution and verification.

The workflow is issue-centered: humans own intent, priority, trade-offs, acceptance criteria, and final review. Agents gather context, slice work into issues, implement one issue at a time, run verification loops, and leave handoff notes when work moves between contributors.

The ZJ-prefixed docs (`ZJ-CONTEXT.md`, `docs/zj-agents/`, `docs/zj-adr/`) keep this workflow's context, decisions, and coordination notes separate from other agents or human-maintained documentation.

### Default Issue-Centered Loop

```text
Idea
  ↓
Align intent and language
  ↓
Slice into issues
  ↓
Triage when coordination is needed
  ↓
Implement one issue with tests
  ↓
Diagnose if stuck
  ↓
Review, merge, or hand off
```

1. **Align intent and language**
   Use `/zj-grilling` for general planning, or `/zj-domain-modeling` when the repo's domain language and ADRs matter.

2. **Slice the work into issues**
   Use `/zj-to-tickets` to turn the agreed plan into small, independently grabbable tickets.

3. **Triage when coordination is needed**
   Use `/zj-triage` when an issue is ambiguous, missing context, blocked on a human decision, or needs an explicit human/agent readiness label.

4. **Implement one issue at a time**
   Use `/zj-tdd` to solve one issue with a red-green-refactor loop and explicit verification.

5. **Diagnose if stuck**
   Use `/zj-diagnosing-bugs` when a test failure, bug, or performance regression needs root-cause analysis instead of guesswork.

6. **Review, merge, or hand off**
   Humans review the result and make the final call. Use `/zj-handoff` when another human or agent needs to continue from the current context.

For solo work, you can often skip triage and move directly from a well-scoped issue to `/zj-tdd`.

> **In multi-human or multi-agent workflows, triage becomes the coordination contract.** Keep issue labels accurate and state transitions explicit so contributors can pick up work without guessing, duplicating effort, or fighting hidden assumptions.

### Example: Idea → Issue → Implementation

1. Human: "We need to improve onboarding."
2. Align the intent with `/zj-grilling`.
3. Turn the agreed plan into issues with `/zj-to-tickets`.
4. Pick one issue and implement it with `/zj-tdd`.
5. If the implementation gets stuck, switch to `/zj-diagnosing-bugs`.
6. Use `/zj-handoff` when another human or agent needs to continue.

### Variations

- Need product framing before issue slicing? Use `/zj-to-spec`.
- Need broader codebase context first? Use `/zj-zoom-out`.
- Need architecture improvement? Use `/zj-improve-codebase-architecture`.
- Need a throwaway design or logic spike before committing? Use `/zj-prototype`.
- Need a compact operating mode for long sessions? Use `/zj-caveman`.

## Why These Skills Exist

Jununfly maintains these skills as a way to fix common failure modes in Claude Code, Codex, and other coding agents.

### #1: The Agent Didn't Do What I Want

> "No-one knows exactly what they want"
>
> David Thomas & Andrew Hunt, [The Pragmatic Programmer](https://www.amazon.co.uk/Pragmatic-Programmer-Anniversary-Journey-Mastery/dp/B0833F1T3V)

**The Problem**. The most common failure mode in software development is misalignment. You think the dev knows what you want. Then you see what they've built - and you realize it didn't understand you at all.

This is just the same in the AI age. There is a communication gap between you and the agent. The fix for this is a **grilling session** - getting the agent to ask you detailed questions about what you're building.

**The Fix** is to use:

- [`/zj-grilling`](./skills/productivity/zj-grilling/SKILL.md) - for non-code uses
- [`/zj-domain-modeling`](./skills/engineering/zj-domain-modeling/SKILL.md) - grilling _plus_ the domain-language and ADR documentation goodies

These are my most popular skills. They help you align with the agent before you get started, and think deeply about the change you're making. Use them _every_ time you want to make a change.

### #2: The Agent Is Way Too Verbose

> With a ubiquitous language, conversations among developers and expressions of the code are all derived from the same domain model.
>
> Eric Evans, [Domain-Driven-Design](https://www.amazon.co.uk/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215)

**The Problem**: At the start of a project, devs and the people they're building the software for (the domain experts) are usually speaking different languages.

Agents are usually dropped into a project and asked to figure out the jargon as they go. So they use 20 words where 1 will do.

**The Fix** for this is a shared language. It's a document that helps agents decode the jargon used in the project.

<details>
<summary>
Example
</summary>

Here's an example `ZJ-CONTEXT.md` from a course video manager repo. Which one is easier to read?

- **BEFORE**: "There's a problem when a lesson inside a section of a course is made 'real' (i.e. given a spot in the file system)"
- **AFTER**: "There's a problem with the materialization cascade"

This concision pays off session after session.

</details>

This is built into [`/zj-domain-modeling`](./skills/engineering/zj-domain-modeling/SKILL.md) and [`/zj-grilling`](./skills/productivity/zj-grilling/SKILL.md). Together they're a grilling session that helps you build a shared language with the AI, and document hard-to-explain decisions in ADRs.

It's hard to explain how powerful this is. It might be the single coolest technique in this repo. Try it, and see.

> [!TIP]
> A shared language has many other benefits than reducing verbosity:
>
> - **Variables, functions and files are named consistently**, using the shared language
> - As a result, the **codebase is easier to navigate** for the agent
> - The agent also **spends fewer tokens on thinking**, because it has access to a more concise language

### #3: The Code Doesn't Work

> "Always take small, deliberate steps. The rate of feedback is your speed limit. Never take on a task that’s too big."
>
> David Thomas & Andrew Hunt, [The Pragmatic Programmer](https://www.amazon.co.uk/Pragmatic-Programmer-Anniversary-Journey-Mastery/dp/B0833F1T3V)

**The Problem**: Let's say that you and the agent are aligned on what to build. What happens when the agent _still_ produces crap?

It's time to look at your feedback loops. Without feedback on how the code it produces actually runs, the agent will be flying blind.

**The Fix**: You need the usual tranche of feedback loops: static types, browser access, and automated tests.

For automated tests, a red-green-refactor loop is critical. This is where the agent writes a failing test first, then fixes the test. This helps give the agent a consistent level of feedback that results in far better code.

This repo includes a **[`/zj-tdd`](./skills/engineering/zj-tdd/SKILL.md) skill** you can slot into any project. It encourages red-green-refactor and gives the agent plenty of guidance on what makes good and bad tests.

For debugging, it also includes a **[`/zj-diagnosing-bugs`](./skills/engineering/zj-diagnosing-bugs/SKILL.md)** skill that wraps best debugging practices into a simple loop.

### #4: We Built A Ball Of Mud

> "Invest in the design of the system _every day_."
>
> Kent Beck, [Extreme Programming Explained](https://www.amazon.co.uk/Extreme-Programming-Explained-Embrace-Change/dp/0321278658)

> "The best modules are deep. They allow a lot of functionality to be accessed through a simple interface."
>
> John Ousterhout, [A Philosophy Of Software Design](https://www.amazon.co.uk/Philosophy-Software-Design-2nd/dp/173210221X)

**The Problem**: Most apps built with agents are complex and hard to change. Because agents can radically speed up coding, they also accelerate software entropy. Codebases get more complex at an unprecedented rate.

**The Fix** for this is a radical new approach to AI-powered development: caring about the design of the code.

This is built in to every layer of these skills:

- [`/zj-to-spec`](./skills/engineering/zj-to-spec/SKILL.md) quizzes you about which modules you're touching before creating a spec
- [`/zj-zoom-out`](./skills/engineering/zj-zoom-out/SKILL.md) tells the agent to explain code in the context of the whole system

And crucially, [`/zj-improve-codebase-architecture`](./skills/engineering/zj-improve-codebase-architecture/SKILL.md) helps you rescue a codebase that has become a ball of mud. I recommend running it on your codebase once every few days.

### Summary

Software engineering fundamentals matter more than ever. These skills condense those fundamentals into repeatable practices, to help you ship better software with agents.

## Reference

### Engineering

Skills I use daily for code work.

- **[zj-diagnosing-bugs](./skills/engineering/zj-diagnosing-bugs/SKILL.md)** — Disciplined diagnosis loop for hard bugs and performance regressions: reproduce → minimise → hypothesise → instrument → fix → regression-test.
- **[zj-triage](./skills/engineering/zj-triage/SKILL.md)** — Triage issues through a state machine of triage roles.
- **[zj-codebase-design](./skills/engineering/zj-codebase-design/SKILL.md)** — Shared discipline and vocabulary for designing deep modules: small interfaces, clean seams, testable through the interface.
- **[zj-domain-modeling](./skills/engineering/zj-domain-modeling/SKILL.md)** — Actively build and sharpen a project's domain model — challenge terms, stress-test with scenarios, update `ZJ-CONTEXT.md` and ADRs inline.
- **[zj-improve-codebase-architecture](./skills/engineering/zj-improve-codebase-architecture/SKILL.md)** — Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
- **[zj-roadmap-driven](./skills/engineering/zj-roadmap-driven/SKILL.md)** — 路线图驱动开发：以树形 roadmap 和决策记录帮助 Human 和 Agent 保持共享地图。
- **[zj-research](./skills/engineering/zj-research/SKILL.md)** — Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo.
- **[zj-setup-skills](./skills/engineering/zj-setup-skills/SKILL.md)** — Scaffold the per-repo config (issue tracker, triage label vocabulary, domain doc layout) that the other engineering skills consume. Run once per repo before using `zj-to-tickets`, `zj-to-spec`, `zj-triage`, `zj-diagnosing-bugs`, `zj-tdd`, `zj-improve-codebase-architecture`, or `zj-zoom-out`.
- **[zj-tdd](./skills/engineering/zj-tdd/SKILL.md)** — Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[zj-code-review](./skills/engineering/zj-code-review/SKILL.md)** — Two-axis review of a diff since a fixed point — Standards (does the code follow this repo's documented coding standards, plus a fixed code-smell baseline?) and Spec (does it faithfully implement the originating issue/spec?). Runs both reviews as parallel sub-agents and reports them side by side.
- **[zj-to-tickets](./skills/engineering/zj-to-tickets/SKILL.md)** — Break any plan, spec, or the current conversation into tracer-bullet tickets (vertical slices), each declaring its blocking edges, published to the configured tracker — one file per ticket locally or native blocking links on a real tracker.
- **[zj-to-spec](./skills/engineering/zj-to-spec/SKILL.md)** — Turn the current conversation context into a spec and submit it as an issue. No interview — just synthesizes what you've already discussed.
- **[zj-zoom-out](./skills/engineering/zj-zoom-out/SKILL.md)** — Tell the agent to zoom out and give broader context or a higher-level perspective on an unfamiliar section of code.
- **[zj-prototype](./skills/engineering/zj-prototype/SKILL.md)** — Build a throwaway prototype to answer a design question — a single shareable HTML file for logic/state-model questions, or several radically different UI variations on one route.

### Productivity

General workflow tools, not code-specific.

- **[zj-caveman](./skills/productivity/zj-caveman/SKILL.md)** — Ultra-compressed communication mode. Cuts token usage ~75% by dropping filler while keeping full technical accuracy.
- **[zj-grilling](./skills/productivity/zj-grilling/SKILL.md)** — Grill the user relentlessly about a plan, decision, or idea until every branch of the design tree is resolved (frontier/rounds method).
- **[zj-handoff](./skills/productivity/zj-handoff/SKILL.md)** — Compact the current conversation into a handoff document so another agent can continue the work.
- **[zj-write-a-skill](./skills/productivity/zj-write-a-skill/SKILL.md)** — Create new skills with proper structure, progressive disclosure, and bundled resources.
- **[zj-writing-for-agents](./skills/productivity/zj-writing-for-agents/SKILL.md)** — Reference for writing any document an agent consumes (skills, AGENTS.md/CLAUDE.md, pointer-reached docs): context pointers, progressive disclosure, leading words, pruning.

### Misc

Tools I keep around but rarely use.

- **[zj-git-guardrails-claude-code](./skills/misc/zj-git-guardrails-claude-code/SKILL.md)** — Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, etc.) before they execute.
- **[zj-migrate-to-shoehorn](./skills/misc/zj-migrate-to-shoehorn/SKILL.md)** — Migrate test files from `as` type assertions to @total-typescript/shoehorn.
- **[zj-scaffold-exercises](./skills/misc/zj-scaffold-exercises/SKILL.md)** — Create exercise directory structures with sections, problems, solutions, and explainers.
- **[zj-setup-pre-commit](./skills/misc/zj-setup-pre-commit/SKILL.md)** — Set up Husky pre-commit hooks with lint-staged, Prettier, type checking, and tests.
