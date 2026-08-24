# A34 fresh-ledger findings — LangGraph checkpoint/resume adapter probe

Evidence source: `../../zj-research/zagenticloop-checkpoint-adapter-probe/a34-live-ledger-response-v2.json`

Collection status: `../../zj-research/zagenticloop-checkpoint-adapter-probe/a34-live-collection-status-v2.json`

Brief fingerprint: `c012ac5ea04d673fb1e7c7f6f317c62dc822d34727f78ef39889c61f5d544250`

This note uses the second A34 authenticated fresh sealed ledger. The first A34
fresh pass is retained as a runtime acceptance artifact, but this v2 ledger is
the report's sole external evidence source. The code-side baseline is the
separate, dirty-but-pinned `ZAgenticLoop` Repository Map and Architecture Study:

- Map: `../../zj-code-research/zagenticloop-checkpoint-adapter/repository-map-a34-88cdfb8-source.bundle`
- Study: `../../zj-code-research/zagenticloop-checkpoint-adapter/architecture-study-a34-88cdfb8-checkpoint.bundle`

## Native baseline

The Architecture Study snapshot records the current working-tree checkpoint
fixture and test boundary. The fixture binds work item, execution identity,
checkpoint source revision, artifact/state digests, duplicate delivery,
Evidence, verification, Human acceptance, and native-core authority. Its oracle
hard-stops resume identity changes, second execution authority, digest drift,
review-handoff drift, or provider authority bypass. These are source-snapshot
observations, not claims derived from the external GitHub ledger.

## LangGraph evidence

- `062b826405b696d0a9fa4f64` records that the first-party checkpoint conformance
  suite validates a `BaseCheckpointSaver` implementation's storage contract,
  including blob round-trips, metadata preservation, namespace isolation, and
  incremental channel updates. This supports a storage/conformance seam.
- `6ee57429e8b6891fcd4fd1c6` is the same first-party conformance package's
  canonical source boundary. It supports the existence of a separately
  versioned checkpointer conformance component, not a product-authority claim.
- `7146173f86f924c4895d1114` records the first-party Postgres checkpointer as a
  persistence implementation for durable, long-running workflows and agents;
  the excerpt also names the Psycopg 3 installation boundary.
- `e0458f396bb78f8b06a9f3fd` points to the first-party PyPI/API boundary for the
  conformance package. It does not establish a native TypeScript/Node.js
  checkpointer seam.
- `28fbdbbeb69b0dd1ca4882e2` repeats the conformance package's storage-contract
  boundary for the host-authority criterion; it does not prove that LangGraph
  should own ZAgenticLoop execution, Evidence, Human acceptance, security, or
  lifecycle facts.

## Explicit gaps

The v2 ledger has `unknownCriteria: []` because the compiler found at least one
matching source for every requested criterion. That mechanical result is not a
semantic proof that every question was answered. This run did not produce a
direct source excerpt establishing `thread_id`/`interrupt`/`Command` resume
identity, a native JavaScript/TypeScript checkpointer package, or host-product
security/approval ownership. The report keeps those items as unknown follow-up
gates rather than converting them to absent capabilities.

## Synthesis boundary

The evidence supports testing LangGraph's checkpointer storage contract as one
removable capability. It does not support adopting LangGraph as the Graph/OPN
core or moving native execution authority. The next slice is therefore an
isolated provider-neutral adapter against the native fixture, with explicit
resume identity, duplicate delivery, digest, Evidence, verification, Human
acceptance, runtime, and removal checks.
