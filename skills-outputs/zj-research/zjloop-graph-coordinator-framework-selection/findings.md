# ZAgenticLoop Graph Coordinator framework selection — cited findings

## Evidence boundary

The local code pass is bound to ZAgenticLoop commit `c7d4b082b0dde7df260848e2b3209c7c38889dd3` and Architecture Study snapshot `study-bec314dee3c9f2e9f604c52b`. The bounded Repository Map is snapshot `map-c8ade72a1d1d9640c164106c`; both code-research hard gates pass after fixing flow-ID uniqueness in the study generator.

The requested three-repository collection was attempted with `research-brief.json`, but the unauthenticated GitHub API rate limit was exhausted during the multi-repository run. The sealed ledger used below is the previously successful `zj-research-cli/v1` collection saved as `ledger-response.json`, with source brief `sealed-ledger-source-brief.request.json`. It pins LangGraph, AutoGen, and CrewAI to commits and provides canonical Evidence IDs, but its criteria were broader than this decision. Its evidence is therefore usable for provenance and boundary checks, not as proof of complete product fit. The report keeps that limitation explicit.

## ZAgenticLoop baseline observed by the Architecture Study

- The native agent runtime validates registration, transport envelope, target identity, task/artifact binding, and bounded-loop task shape before dispatch. It persists received, validated, dispatched, running, terminal, and evidence-recorded transitions through the SQLite StateStore and treats duplicate execution as side-effect-free (`study-bec314dee3c9f2e9f604c52b`; code-study evidence `evidence-0902f19d56d9239abd98`, `evidence-7a595f617fbc6b2b5aa5`, `evidence-647c77a66f90ab59421a`, `evidence-31ee83101e9534bc2d31`).
- Native agent execution is converted into a native OPN tracer record; successful terminal execution requires output evidence, while failed, blocked, timed-out, and cancelled states remain blocked rather than becoming success (`evidence-1a886d446e32887f218e`, `evidence-99f1a672b90ae47077e7`, `evidence-31ee83101e9534bc2d31`).
- The merge path binds Human acceptance to a merge-authorization digest, checks target refs, source reachability, fast-forward possibility, clean target state, and scope digest before allowing a side effect. Missing observations produce `outcome-uncertain`, not an optimistic result (`evidence-31ee83101e9534bc2d31`, `evidence-e9291179b7fdca1036d9`, `evidence-a322146e9b834643d9af`); post-merge verification separately checks final head, clean state, diff, scope, and project verification.
- Human acceptance is a signed durable fact tied to the review handoff and verification digest; recording is validated and idempotent/conflict-aware in the SQLite StateStore (`evidence-3668d8b2a63cf34fa762b`, `evidence-1231285663172907e4ae`, `evidence-5cb8d65fc00e2d534461`, `evidence-2a70595255ba75f0e806`).
- Artifacts and evidence are content-addressed. Artifact reads verify network binding, byte length, and SHA-256; evidence reads require an actor and append an access audit record, while storage roots and access logs use restrictive permissions (`evidence-ea9fa2a7f1ad1150ae67`, `evidence-845693169a901ce7f813`, `evidence-e868dc6e25d140f59046`).
- The provider seam is already adapter-shaped: the Codex adapter builds an explicit read-only or write-enabled invocation, requires a process adapter, passes an environment allowlist, and returns provider results through the local-process boundary (`evidence-a5f8db6f760f8d479c4c`, `evidence-956919ac82b6c4670f72`, `evidence-64093a451f8ca4a08cee`).
- Execution policy and lifecycle are separate gates. Policy binds approval, preflight, artifact persistence, provider protocol, and outcome uncertainty; lifecycle requires verifier evidence before review, a review handoff before pending review, and Human acceptance before completion. (`evidence-84b73539ec0da35d247f`, `evidence-893cde8a935158037b1d`, `evidence-d4917550fef74e84ef45`, `evidence-31ee83101e9534bc2d31`).

