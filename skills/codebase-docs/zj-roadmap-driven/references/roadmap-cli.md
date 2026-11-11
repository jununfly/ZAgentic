# Roadmap CLI reference

`$SKILL_ROOT` 是本 SKILL.md 所在目录的绝对路径（路径基准定义见 [SKILL.md](../SKILL.md) 的 Quick start）。
以下命令的 cwd 是**目标项目**，不是 skill 目录；所有脚本调用都必须带这个前缀，解释器统一用 `python3`。

All roadmap operations use the skill's `roadmap_cli.py`. Inputs are deterministic and the Python dependency is standard-library-only (Python 3.8+).

## Commands

```bash
# Initialize (single-file mode is the default)
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" init <roadmap_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]

# Convert between carriers explicitly; the source is never rewritten
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" migrate <roadmap_path> --to single|sqlite \
    [--output <path>]

# Add explicit outline Placement facts; target carrier follows its extension
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" migrate-placements <roadmap_path> --output <path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" migrate-types <roadmap_path> --output <path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" placement list <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" placement add-reference <roadmap_path> <work> <parent> [--rank N]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" placement move <roadmap_path> <placement_id> <parent> [--rank N]

# Node CRUD
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" add <json_path> <parent_id> "<label>" [--status pending] [--mode explore]
    [--obligation-key <key>]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" add <json_path> <parent_id> "<label>" --max-children 3 --max-rounds 2
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update <json_path> <node_id> --status completed
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update <json_path> <node_id> --label "新标签" --notes "备注内容"

# Explore budget (structural units) and exit criteria
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update <json_path> <node_id> --max-children 3 --max-rounds 2
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update <json_path> <node_id> --exit-criteria "判据文本"   # repeatable
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update <json_path> <node_id> --clear-budget --clear-exit-criteria
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" delete <json_path> <node_id>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" get <json_path> <node_id>

# Decisions
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" decide <json_path> <node_id> "问题" "答案" ["备注"]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" decisions <json_path> [<node_id>]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" remove-decision <json_path> <node_id> --index N
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" remove-decision <json_path> <node_id> --question "<问题文本>"

# Failure semantics & escalation
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" fail <json_path> <node_id> --error "失败原因" [--question "升级时给 Human 的问题"] [--max-attempts N]
#   attempts+1 / last_error / retry_backoff(封顶指数退避)；达阈值(默认3)挂 open_question 升级。不改 status。
#   执行侧元数据，需持租约（同 status）：非持有者写返回 E_LEASE_HELD。

# Dependencies — edges live outside the tree.
# Note: `edge` takes the action first and the path second, unlike every other
# command, because it is a command group (`git remote add` style).
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" edge add <roadmap_path> <from_id> <to_id> --type blocks|informs|supersedes|derives-from
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" edge list <roadmap_path> [--node <node_id>]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" edge remove <roadmap_path> <edge_id>

# Execution trace. `prompted-by` is written as plan -> trace when --under is present.
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" trace add <roadmap_path> --kind <kind> --body "..." [--under <plan_id>] [--from <trace_id>]
    [--obligation-key <key>] [--evidence "..."]...
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" trace list <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" trace get <roadmap_path> <trace_uid>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" trace prune <roadmap_path> <trace_uid> [--edge <edge_id>]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" context <roadmap_path> <node_id> [--include trace]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" promote <roadmap_path> <trace_uid> --under <plan_id> [--label "..."]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" promote <roadmap_path> <trace_uid> --accept \
    --approved-digest <digest> --idempotency-key <key> [--answer '<json object>'] \
    [--fault-stage before-commit|during-commit|after-commit-before-view]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" promote <roadmap_path> <trace_uid> --reject [--reason "..."]

# Deterministic reconciliation preview (read-only; no ChangeSet is applied)
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" reconcile <roadmap_path> <trace_uid>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" reconcile <roadmap_path> --trace <trace_uid> --trace <trace_uid>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" reconcile <roadmap_path> <trace_uid> --answer '<json object>'

# Reviewed ChangeSet apply; retries with the same key are idempotent
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" apply <roadmap_path> <proposal_id> \
    --approved-digest <digest> --idempotency-key <key> \
    [--answer '<json object>'] \
    [--fault-stage before-commit|during-commit|after-commit-before-view]

# Reviewed batch ChangeSet; duplicate novel findings share one WorkItem
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" apply-batch <roadmap_path> \
    --trace <trace_uid> [--trace <trace_uid> ...] \
    --approved-digest <batch_digest> --idempotency-key <key>

# Generic closed topology ChangeSet
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" changeset preview <roadmap_path> --changes '<json array>' \
    [--scope <node_uid>]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" changeset apply <roadmap_path> --changes '<json array>' \
    --approved-digest <digest> --idempotency-key <key> [--scope <node_uid>]

# Lease inputs accept display ids for Human convenience; the sidecar/database
# key and every emitted node_uid use the node's immutable uid.
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" lease claim <roadmap_path> <node_uid> --agent <agent_id> [--ttl 300]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" lease heartbeat <roadmap_path> <node_uid> --agent <agent_id>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" lease steal <roadmap_path> <node_uid> --agent <agent_id>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" lease release <roadmap_path> <node_uid> --agent <agent_id> [--force]

# Render and inspect
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" render <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" section <roadmap_path> [--max-depth 2] [--max-bytes N]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" section <roadmap_path> --all [--max-bytes N]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" link <json_path> <md_file>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" tree <json_path> [<node_id>] [--depth 3]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" path <json_path> <node_id>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" siblings <json_path> <node_id>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" focus <json_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" validate <json_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" stats <json_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" recommend-storage <roadmap_path> [--measure]
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" next <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" signals <roadmap_path>

# Scheduling query (read-only, derived) — see "## Scheduling query" below
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" ready <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" critical-path <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" impact <roadmap_path> <node_id>

# Process-state authority boundary
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" authority-check <project_root> [--exclude <path>]...
```

