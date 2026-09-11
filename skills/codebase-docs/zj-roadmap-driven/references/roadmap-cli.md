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
python roadmap_cli.py add <json_path> <parent_id> "<label>" --max-children 3 --max-rounds 2
python roadmap_cli.py update <json_path> <node_id> --status completed
python roadmap_cli.py update <json_path> <node_id> --label "新标签" --notes "备注内容"

# Explore budget (structural units) and exit criteria
python roadmap_cli.py update <json_path> <node_id> --max-children 3 --max-rounds 2
python roadmap_cli.py update <json_path> <node_id> --exit-criteria "判据文本"   # repeatable
python roadmap_cli.py update <json_path> <node_id> --clear-budget --clear-exit-criteria
python roadmap_cli.py delete <json_path> <node_id>
python roadmap_cli.py get <json_path> <node_id>

# Decisions
python roadmap_cli.py decide <json_path> <node_id> "问题" "答案" ["备注"]
python roadmap_cli.py decisions <json_path> [<node_id>]
python roadmap_cli.py remove-decision <json_path> <node_id> --index N
python roadmap_cli.py remove-decision <json_path> <node_id> --question "<问题文本>"

# Dependencies (P1) — edges live outside the tree.
# Note: `edge` takes the action first and the path second, unlike every other
# command, because it is a command group (`git remote add` style).
python roadmap_cli.py edge add <roadmap_path> <from_id> <to_id> --type blocks|informs|supersedes|derives-from
python roadmap_cli.py edge list <roadmap_path> [--node <node_id>]
python roadmap_cli.py edge remove <roadmap_path> <edge_id>

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

## Edges

Edges are a layer orthogonal to the tree: `blocks` (hard dependency), `informs`
(context only), `supersedes` (replaces another node), `derives-from` (provenance).

Only `blocks` may not form a cycle — a `blocks` edge that would close one is
refused with `E_CYCLE` (exit 1) and nothing is written. `informs` and
`derives-from` cycles are allowed: they carry context, not scheduling. A node
may not `blocks` itself. Pointing an edge at a node that does not exist fails
with `E_NODE_NOT_FOUND` (exit 1) — dangling edges are never created silently.

Edge ids are assigned from a monotonic counter (`e1`, `e2`, ...) and are never
reused after removal, so downstream output can cite them as stable references.

`blocked` is derived from `blocks` edges on read, never stored: `get <node>`
adds `blocked: true` plus `blocked_reason` (the ids of the `blocks` edges whose
source node is not `completed`) and omits both when nothing blocks the node.
Completing the predecessor or removing the edge is visible in the very next read.
`tree` and the Markdown views render the same node with the `[!]` icon.
`--status blocked` is refused with `E_INVALID_STATUS` (exit 1) — a Human-written
`blocked` would be a second source of truth that can disagree with the edges.
`informs`, `derives-from` and `supersedes` never block.

A `supersedes` edge archives the node it points at: the superseded node stays in
the graph, keeps its decisions and history readable, and gains `archived: true`.
That marker is deliberately not a status — "completed, then superseded" is a
legitimate combination, and folding archived into `status` would discard the fact
that the work was finished. Removing the edge does not undo the marker; clear it
explicitly if the supersession is retracted.

`delete` cascades to every edge touching the removed subtree, and reports the
count broken down by type:

```text
Deleted: ['1-2']
Removed edges: 2 (blocks 1, informs 1)
```

There is no `--cascade` opt-in: an edge cannot outlive its nodes. The edges are
removed **before** the node shards, so an interrupted delete leaves "edges gone,
node still there" — rerunnable — rather than a dangling edge. When no edge was
removed the extra line is not printed, so `delete` stays byte-identical to its
pre-P1 output. A dangling edge that does appear (hand-edited file, or a crash on
the bundle carrier) is reported by `validate`, not silently scheduled around.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic failure (invalid argument, missing node, bundle error) |
| 2 | Lock timeout (another writer holds `<roadmap_path>.lock/`) |
| 3 | `E_BUDGET_EXCEEDED` — an explore node's `max_children` or `max_rounds` cap was hit |

Budget failures print `Error: E_BUDGET_EXCEEDED: <detail>` on stderr. Branch on
the code, never on the human-readable text after it. The cap is enforced on both
carriers (single-file JSON and bundle) by the same shared helper, so the two
never disagree on what counts as a start or a child.

| Code | Raised by |
|------|-----------|
| `E_CYCLE` | a `blocks` edge that would close a cycle |
| `E_NODE_NOT_FOUND` | an edge pointing at a node that does not exist |
| `E_INVALID_STATUS` | `add` / `update --status blocked` (blocked is derived, not settable) |

All three exit 1. `E_CYCLE` and `E_NODE_NOT_FOUND` are only raised by `edge`;
pre-existing commands still raise `KeyError`/`BundleError` with their original
wording, so their output is unchanged by P1.

Bundle layout:

```text
roadmap.bundle/
├── manifest.json          # small control plane (edgeSequence lives here)
├── current.json           # active materialized snapshot pointer
├── nodes/                 # one current-state shard per node
├── decisions/             # one decision shard per node
├── edges/                 # one shard per edge + a rebuildable index.json
├── history/events.jsonl   # append-only mutation history
├── snapshots/             # materialized snapshot metadata
├── views/                 # generated Markdown views
└── indexes/               # disposable derived indexes
```

Edges live in exactly one place — `edges/<id>.json`. Node shards never cache an
edge id: a second copy would allow "the node says this edge exists, `edges/`
disagrees", and a transaction cannot save you from that (forget one of the two
writes and the transaction still commits). `edges/index.json` is pure redundancy
for `from`/`to` lookups and is rebuilt by rescanning the directory if it goes
missing; the monotonic counter is **not** in it — that one lives in
`manifest.json` as `edgeSequence`, because a rebuilt counter would reuse ids.
A bundle that has never had an edge has no `edges/` directory at all.

`migrate --to bundle` carries edges across. Dropping them would be silent data
loss that looks like success at the command layer.

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