These observations make the native core the current semantic owner of graph execution, evidence, Human control, security gates, and lifecycle. An external framework would have to enter through a narrow adapter and conformance fixture; replacing the core would duplicate or compete with existing facts.

## Candidate evidence

### LangGraph

The sealed ledger pins LangGraph to `f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`, with `40,082` stars and `topicMatch=1` copied unchanged into the report candidate. Its repository map lists a stateful multi-actor agent core, checkpoint packages including Postgres and SQLite, CLI, and Python/TypeScript SDKs (`1266c49589267df774dee5e9`, `06bfa6645b43d686af376096`, `bc964b8b7a425b0856ceaa62`). This is the strongest candidate for a focused durable-state/checkpoint capability study.

The same ledger only observed the candidate through repository maintenance material for several criteria. It does not establish that LangGraph should own ZAgenticLoop's OPN semantics, Human acceptance, sandbox policy, evidence provenance, or merge lifecycle. Those remain `unverified` for this run.

### AutoGen

The sealed ledger pins AutoGen to `027ecf0a379bcc1d09956d46d12d44a3ad9cee14`, with `60,535` stars and `topicMatch=2`. README evidence identifies it as an agent framework and Docker/devcontainer evidence shows a reproducible development environment (`6867ddc092eda10b00bef823`, `75e442270a45d62febe84f32`, `576203d060741d1c914c50f1`). That supports a follow-up study of delegation and multi-agent coordination, not a product-core decision.

The ledger does not close the ownership boundary for durable state, Human acceptance, sandbox authority, TypeScript/Node embedding, or exit. These criteria remain `unverified`; popularity is not a substitute.

### CrewAI

The sealed ledger pins CrewAI to `0c2bcb510c8b15d077e45e34513cc3631cb366c1`, with `57,365` stars and `topicMatch=3`. Its primary evidence describes a Python agentic-systems framework and emphasizes public API, complex logic, tests, and documentation (`71333c76e7055360b395d506`, `02b8e8d72aabd3c80fd5598d`, `5c8fb1c00d0195d5ff98b195`). That makes role/task orchestration a plausible unit-capability experiment.

The collection did not prove durable scope, sandbox policy, evidence provenance, Human acceptance, or a low-cost TypeScript/Node exit path. Those remain `unverified`.

## Decision synthesis

1. **Whole-framework core:** reject for now. The native baseline already owns the high-risk semantics that a framework-core adoption would need to replace or translate: execution identity, idempotency, evidence, approval, Human acceptance, merge admission, and post-merge verification.
2. **LangGraph adapter:** highest-priority capability probe, limited to checkpoint/resume or graph scheduling behind a provider-neutral seam. It must not own OPN records, Human acceptance, artifact/evidence storage, or final lifecycle status.
3. **AutoGen adapter:** defer to a delegation/role-conversation probe after the LangGraph state probe. The current sealed evidence is not strong enough to justify dependency adoption.
4. **CrewAI adapter:** defer to a role/task orchestration probe only if it can be isolated behind the same seam and does not bring Python runtime ownership into the TypeScript core by default.
5. **Native core:** recommended default. Keep external framework work reversible and deleteable; promote an adapter only after conformance tests show lower ownership cost without semantic drift.

## Validation and exit criteria

Run one identical fixture through native and adapter paths:

- graph has two agent nodes, one retry, one blocked approval, one resumed execution, one evidence artifact, and one Human acceptance;
- assert stable execution/task/plan identities, duplicate delivery is side-effect-free, and checkpoint/resume preserves the same work item;
- assert no adapter path can bypass provider preflight, credential allowlist, artifact digest checks, independent verification, review handoff, or Human acceptance;
- assert a failed or uncertain external call cannot be rendered as completed and can be reconciled or rolled back;
- measure adapter code size, state translations, extra runtime components, cold-start latency, recovery success, and upgrade/exit effort.

Promote an adapter only when all negative security and authority cases pass, recovery is 100% for the fixture, and the adapter can be removed without rewriting native OPN, evidence, Human acceptance, or lifecycle facts. Otherwise remain native and record the candidate as deferred rather than absent.