Missing positional arguments and unknown command-group actions fail with
`E_USAGE` instead of a Python traceback.

`reconcile` requires an explicit `obligation_key` on the trace. It compares that
key with plan nodes across the whole carrier, without inferring identity from
free text. One active exact match yields `covered`; a completed exact match
yields `refine` with a Human question; no match requires at least one trace
`evidence` item and yields `novel`; multiple exact matches yield `unresolved`
with a Human question and no `work.create` change. The command is a preview
only: it does not mutate the carrier or Markdown view. Proposal output uses
immutable UIDs for durable references and includes `base_revision` plus a
deterministic `proposal_id`.

`--answer '<json object>'` records an explicit Human decision. `dismiss` requires
`reason`; completed exact matches support `refine` actions `reopen`, `supersede`,
and `noop`; `reshape` accepts a closed `changes` list and applies it through the
same candidate-state validator as generic ChangeSets.

`promote --accept` is a compatibility adapter for the reviewed reconciliation
path. It recomputes the trace-scoped proposal (or recovers the original proposal
on an idempotent retry), verifies `--approved-digest`, and then delegates the
topology write and Markdown publication to the same ChangeSet apply path as
`apply`. It requires an idempotency key and rejects legacy `--under`, `--label`,
and `--reason` overrides; Human decisions belong in `reconcile --answer`. The
legacy direct topology write — the `apply_promotion` accept branch and the
`Roadmap.promote` `create_plan` consumer (`add_node` / `add_edge`) — was removed
in #234: `apply_promotion` no longer accepts `accept`, and `Roadmap.promote(...,
"accept")` raises `E_RECONCILIATION_REQUIRED` before any state machine runs. The
reviewed path is now the only writer; old `promotion` fields are compatibility
state rather than a second canonical write path.

Repeated `--trace` values produce one deterministic
`zj-reconciliation-batch/v1` response: duplicate trace references are removed,
UIDs are sorted, and the response includes per-trace proposals, disposition
counts, and a `batch_digest`. This remains a preview; it does not apply any
proposal.

`apply` accepts a reviewed proposal digest and applies covered or novel changes
as one ChangeSet. `apply-batch` accepts the batch digest and the same trace set;
novel findings sharing an obligation key converge on one WorkItem while every
Trace receives its own reconciliation record and provenance edge. Both return
`zj-changeset-receipt/v1`; the same idempotency key
returns the original receipt, while a stale base revision returns `E_CONFLICT`
and a digest mismatch returns `E_APPROVAL_MISMATCH`. A batch containing
`refine`, `reshape`, `dismiss`, or `unresolved` proposals is rejected with
`E_CHANGESET_INVALID` until a Human supplies the corresponding topology or
disposition decision. `--fault-stage` is a
deterministic validation seam: before-commit and during-commit leave canonical
state unchanged, while after-commit-before-view proves that a committed state
can be retried to repair its Markdown view without duplicating the mutation.

`migrate-placements` creates a new target artifact and never rewrites its source.
It projects every non-root plan node from ordered `children` into a
`kind: primary` Placement with immutable `work_uid`, `parent_uid`, and
zero-based `outline_rank`. `placement list` adds derived `work_id` and
`parent_id` fields for Human convenience. Existing target artifacts are refused.
`placement add-reference` and `placement move` change only outline placement;
they never copy or mutate the referenced WorkItem state.

`changeset preview/apply` accepts a JSON array of closed operations and emits a
`zj-changeset/v1` digest. Supported kinds are `work.create`, `work.patch`,
`work.coalesce`, `work.supersede`, `placement.put/move/reference`,
`edge.put/remove/replace`, `decision.append`, and `trace.disposition`. The apply
path evaluates the complete candidate state before committing; cycle, layer,
Placement, and structural errors leave the carrier unchanged.
When `--scope` is supplied, preview rejects every referenced WorkItem, Edge
endpoint, Placement endpoint, Decision target, or prompted-by Trace outside the
inclusive scope subtree. The scope is part of the reviewed digest, so apply
cannot silently widen or drop it; legacy tree-backed Placement ids are checked
against their derived primary facts before any materialization.

`migrate-types` creates a new artifact, classifies the root and nodes with
children as `group` and leaves as `work`, and preserves UIDs, decisions, status,
edges, leases, and source bytes. Once Placements exist, `tree`, `section`, and
`render` read them as the outline source; reference entries render with the
text marker `↪ reference (same WorkItem, not a copy):`. The `↪` glyph is a
redundant visual hint: removing it leaves the full plain-text semantics, so the
notation never depends on color or an icon alone. The marker names identity in
words instead of pointing at a primary display id, because display ids are
convenience addresses and are not durable references.

`render` writes the lightweight Markdown view: when there is a current focus it renders a radial view (ancestor chain always visible + focus subtree drilled down + non-focus siblings collapsed to a count), and falls back to a root tree at depth=2 when there is no focus; completed subtrees collapse, in_progress/blocked/open_question nodes force-expand; the tail carries a `ready` preview. `section` is bounded by default; use `--all` for an explicit full export and optionally cap its bytes. `focus` returns the first in-progress leaf.

`tree <roadmap_path> [node_id] [--depth N]` prints a box tree rooted at `node_id` (default `1`) up to `--depth`. `tree --anchor <id>` renders the radial view anchored at `<id>` (the ancestor chain + focus subtree + sibling counts); `--anchor` without a value anchors at the current focus, falling back to the root when none. For edge context one level deeper, use `context <node_id>` — the radial view's ancestor chain is already the broader context.

`recommend-storage` is a read-only advisory. It reports node/decision counts and
canonical and view bytes. It returns `keep-single`, `consider-sqlite`, or
`keep-sqlite` without writing indexes, migrating the roadmap,
or editing Markdown. When a recommendation names a different carrier it also
carries the exact command to act on it in `recommendation.command`
(`migrate <path> --to <carrier>`) — naming the command is not running it.
`--measure` adds local bounded-tree and full-section timings; timing thresholds
are advisory and machine-dependent.

## Process-state authority boundary

The carrier is canonical for Roadmap process state only: plan shape, current
status, process decisions, and next work. Product behavior, architecture, release
state, and correctness become durable claims only after they are established in
code/tests/runtime evidence and promoted to the appropriate ADR, design, or
contract.

Every `render` and `section` Markdown view carries this machine-readable envelope:

```text
<!-- zj-roadmap-authority/v1
role: process-state
durable-citation: forbidden
promote-via: ADR|design|contract|runtime-evidence
-->
```

`authority-check <project_root> [--exclude <path>]...` scans only files that could
carry durable facts. Process-state trees are out of scope: `docs/plans/`, `.git/`,
`.workbuddy/` (append-only agent memory), `node_modules/`, `tmp/`, the Roadmap
carrier itself, and any Markdown view carrying the `zj-roadmap-authority/v1`
envelope. `--exclude` is repeatable and project-relative; it declares one extra
file or directory (which need not exist in this checkout). It refuses the project
root and any path outside it, and every other path keeps being checked.
Exclusions change only the scan scope, never the judgement. It rejects both
direct citations of actual process artifacts and narrow, high-confidence claims
that use a Roadmap node's completed status as proof. Copied completion claims
remain detectable after the process artifact is cleaned up. A finding exits 1
and prints stable diagnostics:

```text
Error: E_PROCESS_AUTHORITY_LEAK: path/to/file.md:12: cites transient process artifact ...
```

A governance page may show one forbidden example by placing
`roadmap-authority-allow: governance-example` on the same line. The allowance is
line-local so it cannot mask the rest of a file.

## Carriers and explicit migration

The CLI selects storage from the path: a `.sqlite` / `.sqlite3` / `.db` file is
**sqlite**, anything else is **single-file** JSON. The carriers share one adapter
contract, so the same command works on any of them.

```bash
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" migrate <roadmap_path> --to single|sqlite \
    [--output <path>]
