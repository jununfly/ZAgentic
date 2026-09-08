# Roadmap CLI reference

All roadmap operations use the skill's `roadmap_cli.py`. Inputs are deterministic and the Python dependency is standard-library-only (Python 3.8+).

## Commands

```bash
# Initialize (single-file mode is the default)
python roadmap_cli.py init <roadmap_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]
python roadmap_cli.py init <bundle_path> --storage bundle --title "大型路线图"

# Convert an existing legacy JSON explicitly; the source is never rewritten
python roadmap_cli.py migrate <json_path> --to bundle [--output <bundle_path>] [--snapshot-interval N]

# Node CRUD
python roadmap_cli.py add <json_path> <parent_id> "<label>" [--status pending] [--mode explore]
python roadmap_cli.py update <json_path> <node_id> --status completed
python roadmap_cli.py update <json_path> <node_id> --label "新标签" --notes "备注内容"
python roadmap_cli.py delete <json_path> <node_id>
python roadmap_cli.py get <json_path> <node_id>

# Decisions
python roadmap_cli.py decide <json_path> <node_id> "问题" "答案" ["备注"]
python roadmap_cli.py decisions <json_path> [<node_id>]
python roadmap_cli.py remove-decision <json_path> <node_id> --index N
python roadmap_cli.py remove-decision <json_path> <node_id> --question "<问题文本>"

# Render and inspect
python roadmap_cli.py render <roadmap_path>
python roadmap_cli.py section <roadmap_path> [--max-depth 2] [--max-bytes N]
python roadmap_cli.py section <roadmap_path> --all [--max-bytes N]
python roadmap_cli.py link <json_path> <md_file>
python roadmap_cli.py tree <json_path> [<node_id>] [--depth 3]
python roadmap_cli.py path <json_path> <node_id>
python roadmap_cli.py siblings <json_path> <node_id>
python roadmap_cli.py focus <json_path>
python roadmap_cli.py validate <json_path>
python roadmap_cli.py stats <json_path>
python roadmap_cli.py recommend-storage <roadmap_path> [--measure]
```

`render` writes the lightweight Markdown view (tree depth=2, current focus, and one level of the focus subtree). `section` is bounded by default; use `--all` for an explicit full export and optionally cap its bytes. `focus` returns the first in-progress leaf.

`recommend-storage` is a read-only advisory. It reports node/decision counts,
canonical and view bytes, and bundle shard/history sizes. It returns
`keep-single`, `consider-bundle`, `recommend-bundle`, or `keep-bundle` without
writing indexes, migrating the roadmap, or editing Markdown. `--measure` adds
local bounded-tree and full-section timings; timing thresholds are advisory and
machine-dependent.

The CLI selects storage from the path: an existing directory with `manifest.json`
is a roadmap bundle; a file is legacy single-file JSON. Bundle mode keeps node,
decision, and append-only history shards independently readable. `tree`, `get`,
`focus`, node-scoped `decisions`, and light `render` are lazy/bounded operations.
`remove-decision` records a decision retraction in bundle mode, preserving the
original record and its history rather than physically deleting it.

Bundle layout:

```text
roadmap.bundle/
├── manifest.json          # small control plane
├── current.json           # active materialized snapshot pointer
├── nodes/                 # one current-state shard per node
├── decisions/             # one decision shard per node
├── history/events.jsonl   # append-only mutation history
├── snapshots/             # materialized snapshot metadata
├── views/                 # generated Markdown views
└── indexes/               # disposable derived indexes
```

Markdown is a generated view and is never imported back into roadmap state. The
old `import` command is intentionally not supported; use `migrate --to bundle`
for storage conversion.

`unlock` is an explicit cleanup operation:

```bash
python roadmap_cli.py unlock <json_path>
```

Run it only after confirming that no roadmap CLI writer is still active.

## Worked example

```bash
# Human says: 「把文章处理后端走通」
python roadmap_cli.py tree roadmap.json 1-1-1
python roadmap_cli.py add roadmap.json 1-1-1 "文章处理后端流水线" --status in_progress
python roadmap_cli.py decide roadmap.json 1-1-1-5 "后端用什么？" "Python + FastAPI" "轻量够用"
python roadmap_cli.py update roadmap.json 1-1-1-5 --status completed --notes "API: POST /articles/convert"
python roadmap_cli.py render roadmap.json
python roadmap_cli.py section roadmap.json --all
```

## Script location and write safety

Scripts live beside this skill:

```text
<skill_dir>/roadmap.py        # core library
<skill_dir>/roadmap_cli.py    # CLI entry point
<skill_dir>/roadmap_bundle.py # sharded bundle adapter
```

After the skill is loaded, locate them with `$SKILL_DIR` or an absolute path.

Write commands use `<roadmap_path>.lock/` and atomic JSON/Markdown writes. Do not
run write commands for the same roadmap in parallel. A stale lock is not cleared
automatically; the timeout reports its owner and path so it can be checked before
`unlock`. Migration locks both source and destination and builds/validates a
temporary bundle before the final directory rename, so a failed migration leaves
the source untouched.

Deleting a node recursively deletes its children; confirm the target first.

## Demos

- `demos/roadmap_demo.json` — an AI-Native personal compounding-tool-system roadmap.
- `demos/ZJ_ROADMAP_section_demo.md` — standard output rendered from JSON.
- `benchmarks/roadmap_bundle_benchmark.py` — reproducible small/medium/large bundle benchmark generator.
- `tests/verify_real_plan_corpus.py` — read-only real Markdown-plan corpus migration contract.
