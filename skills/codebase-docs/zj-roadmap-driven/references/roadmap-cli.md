# Roadmap CLI reference

All roadmap operations use the skill's `roadmap_cli.py`. Inputs are deterministic and the Python dependency is standard-library-only (Python 3.8+).

## Commands

```bash
# Initialize (single-file mode is the default)
python roadmap_cli.py init <roadmap_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]

# Convert between carriers explicitly; the source is never rewritten
python roadmap_cli.py migrate <roadmap_path> --to single|sqlite \
    [--output <path>] [--snapshot-interval N]

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

# Failure semantics & escalation (P2, #114) — Story 33/34
python roadmap_cli.py fail <json_path> <node_id> --error "失败原因" [--question "升级时给 Human 的问题"] [--max-attempts N]
#   attempts+1 / last_error / retry_backoff(封顶指数退避)；达阈值(默认3)挂 open_question 升级。不改 status。
#   执行侧元数据，需持租约（同 status）：非持有者写返回 E_LEASE_HELD。

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

# Scheduling query (read-only, derived) — see "## Scheduling query" below
python roadmap_cli.py ready <roadmap_path>
python roadmap_cli.py critical-path <roadmap_path>
python roadmap_cli.py impact <roadmap_path> <node_id>
```

`render` writes the lightweight Markdown view (tree depth=2, current focus, and one level of the focus subtree). `section` is bounded by default; use `--all` for an explicit full export and optionally cap its bytes. `focus` returns the first in-progress leaf.

`recommend-storage` is a read-only advisory. It reports node/decision counts,
canonical and view bytes, and bundle shard/history sizes. It returns
`keep-single`, `consider-bundle`, `recommend-bundle`, `consider-sqlite`,
`keep-bundle`, or `keep-sqlite` without writing indexes, migrating the roadmap,
or editing Markdown. When a recommendation names a different carrier it also
carries the exact command to act on it in `recommendation.command`
(`migrate <path> --to <carrier>`) — naming the command is not running it.
`--measure` adds local bounded-tree and full-section timings; timing thresholds
are advisory and machine-dependent.

## Carriers and explicit migration

The CLI selects storage from the path: an existing directory with
`manifest.json` is a **bundle**, a `.sqlite` / `.sqlite3` / `.db` file is
**sqlite**, anything else is **single-file** JSON. The three share one adapter
contract, so the same command works on any of them.

```bash
python roadmap_cli.py migrate <roadmap_path> --to single|sqlite \
    [--output <path>] [--snapshot-interval N]
```

Both Markdown views are produced by **one** template in `roadmap.py`
(`compose_light_section` / `compose_full_section`); the carriers feed it their
own tree, chain and focus node. They used to keep separate copies of the
layout, and the bundle copy silently drifted — no `> 当前施工` line, no
`ROADMAP_TREE` markers, no focus block, no decision notes. Duplicating a
template is the defect, not something care can prevent, so cross-carrier md
equality is asserted directly by `tests/test_cross_carrier_render.py`.

Migration is **explicit only** — no command changes your fact source by itself.
The source file is read and left byte-identical (including mtime), so after a
migration you can always answer "which artifact was the fact source a minute
ago". A target that already exists is refused, and so is migrating onto the
carrier the source is already on: neither is a silent-overwrite-shaped failure.
Nodes, decisions, edges (uid endpoints, translated to display ids only on the
way out), the edge-id counter, node leases and their audit events all come
across; the carried lease still guards writes on the new carrier.

Bundle mode keeps node, decision, and append-only history shards independently
readable, and each node lease in its own `leases/<display-id>.json` shard.
`tree`, `get`,
`focus`, node-scoped `decisions`, and light `render` are lazy/bounded operations.
`remove-decision` records a decision retraction in bundle mode, preserving the
original record and its history rather than physically deleting it.

## Scheduling query (read-only, derived)

Three read-only queries answer "what can I start next / what is the longest
outstanding chain / what does a change ripple into". All three are derived
**on read** from `blocks` edges only — never stored, never counters (Story 24
is deferred to P3). They share one module-level function in `roadmap.py`; both
carriers feed it their own data, so the two carriers print byte-identical
output. None of them takes the whole-graph lock: taking it would serialize
concurrent reads and could trip the lock-timeout exit code 2, which is a
writer's failure mode, not a reader's.

```bash
python roadmap_cli.py ready <roadmap_path>
python roadmap_cli.py critical-path <roadmap_path>
python roadmap_cli.py impact <roadmap_path> <node_id>
```

- **`ready`** — the work-claiming set: nodes that are `pending` **and** have no
  unfinished `blocks` predecessor. Sorted by id. `in_progress` is *not* ready:
  this is "what can be started", not a status filter. A hanging predecessor (its
  node gone but the edge lingers) still counts as blocking.
  - Empty → `No ready nodes.` (exit 0).
- **`critical-path`** — the single longest unfinished chain along `blocks` edges.
  "Unfinished" = `status != completed`; a completed node neither blocks nor
  contributes length. Returns **one** chain (ids, predecessor→successor); ties
  break by the smallest start id, so two reads always agree. Empty graph or
  everything completed → `[]`.
  - Empty → `No unfinished chain.` (exit 0).