```

Both Markdown views are produced by **one** template in `roadmap.py`
(`compose_light_section` / `compose_full_section`); the carriers feed it their
own tree, chain and focus node. They used to keep separate copies of the
layout, and the second copy silently drifted — no `> 当前施工` line, no
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

## Scheduling query (read-only, derived)

Three read-only queries answer "what can I start next / what is the longest
outstanding chain / what does a change ripple into". All three are derived
**on read** from `blocks` edges only — never stored, never counters. They share
one module-level function in `roadmap.py`; both
carriers feed it their own data, so the two carriers print byte-identical
output. None of them takes the whole-graph lock: taking it would serialize
concurrent reads and could trip the lock-timeout exit code 2, which is a
writer's failure mode, not a reader's.

```bash
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" ready <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" critical-path <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" impact <roadmap_path> <node_id>
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
finished from unfinished in the impact set at a glance.

**`ready` ignores leases.** Readiness is decided by status and `blocks` edges
only: whether another agent holds a lease on a node does not remove it from the
set. A lease claims work; it does not hide it.

## Orchestration signals (read-only)

`signals` 是**只读** advisory：把「初始 roadmap 就绪后，现在可能需要编排」变成
一个可发现的确定性输出，不必等 Agent 先意识到要编排、也不必让 Human 先补一轮
CLI 认知。`next` 是另一个早已存在、此前未登记的只读建议（关键路径优先的就绪节点）。

