# doc-kind templates

One row per `doc-kind` in the governance vocabulary, and nothing outside it.
A row is the *placement contract* for that kind: `Job` says which facts have
their home here, `Does NOT belong there` says which facts do not. The second
column is not decoration — a kind that only states what it holds will slowly
absorb whatever lands next to it, which is the main way a documentation system
drifts into duplicates.

`Must-write sections` is a default skeleton; a target repository may override
it for its own kinds. `Page form` picks the shape from
[tutorial or reference](governance-contract.md#page-form-tutorial-or-reference).
`Focused check` is the one audit action that catches this kind's characteristic
rot — it is a checklist item, not a gate, and it introduces no diagnostic code.

| doc-kind | Job | Does NOT belong there | Must-write sections | Page form | Focused check |
| --- | --- | --- | --- | --- | --- |
| `method` | How to perform one repeated piece of work: steps, usage, current behavior | Why it is done this way (a `design` or `adr` claims that), and records of one particular run (process material) | Purpose / When to use / Steps / Verification / Ownership | reference | Every command, flag and default value has actually been run |
| `prd` | What problem one capability solves, its goals and its non-goals | Implementation detail (`design`), and usage instructions after it ships (`method` or `reference`) | Problem / Goals / Non-goals / Scope / Open questions | reference | Non-goals is non-empty and names something someone will ask for |
| `architecture-map` | The index: which page owns which bounded question | Any body content — it holds pointers, never prose | Bound authorities / Categories / Pointer rules | reference | One `authority-id` is bound to exactly one page |
| `architecture-overview` | What the system is: boundary, main parts, and how they relate | Subsystem internals (`architecture-subsystem`), and step-by-step procedures (`method`) | Scope / Context / Components / Boundaries | reference | Every component links to the descendant that owns it |
| `architecture-layers` | Layer responsibilities and the allowed direction of dependency | What happens inside one layer (`architecture-subsystem`) | Layer list / Dependency direction / Rules | reference | Dependency direction is stated once and is one-way |
| `architecture-subsystem` | One subsystem's purpose, responsibility and high-level behavior | Low-level implementation detail (link to the owning descendant) and cross-part sequences (`architecture-flow`) | Purpose / Responsibility / Interfaces / Behavior | reference | No section explains something a descendant already owns |
| `architecture-flow` | One sequence that crosses parts: control or data, in order, with failure | Static responsibility of the participants (that is `architecture-subsystem` or `architecture-overview`) | Actors / Steps / Failure and retry / Boundaries | either | Every step names an owner and a failure path |
| `architecture-cross-cutting` | One concern that applies everywhere: logging, security, configuration, errors | A single component's own explanation of that concern | Concern / Rule / Exceptions / Where enforced | reference | Every exception is named rather than implied |
| `agreement` | What two or more parties owe each other: interface contracts, commitments, limits | One party's internal decision (that is `adr` or `design`) | Parties / Terms / Change process | reference | Change process says who has to agree |
| `design` | Why one option was chosen: options considered, trade-offs, consequences | Usage steps (`method`) and, once built, the description of what now exists (`architecture-*`) | Context / Options / Trade-offs / Decision / Consequences | either | At least two rejected alternatives, each with a reason |
| `testing` | Test strategy: levels, how to run them, what fixtures pin | The result of one run — that is an evidence surface, not a page | Levels / How to run / Fixtures / Coverage expectations | either | Every command in it has been run |
| `benchmark` | The definition of a measurement and the conditions that make two runs comparable | Raw profiles and any single run's numbers (evidence surface) | Workload / Method / Environment / How to reproduce | reference | Environment is stated precisely enough to reproduce |
| `reference` | The lookup surface for external or current facts: APIs, configuration, specifications | A teaching sequence (`method`), and arguments for a position (`design` or `adr`) | Lookup scope / Current behavior / Version pin / Source | reference | Every fact carries a source, a version pin, or both |
| `adr` | One long-lived decision: its verdict and its reasons | How the decision was executed (process material), and the state of the world after it (`architecture-*`) | Context / Decision / Consequences / Status | reference | An implemented decision is written in the present tense about reality |
| `plan` | Work in progress: scope, steps, and the next checkpoint | Conclusions after the work ends (process closeout), and anything durable (`method`, `architecture-*`) | Scope / Steps / Checkpoints | either | There is a stated end condition, not just a task list |
| `retro` | What one piece of finished work produced: findings and next actions | Work still in motion (`plan`), and general practice (`method`) | What happened / Findings / Next actions | reference | Findings are separated from next actions |
| `fixture-documentation` | Why one fixture exists and which invariant it pins | The fixture's own data and results (evidence surface) | What it pins / Why / How to regenerate | reference | It names the invariant, not just the files |
