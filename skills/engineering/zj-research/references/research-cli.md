# Shared research compiler

Use the ZHarness `dsh-research` executable for technical GitHub evidence and Report IR compilation. The adapter accepts only `zj-research-cli/v1` and fails loudly when the executable is missing or incompatible.

Resolve the executable in this order:

1. `ZJ_RESEARCH_CLI`, for a local ZHarness build during development.
2. `dsh-research` on `PATH`, for the released standalone artifact.

Each adapter invocation is bounded to 300 seconds. Set `ZJ_RESEARCH_CLI_TIMEOUT_SECONDS` to a positive number when a collection brief deliberately has a longer deadline.

Run `python scripts/research_cli.py --check` before creating artifacts. Its failure message is the setup instruction; the skill has no Markdown-only compatibility path.

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

The result carries six hard correctness facts, collection cost, coverage, degradation count, report family, and compiler version. Treat `healthy: false` as a failed run. The standalone compiler persists validated sealed ledgers under `$DSH_HOME/cache/research/v1` (or `~/.dsh/cache/research/v1`) and fails loudly on a corrupt entry.