```bash
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" next <roadmap_path>
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" signals <roadmap_path>
```

`signals` 输出 `zj-orchestration-signals/v1`：`checked` 是实际检查过的 plan 节点数
（0 条信号 ≠ 没检查过）、`signal_count`、以及按 `(node, kind)` 排序的 `signals[]`。
每条带 `node` / `label` / `kind` / `detail` / `suggested_action`。规则只覆盖 roadmap
**自身可机械判定的结构状态**：

| kind | 触发条件 | 为什么值得 Human 确认 |
| --- | --- | --- |
| `completed_with_open_question` | 节点 `completed` 但仍挂 `open_question` | 待决问题可能被「已完成」盖住，需要拆 sibling 或重开 |
| `budget_exhausted` | `max_children` / `max_rounds` 已用尽 | 再 `add` 或重开会被 `E_BUDGET_EXCEEDED` 挡下，要收敛 / 提高预算 / 拆分 |
| `cleared_exit_criteria` | 判据被显式清空（`exit_criteria=[]`）且节点未 `completed` | 正在推进却没有完成判据，要补回或显式记录放弃理由 |

刻意不报「从未设置判据」的节点：那在新图上遍地都是，会把信号节变成噪声。也
不判断「判据与事实是否相符」——那需要代码、测试或 runtime evidence，属于
process-state 权威边界之外（见 `SKILL.md` 的权威边界小节）。

