# A32 fresh-ledger findings — Graph Coordinator framework selection

Evidence source: `../zj-research/zjloop-graph-coordinator-framework-selection/a31-live-ledger-response.json`

Collection status: `../zj-research/zjloop-graph-coordinator-framework-selection/a31-live-collection-status.json`

Brief fingerprint: `5fbef253ed7642b64eeb69af673a2e458fa2ed04b9aaabfde8fb09c6f2128a36`

This note uses only the A31 fresh sealed ledger. It does not reuse the older
`ledger-response.json`, and it does not turn an uncovered criterion into an
absence claim.

## LangGraph

- `f1bc2d9c9130f8447fb238e9` records LangGraph as a stateful, multi-actor agent
  framework in the repository's package map.
- `8e073a335f0750bc2dbd531b` identifies checkpoint interfaces and Postgres and
  SQLite checkpointer implementations, supporting a durable-state/checkpoint
  probe.
- `21832892a3528adc38c5308a` describes a checkpoint conformance suite covering
  blob round trips, metadata, namespace isolation, and incremental updates.
- The ledger marks `observability-and-evidence` for LangGraph as unknown. This
  is an evidence gap, not proof that observability is absent.

## AutoGen

- `bb338b2ff54633163d90270f` describes an event-oriented programming model in
  which agents publish and subscribe to events, with memory, prompts, data
  sources, and skills as additional assets.
- `9ddbf455a5b5504746148383` provides the same first-party source boundary for
  provider, model, tool, and integration seams.
- `d4f1c1cc3d0b2eef33f3ccce` ties the programming model to CloudEvents, making
  event identity and transport a possible delegation seam to test.
- The ledger marks `security-and-sandbox` for AutoGen as unknown. The report
  keeps credential, approval, isolation, and dangerous-operation ownership as
  an explicit follow-up.

## CrewAI

- `0d7f5966db7f79bf2e643875` identifies CrewAI as a Python framework for AI
  agents and agentic systems.
- `129e2066db3081234d3acd3e` records SQLite-backed Flow persistence and
  agent-to-agent task utilities among the documented capabilities.
- `b75a38f9696b9a83ee568ec1` describes local traces and deployment to an HTTP
  API, which makes observability and runtime ownership concrete follow-up
  dimensions rather than product-fit proof.

## Synthesis boundary

The fresh ledger supports three narrow probes: LangGraph checkpoint contract,
AutoGen event/delegation seams, and CrewAI role/task plus persistence seams. It
does not establish that any candidate should own ZAgenticLoop's Graph/OPN
authority, Human acceptance, security policy, evidence provenance, or
lifecycle closeout. The report therefore recommends keeping the native core
and evaluating external capabilities only behind removable adapters and a
shared conformance fixture.
