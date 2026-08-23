# Shared research compiler

Use the commit-pinned ZHarness artifact for technical GitHub evidence, Report IR compilation, and research evaluation. The research adapter accepts only `zj-research-cli/v1`; the evaluation adapter accepts only `zj-research-eval-cli/v1`. Both fail loudly when the artifact is missing, modified, or incompatible. This skill remains an independent workflow entry alongside the hosted Research Agent; both consume the same compiler and evaluation facts.

`zj-research` owns the adapters and the artifact lock. `zj-tech-research-report`
does not copy them: its publisher first looks for a sibling `zj-research`
skill, then accepts an explicit skill-root pointer in
`ZJ_RESEARCH_RUNTIME`. The pointed directory must contain
`scripts/research_cli.py` and, for evaluation workflows,
`scripts/research_eval_cli.py`. If neither location is available, publication
stops with the setup pointer instead of falling back to uncited Markdown.

Resolve the executable in this order:

1. `ZJ_RESEARCH_CLI`, for a local ZHarness build during development.
2. `artifacts/compiler-lock.json`, whose SHA-256 pins the bundled compiler to one ZHarness commit.

When a consumer is installed independently, set the pointer to the
`zj-research` skill directory, for example:

```sh
export ZJ_RESEARCH_RUNTIME=/path/to/skills/zj-research
```

The lock records separate `research` and `evaluation` executables inside one artifact. Set `ZJ_RESEARCH_EVAL_CLI` only when testing a local ZHarness evaluation build.

The adapter verifies the artifact hash before use and extracts it to the user cache under a hash-named directory. `ZJ_RESEARCH_COMPILER_CACHE` changes that cache root. Build ZHarness normally, then update the pinned artifact mechanically from a clean `packages/` tree:

```sh
pnpm install && pnpm run build
python scripts/update-research-compiler-artifact.py /path/to/ZHarness
```

Each adapter invocation is bounded to 300 seconds. Set `ZJ_RESEARCH_CLI_TIMEOUT_SECONDS` to a positive number when a collection brief deliberately has a longer deadline.

Run `python scripts/research_cli.py --check` before creating reports. Its failure message identifies the invalid lock, missing artifact, hash mismatch, or protocol incompatibility; the skill has no Markdown-only compatibility path.

Run `python scripts/research_eval_cli.py --check` before validating the corpus. The immutable assets under `research/evaluation/controlled-quality-v1/` must pass both operations before a Judge configuration contributes to a quality baseline:

```sh
python scripts/research_eval_cli.py validate-assets manifest.json rubrics.json annotations.json calibration.json
python scripts/research_eval_cli.py calibrate-judge rubrics.json calibration.json
```

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