**边界**：命令不拿整图锁、不改 carrier、不改 Markdown、不产出 ChangeSet；
`suggested_action` 只是文本，**把命令写出来 ≠ 替人跑**。编排结果仍由 Human 用
`decide` + `changeset preview/apply`（preview + approved digest）显式落盘。

`signals --as-changeset` 把信号转成**候选** ChangeSet（仍是只读输出，不落盘）：每条
信号先落一条 `decision.append` 记录决策，`cleared_exit_criteria` 信号在显式给出
`--criterion <文本>` 时再补一个 `work.patch(exit_criteria)`。Human 拿到候选后按需
编辑（尤其判据内容，**绝不替人猜**），再走 `changeset preview/apply` 完成一次确认——
这就是 #245 切片 2 的「信号 → 候选 ChangeSet → 一次 Human 确认」收敛路径：复用既有
digest / `--idempotency-key` / `--scope`，不开第二套 canonical 写入命令。该 flag 不
增加命令总数，也不把 `signals` 变成写命令（`signals` 仍在 LOCK_COMMANDS 之外）。

`render` 的轻量视图把信号折成 `<details>` 摘要，`section` 平铺成 `### 编排信号`
供 grep；两个视图共用同一份条目模板与 5 条上限。**无信号时两者输出逐字节不变**，
由 `test_orchestration_signals.py` 的 `compose_*` 字节断言与无信号图 CLI 控制例、
`test_blocked_chain_single_file.py::Slice06` 的无阻塞三态归一化控制例，以及
`test_cross_carrier_render.py` 的双 carrier 逐字节断言共同钉住。
（Slice06 里那条对历史 commit `c2e5a64` 的基线比对因 radial render 有意改变
有焦点视图而被 skip，不作为本结论的依据。）

## Edges

Edges are a layer orthogonal to the tree: `blocks` (hard dependency), `informs`
(context only), `supersedes` (replaces another node), `derives-from` (provenance).

`blocks` and `supersedes` may not form cycles. Plan-to-plan `derives-from` and
`informs` retain their non-scheduling cycle behavior. Trace causal edges have
stricter contracts: `mainline` and `reference` are trace→trace,
`prompted-by` is plan→trace, and cross-layer `derives-from` is trace→plan;
`mainline`, `prompted-by`, and cross-layer `derives-from` share one acyclic
causal graph. Violations return `E_LAYER_VIOLATION` or `E_CYCLE` before anything
is written. A node may not `blocks` itself. Pointing an edge at a node that does
not exist fails with `E_NODE_NOT_FOUND` (exit 1) — dangling edges are never
created silently.

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
removed **before** the node records, so an interrupted delete leaves "edges
gone, node still there" — rerunnable — rather than a dangling edge. When no
edge was removed the extra line is not printed, so `delete` stays
byte-identical to its pre-edge output. A dangling edge that does appear
(hand-edited file, or an interrupted write) is reported by `validate`, not
silently scheduled around.

`compressed_from` is a UID reference outside the edge table. Deleting a node or
subtree still cited by a surviving trace is refused with `E_REFERENCED`; the
edge cascade never leaves that provenance dangling.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic failure (invalid argument, missing node, invalid artifact) |
| 2 | Lock timeout (another writer holds `<roadmap_path>.lock/`) |
| 3 | `E_BUDGET_EXCEEDED` — an explore node's `max_children` or `max_rounds` cap was hit |