- **`impact`** — every downstream node reachable from `<node_id>` along `blocks`
  edges (a change to a ripples to b). Excludes `<node_id>` itself; sorted by id.
  `informs` / `derives-from` / `supersedes` do not propagate — only `blocks`
  carries scheduling. A leaf has no downstream impact.
  - Empty → `No downstream impact.` (exit 0).
  - `<node_id>` does not exist → `E_NODE_NOT_FOUND` on stderr, exit 1.

All three print `{id}. {label} {status_icon}` per line, so the Human can tell
finished from unfinished in the impact set at a glance. The lease clause in the
spec's readiness rule (Story 20) is P2's work and is not yet implemented; today
the "no valid lease" branch is vacuously true and is intentionally not a flag or
a hardcoded `True` — when leases land, only that one clause changes.

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

When something is blocked, the Markdown views add a short **blocked chain** section
listing who is holding what up. `render` (the view written into the linked md file)
puts it inside a collapsed `<details>` so the DAG stays out of your line of sight;
`section` prints it plainly under a `### 阻塞链` heading, because that output goes
to pipes and greps. At most 5 nodes are listed and the rest are counted, not
silently dropped. With nothing blocked, both views are byte-identical to their
pre-chain output. See `roadmap-data-model.md` for the full reasoning.
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
| `E_LEASE_HELD` | writing a lease holder's fields on a node someone else holds (or with a stale fencing token) |
| `E_CONFLICT` | `--if-rev <sha>` no longer matches the current revision |
| `E_SCOPE` | an `--scope`-bearing write aimed outside that node's subtree |

All six exit 1. `E_CYCLE` and `E_NODE_NOT_FOUND` are only raised by `edge`;
pre-existing commands still raise `KeyError`/`BundleError` with their original
wording, so their output is unchanged by P1.

### Scope tokens (P2)

`--scope <node>` confines the write to `<node>` and its subtree (inclusive). A
write aimed anywhere else fails with `E_SCOPE` **naming the allowed scope**, so
the caller can correct the call instead of editing someone else's subtree. The
check walks parent links upward from the target, so it costs O(depth) and both
carriers answer it with the same code.

Omitting `--scope` means unrestricted, not read-only: the CLI cannot tell a
subagent from a planner or a Human, and "read-only by default" would also block
the lease holder from writing `status` on the node it holds. Read-only is a
policy the *parent* agent enforces by always handing down a `--scope`.

### Field-level ownership (P2)

Which fields a lease actually protects:

| Owner | Fields | Guarded by the lease? |
|-------|--------|----------------------|
| lease holder | `status`, `notes` | yes |
| planner | `label`, `mode`, `budget`, `exit_criteria` | no |
| append-only | `decisions` (`decide`) | no |
| structural | `add`, `delete`, `remove-decision` | yes |

The point is that most concurrent edits never conflict: renaming or re-budgeting
a node while another agent executes it is legal and succeeds. A mixed `update`
that touches any lease-holder field is rejected whole — no half-written node.

### Failure semantics & escalation (P2, #114)

`fail` records an execution failure on a node (Story 33/34):

```bash
python roadmap_cli.py fail <json_path> <node_id> --error "..." [--question "..."] [--max-attempts N]
```

- `attempts` increments; `last_error` and `last_failed_at` are recorded; `retry_backoff`
  is set to a capped exponential `min(60 * 2^(n-1), 3600)` seconds, recomputed every fail.
- When `attempts` reaches the threshold (default `3`, overridable per node via
  `--max-attempts`), the node gets an `open_question` field
  `{question, raised_at, raised_by, attempts}` — the signal #115's md queue renders.
- **`fail` never writes `status`.** `blocked` stays purely derived from `blocks` edges
  (§3 decision). Escalation is expressed by the `open_question` marker, not by changing
  status — so the `[!]` icon keeps meaning "dependency-blocked" only.
- `fail` touches executor-owned metadata, so it passes through the same lease gate as
  `status`: a non-holder write is rejected with `E_LEASE_HELD`.

Bundle layout:

```text
roadmap.bundle/
├── manifest.json          # small control plane (edgeSequence lives here)
├── current.json           # active materialized snapshot pointer
├── nodes/                 # one current-state shard per node
├── decisions/             # one decision shard per node
├── edges/                 # one shard per edge + a rebuildable index.json
├── leases/                # one shard per leased node (the lease store)
├── history/events.jsonl   # append-only mutation history (incl. lease audit)
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
The same "read the source-of-truth shards, not the index" rule is why
`materialize()` reads edges out of `edges/*.json`: `index.json` has no edge
list at all, so trusting it used to make `current_revision()` blind to every
edge (fixed in #117). A bundle that has never had an edge has no `edges/`
directory at all — including after a migration.

Every `migrate --to <carrier>` carries edges, decisions, node leases and their
audit events across. Dropping any of them would be silent data loss that looks
like success at the command layer.

Markdown is a generated view and is never imported back into roadmap state. The
old `import` command is intentionally not supported; use
`migrate --to single|sqlite` for storage conversion (bundle is deprecated #140, so migrate
existing bundles to sqlite or single).

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
