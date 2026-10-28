# Multi-device multi-agent context findings

## Run identity

The real Research Agent did not publish a report. Its first attempt stopped on `GITHUB_RATE_LIMITED`; an authenticated retry stopped on a DeepSeek `TRANSPORT` failure. Neither attempt created a report artifact. The shared pinned Evidence Compiler then collected the three repositories with one brief, and the shared Report Compiler published the final Markdown/HTML pair.

## Cited findings

- MineContext presents a proactive personal context-aware AI partner with context capture and processing plus a local-first privacy stance. The selected commit does not provide strong evidence for team task ownership or collaboration-control semantics. Evidence: `c1670d9d33d1395b02484b66`, `f5afc3d0b3536e1f3f9ad043`, `46a23e06545555264946319f`.
- MyContext presents a persistent personal work context layer. Its README describes authorized multi-source ingestion, incremental collection, a local SQLite vault, personal data control, and approval for consequential actions. Evidence: `b694a2b9b94a8ba7e6b47ef4`, `6953f661bac7a6ee6f695ab3`, `e1c77df9c8b21389e3d252f5`, `5d344f534037a88a2d0ae65d`.
- TencentDB-Agent-Memory's MemoryCore explicitly models users, teams, Agents, tasks, Skills, knowledge assets, memberships, ownership, and access relationships. It exposes memory, knowledge metadata, and asset metadata through an independent HTTP Gateway and TypeScript/Python SDKs. Evidence: `a53eaf05e9e36a79f063b7ea`, `b7389632d90d5c3be6a231f3`.
- TencentDB-Agent-Memory has container and migration mechanisms, but those mechanisms do not establish Git merge ownership, canonical-roadmap decisions, atomic Work Packet claims, experiment budgeting, or release authorization. Those remain responsibilities of the ZHarness/ZAgentic control plane. Evidence: `21caa43672cc9f52c6c746a1`, `1879da8cdc20aaea25ede65c`, `6de50efd7dd6779d955d942a`.
- Popularity and task match remain separate. At collection time the candidates were MineContext `5468 / 0`, MyContext `1549 / 2`, and TencentDB-Agent-Memory `23084 / 7` for `stars / topicMatch`; the compiler fixed every observation to the revisions in the sealed ledger.

## Information gaps and next steps

| Gap | Nature | Next step |
|---|---|---|
| Cross-device consistency under concurrent writes | unverified | Run a two-device PoC with revisioned writes, disconnect/reconnect, conflict injection, and recovery audit. |
| Team/Agent permission enforcement | unverified | Map the MemoryCore ownership fields to actual authorization checks and test unauthorized reads and writes. |
| Retrieval quality for engineering decisions | unverified | Build a small approved corpus of Work Packets, roadmap decisions, Agent Notes, and receipts; measure provenance and recall. |
| Control-plane integration | absent | Design a narrow adapter; keep Git, roadmap, claims, budgets, and release gates authoritative outside the memory system. |
| Real Research Agent stability | unverified | After upstream availability recovers, rerun the exact topic and compare its report with this compiler-backed result. |

## Self-evaluation

| Criterion | Result |
|---|---|
| Citations accurate — hard gate | Pass: every repository observation traces to the sealed ledger and commit-pinned source list. |
| Synthesis saves time | Pass: the recommendation separates memory-layer fit from collaboration-control-plane fit. |
| Incrementally editable | Pass: the brief, sealed ledger, Report IR, generated report, receipt, and gaps are separate versioned artifacts. |