Budget failures print `Error: E_BUDGET_EXCEEDED: <detail>` on stderr. Branch on
the code, never on the human-readable text after it. The cap is enforced on both
carriers (single-file JSON and sqlite) by the same shared helper, so the two
never disagree on what counts as a start or a child.

| Code | Raised by |
|------|-----------|
| `E_CYCLE` | a `blocks` or `supersedes` edge, or a trace causal edge, that would close its graph's cycle |
| `E_NODE_NOT_FOUND` | an edge pointing at a node that does not exist |
| `E_INVALID_STATUS` | `add` / `update --status blocked` (blocked is derived, not settable) |
| `E_LEASE_HELD` | writing a lease holder's fields on a node someone else holds (or with a stale fencing token) |
| `E_CONFLICT` | `--if-rev <sha>` no longer matches the current revision |
| `E_SCOPE` | an `--scope`-bearing write aimed outside that node's subtree |
| `E_RECONCILE_KEY_MISSING` | reconciliation input has no explicit deterministic `obligation_key` |
| `E_NOVELTY_EVIDENCE_MISSING` | no exact match exists but the finding has no novelty evidence |
| `E_PROPOSAL_NOT_FOUND` | the proposal id is absent or no longer valid for the current revision |
| `E_APPROVAL_MISMATCH` | the reviewed digest differs from the current proposal |
| `E_IDEMPOTENCY_CONFLICT` | an idempotency key was already used for different proposal material |
| `E_CHANGESET_INVALID` | the proposal disposition or final candidate state cannot be applied |
| `E_RECONCILIATION_REQUIRED` | direct promotion acceptance is disabled; use reviewed reconciliation + ChangeSet apply |
| `E_INJECTED_FAILURE` | the explicit fault-injection validation seam was triggered |
| `E_PROCESS_AUTHORITY_LEAK` | durable code/docs cite Roadmap process state or artifacts as evidence |

All listed errors exit 1. `E_CYCLE` may surface through `edge`, `trace add`, or `promote`,
because all three can add an edge governed by an acyclic contract.
`E_NODE_NOT_FOUND` is raised by `edge`; pre-existing commands still raise
`KeyError`/`ValueError` with their original wording, so their output is unchanged.

### Scope tokens

`--scope <node>` confines the write to `<node>` and its subtree (inclusive). A
write aimed anywhere else fails with `E_SCOPE` **naming the allowed scope**, so
the caller can correct the call instead of editing someone else's subtree. The
check walks parent links upward from the target, so it costs O(depth) and both
carriers answer it with the same code.

Omitting `--scope` means unrestricted, not read-only: the CLI cannot tell a
subagent from a planner or a Human, and "read-only by default" would also block
the lease holder from writing `status` on the node it holds. Read-only is a
policy the *parent* agent enforces by always handing down a `--scope`.

### Field-level ownership

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

### Failure semantics & escalation

`fail` records an execution failure on a node:

```bash
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" fail <json_path> <node_id> --error "..." [--question "..."] [--max-attempts N]
```

- `attempts` increments; `last_error` and `last_failed_at` are recorded; `retry_backoff`
  is set to a capped exponential `min(60 * 2^(n-1), 3600)` seconds, recomputed every fail.
- When `attempts` reaches the threshold (default `3`, overridable per node via
  `--max-attempts`), the node gets an `open_question` field
  `{question, raised_at, raised_by, attempts}` — the marker the md queue renders.
- **`fail` never writes `status`.** `blocked` stays purely derived from `blocks` edges
  (blocked is derived, not stored). Escalation is expressed by the `open_question`
  marker, not by changing status — so the `[!]` icon keeps meaning "dependency-blocked" only.
- `fail` touches executor-owned metadata, so it passes through the same lease gate as
  `status`: a non-holder write is rejected with `E_LEASE_HELD`.

Every `migrate --to <carrier>` carries edges, decisions, node leases and their
audit events across. Dropping any of them would be silent data loss that looks
like success at the command layer.

Markdown is a generated view and is never imported back into roadmap state. The
old `import` command is intentionally not supported; use
`migrate --to single|sqlite` for storage conversion.

