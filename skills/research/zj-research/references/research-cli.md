# Shared research compiler

`zj-research` is a **protocol adapter**, not a compiler carrier. It defines the
protocols (`zj-research-cli/v1`, `zj-research-eval-cli/v1`), the request/response
schemas, and the Python adapter that invokes an **external** research compiler.
It bundles no compiler and carries no upstream vendor tie, so the skill runs on
any agent that points at its own compiler implementation.

The research adapter accepts only `zj-research-cli/v1`; the evaluation adapter
accepts only `zj-research-eval-cli/v1`. Both fail loudly when the external
compiler is missing, incompatible, or returns invalid output. This skill remains
an independent workflow entry alongside the hosted Research Agent; both consume
the same protocol and evaluation facts.

`zj-research` owns the adapters. `zj-tech-research-report` does not copy them:
its publisher first looks for a sibling `zj-research` skill, then accepts an
explicit skill-root pointer in `ZJ_RESEARCH_RUNTIME`. The pointed directory must
contain `scripts/research_cli.py` and, for evaluation workflows,
`scripts/research_eval_cli.py`. If neither location is available, publication
stops with the setup pointer instead of falling back to uncited Markdown.

## Supplying the compiler

The adapters resolve the executable **only** from an environment variable. There
is no bundled fallback.

1. `ZJ_RESEARCH_CLI` — the research compiler (speaks `zj-research-cli/v1`).
2. `ZJ_RESEARCH_EVAL_CLI` — the evaluation compiler (speaks `zj-research-eval-cli/v1`);

   set this only when running evaluation workflows.

The value is split with shell semantics and executed directly, e.g.:

```sh
export ZJ_RESEARCH_CLI="node /path/to/compiler/lib/bin.js"
export ZJ_RESEARCH_EVAL_CLI="node /path/to/compiler/lib/eval.js"
```

`/path/to/compiler` is whatever compiler implementation the host provides — the
skill makes no assumption about its origin. When the variable is unset, the
adapter raises a clear setup error naming the missing variable instead of
silently falling back.

When a consumer is installed independently, set the pointer to the `zj-research`
skill directory so the publisher can find the adapters:

```sh
export ZJ_RESEARCH_RUNTIME=/path/to/skills/zj-research
```

Note: `ZJ_RESEARCH_RUNTIME` only locates the adapter scripts. The adapter itself
still requires `ZJ_RESEARCH_CLI` (and `ZJ_RESEARCH_EVAL_CLI` for evaluation) to
be set in the runtime environment.

Each adapter invocation is bounded to 300 seconds. Set
`ZJ_RESEARCH_CLI_TIMEOUT_SECONDS` to a positive number when a collection brief
deliberately has a longer deadline.

Run `python scripts/research_cli.py --check` before creating reports. Its failure
message identifies the missing `ZJ_RESEARCH_CLI`, an incompatibility, or a
protocol mismatch; the skill has no Markdown-only compatibility path.

For every fresh `collect`, pass `--status-output collection-status.json` and keep
that sidecar beside the request and ledger:

```sh
python scripts/research_cli.py request.json \
  --output ledger-response.json \
  --status-output collection-status.json
```

The adapter performs a GitHub `/rate_limit` preflight before starting the
compiler. The status records whether the run was `fresh-collection`,
`reused-sealed-ledger`, or `collection-blocked`, plus the current brief and
authentication/quota observation. An anonymous request is allowed when quota
is available; set `GITHUB_TOKEN` for the authenticated quota. A blocked run
does not create a partial or synthetic sealed ledger and never silently falls
back to an older one.

To reuse an existing sealed ledger, make that choice explicit and use the
matching brief:

```sh
python scripts/research_cli.py request.json \
  --reuse-ledger previous-ledger-response.json \
  --output ledger-response.json \
  --status-output collection-status.json
```

The adapter verifies the sealed-ledger schema and brief fingerprint before
returning it. Runtime failures are emitted as `zj-research-cli-error/v1`
diagnostics with stable codes such as `GITHUB_AUTHENTICATION_FAILED`,
`GITHUB_FORBIDDEN`, `GITHUB_RATE_LIMITED`, `GITHUB_NETWORK_FAILED`, and
`COMPILER_OUTPUT_INVALID`; the original compiler message remains in diagnostic
details without being mistaken for a fresh ledger.

## Operations

Run `--check` to execute the protocol's `describe` handshake and confirm that all required operations are present.

`collect` input with explicit repositories:

```json
{"protocol":"zj-research-cli/v1","operation":"collect","brief":{"schema":"zj-research-brief/v1","topic":"...","criteria":[{"id":"governance","question":"...","critical":true,"keywords":["policy"]}],"repositories":[{"owner":"org","name":"repo"}],"policyVersion":"v1","budget":{"maxFiles":24,"maxBytes":1000000,"deadlineMs":120000}}}
```

For topic-driven candidate discovery, keep `repositories` as an empty or seed list and add:

```json
{"discovery":{"query":"agent harness","limit":10,"topicKeywords":["agent","governance","evaluation"]}}
```

The sealed ledger owns each selected repository's `stars`, `topicMatch`, and immutable revision. Do not replace those fields with model estimates.

边界（机器检查 vs review 层）：本适配器只验 ledger 形状——`repositories` 必须是对象数组，不得被标量或字符串「估计」整体替换。字段「不得被模型估计替换」的语义校验属 review 层职责：严格侧误拒风险高（合法的一手数据也可能长得像估计），不在适配器内机械判定（对应 zj-review-findings Step 4 的机器检查边界）。

`compile-report` input:

```json
{"protocol":"zj-research-cli/v1","operation":"compile-report","report":{"schema":"zj-research-report-ir/v1","family":"zj-draft/v1"},"ledger":{"schema":"zj-verified-evidence-ledger/v1"}}
```

The abbreviated objects above show routing fields only. Pass the complete Report IR and sealed ledger produced by the research run. The response echoes the protocol and operation; use only `result` after the adapter validates both.

`render-html` derives the human-reading artifact from the exact final Markdown:

```json
{"protocol":"zj-research-cli/v1","operation":"render-html","family":"zj-draft/v1","markdown":"# ..."}
```

The family-specific validator rejects missing or reordered sections before returning `result.html`. Never edit the returned HTML or treat it as a fact source.

`evaluate` accepts the same complete Report IR and ledger plus application-owned publication facts:

```json
{"protocol":"zj-research-cli/v1","operation":"evaluate","report":{"schema":"zj-research-report-ir/v1","family":"zj-draft/v1"},"ledger":{"schema":"zj-verified-evidence-ledger/v1"},"publication":{"reportHash":"<sha256>","markdownPath":"/absolute/report.md","htmlPath":"/absolute/report.html","publishCount":1}}
```

The result carries six hard correctness facts, collection cost, coverage, degradation count, report family, and compiler version. Treat `healthy: false` as a failed run.