`unlock` is an explicit cleanup operation:

```bash
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" unlock <json_path>
```

Run it only after confirming that no roadmap CLI writer is still active.

## Worked example

```bash
# Human says: 「把文章处理后端走通」
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" tree roadmap.json 1-1-1
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" add roadmap.json 1-1-1 "文章处理后端流水线" --status in_progress
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" decide roadmap.json 1-1-1-5 "后端用什么？" "Python + FastAPI" "轻量够用"
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" update roadmap.json 1-1-1-5 --status completed --notes "API: POST /articles/convert"
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" render roadmap.json
python3 "$SKILL_ROOT/scripts/roadmap_cli.py" section roadmap.json --all
```

## Script location and write safety

Scripts live inside this skill, addressed by the `$SKILL_ROOT` path basis declared in [SKILL.md](../SKILL.md):

```text
$SKILL_ROOT/scripts/roadmap.py        # core library
$SKILL_ROOT/scripts/roadmap_cli.py    # CLI entry point
```

The Agent resolves `$SKILL_ROOT` to an absolute path when the skill is loaded. The command cwd is the target project, never the skill directory.

Write commands use `<roadmap_path>.lock/` and atomic JSON/Markdown writes. Do not
run write commands for the same roadmap in parallel. A stale lock is not cleared
automatically; the timeout reports its owner and path so it can be checked before
`unlock`. Migration locks both source and destination and builds/validates a
temporary artifact before the final write, so a failed migration leaves
the source untouched.

Deleting a node recursively deletes its children; confirm the target first.

## 只读可视化（独立 viz 包）

viz 是独立 Python 包，**不新增 roadmap_cli 顶层命令**（命令清单冻结测试保持不变）。
所有产物路径必须 Human 显式给出；`--out` 不传则不写 HTML 文件（ADR 0010），只打印
摘要与 anchor；`--dependency` / `--context` 同样无默认值、不落 cwd。

```bash
PYTHONPATH="$SKILL_ROOT" python3 -m viz.cli <roadmap.json> --out X.html \
    [--dependency X.dependency.json] [--context X.context.json] [--focus <节点id>]
```

设计要点见[可视化设计要点](viz-design.md)；几何校验与 dagre 溯源见
[VENDOR.md](../viz/VENDOR.md)。

S1 追加只读入口（路径一律显式，ADR 0010）：

- `--ir X.ir.json` — 输出冻结的 view-ir（`zj-roadmap-view-ir/v1`，字段集合由守卫锁定）。
- `--receipt X.receipt.json` — 读上次 baseline 并写回；缺失/损坏时 fail-closed 回退全量视图，
  receipt 不进 carrier、不参与 view-ir 计算，落点须在 gitignored 隔离区。
- `--delta X.delta.json` — 输出 `added / changed / removed / stable-folded`。
- `roadmap` 位置参数同时接受 JSON 与 SQLite carrier（`.sqlite/.sqlite3/.db`）；同 anchor 下
  两 carrier 的 HTML / Mermaid / dependency / context / view-ir 逐字节相同。

## Demos

- `demos/roadmap_demo.json` — 历史静态示例（2026-06-22），仅用于说明 carrier 形状；不作为回归语料。
- `demos/ZJ_ROADMAP_section_demo.md` — 同上，历史渲染样例。
- `demos/roadmap_viz_sample.json` — **活跃语料**（21 节点 / 15 条 blocks 边 / 3 条一等债务），viz 单测与几何校验都用它。
- `tests/verify_real_plan_corpus.py` — read-only real Markdown-plan corpus migration contract.

## 高级拓扑语义（reconciliation / Placement / ChangeSet）

当前 reconciliation preview 只接受显式 `obligation_key`：先用确定性 key
匹配全图 plan 节点，再输出 `covered`、`refine`、`reshape`、`novel`、
`dismiss` 或 `unresolved` proposal。`novel` 必须由 trace 的 `evidence`
支撑；多个 exact match 只提出 Human 问题，不自动创建 WorkItem。Human
答案通过 inline JSON 传给 `--answer`：`dismiss` 必须有 reason，完成项的
`refine` 支持 reopen/supersede/noop，`reshape` 携带闭合 ChangeSet changes。
可以用重复的 `--trace` 一次生成批量 preview；`reconcile` 本身只读，单条
ChangeSet 经 digest 审批后显式 `apply`，重复 obligation 的 Trace 批次经
`apply-batch` 合并为一个 WorkItem 并保留所有来源。

Placement 迁移也是显式的：`migrate-placements <source> --output <target>`
按目标扩展名选择 JSON 或 SQLite carrier，把旧的 ordered `parent`/`children`
投影成 primary Placement，并保留源文件字节不变。`placement list <roadmap>`
只显示 Placement 及其 Work/parent 的 display-id 投影；`outline_rank` 只表达
展示顺序，不表达调度或因果关系。已有 roadmap 可用 `placement add-reference`
添加共享 Work 的第二个 outline context，用 `placement move` 移动 Placement；
这两者不复制 WorkItem 的状态、决策或租约。

通用拓扑 ChangeSet 可用 `changeset preview/apply` 走同一套候选状态校验，
支持 `work.create/patch/coalesce/supersede`、Placement put/move/reference、
Edge put/remove/replace、Decision append 和 Trace disposition。已迁移的
roadmap 可用 `migrate-types --output` 将带 children 的 plan 节点分类为
`group`、叶节点分类为 `work`；有 Placements 时 `tree`、`section`、`render`
从 Placement 事实投影，并以文本 `↪ reference (same WorkItem, not a copy):`
显示引用上下文（`↪` 仅为冗余视觉提示，语义由文字承载）。
ChangeSet 也可带 `--scope <node_uid>`；preview 会展开 Edge/Placement 的
不透明引用并拒绝所有越出该子树的 Work、Decision、Trace 或拓扑端点，scope
同时进入 approved digest。

## 编排信号与候选 ChangeSet

初始 roadmap 就绪后，`signals` 与 md 尾部的折叠小节负责让「现在可能需要编排」
成为可发现、可确认的信号，而不是靠 Human 记得去触发。它只报 roadmap 自身可
机械判定的结构状态（`completed` 仍挂 `open_question`、探索预算触顶、判据被显式
清空），**不推断产品事实或外部证据** —— 后者属于 process-state 权威边界之外。
`signals` 不写入、不产出 ChangeSet；`suggested_action` 只给可确认的
next-action 文本，**把命令写出来 ≠ 替人跑**，决策仍用 `decide` 落盘、结构变更
仍走 `changeset preview/apply`。无信号时两个 Markdown 视图逐字节不变。

`signals --as-changeset` 把信号转成**候选** ChangeSet（仍是只读输出，不落盘）：
每条信号先落一条 `decision.append`，`cleared_exit_criteria` 信号在显式给出
`--criterion <文本>` 时再补 `work.patch(exit_criteria)`。Human 拿到候选后按需
编辑（尤其判据内容，绝不替人猜），再走 `changeset preview/apply` 一次确认 ——
复用既有 digest / `--idempotency-key` / `--scope`，不开第二套写入命令。
该 flag 不增命令数。

## 载体迁移与推荐（只读建议）

`recommend-storage` 只读取事实源和派生文件，**但从不动手**：输出 `keep-single`、
`consider-sqlite` 或 `keep-sqlite`，不写索引、不迁 carrier、不改写 Markdown。给出迁移
目标的档位会在 `recommendation.command` 里附上那条显式命令
（`migrate <path> --to <carrier>`）让人去跑——把命令写出来 ≠ 替人跑。

换 carrier 只能靠 `migrate <path> --to single|sqlite`：源文件一个字节都不改，目标已
存在或与源同 carrier 都直接拒绝。**没有任何命令会自动替你换事实源**，所以「现在
哪个产物是事实源」永远是你上一次显式做出的那个。租约与它的审计事件会一起走
（带过去的那把锁在新 carrier 上仍然生效）。
