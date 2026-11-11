# Roadmap data model

Use this reference when creating, inspecting, renaming, or updating roadmap nodes.

## Node fields

| Field | Type | Meaning |
|------|------|---------|
| `id` | string | Number such as `1`, `1-1`, `1-1-1` |
| `label` | string | Node name |
| `status` | string | Settable: `pending` / `in_progress` / `completed`. `blocked` is **derived only** — never set, never stored (see below) |
| `mode` | string | `explore` / `exploit` |
| `parent` | string\|null | Parent node id; `null` for the root |
| `children` | list | Child node ids |
| `decisions` | list | Decision records `[{q, answer, note}]` |
| `notes` | string | Free-form notes |
| `budget` | dict | Structural cap `{max_children, max_rounds}`; absent or missing sub-key = unlimited |
| `exit_criteria` | list | Checkable completion conditions (strings) |
| `rounds` | int | How many times the node has been started (entered `in_progress`) |
| `obligation_key` | string|absent | Explicit deterministic identity key used by reconciliation preview |
| `node_type` | `group`\|`work`\|absent | Typed plan node after explicit type migration; groups own decomposition, works are atomic leaves |

Trace nodes may also carry `obligation_key` and an optional `evidence` list.
The key is never inferred from `label` or `body`; it is the exact-match input
for `reconcile`, while evidence is required when a finding has no exact plan
match and is proposed as `novel`.

## Reconciliation preview

```bash
python roadmap_cli.py reconcile <roadmap_path> <trace_uid>
```

The read-only preview scans the whole plan layer using the trace's explicit
`obligation_key`. One exact match produces `covered`; no match requires trace
evidence and produces `novel`; multiple exact matches produce `unresolved` with
a Human question and no `work.create` change. The proposal contains the
immutable candidate UIDs, `base_revision`, and a deterministic `proposal_id`.
It does not apply a ChangeSet or update Markdown.

## Batch reconciliation and ChangeSet apply

Repeated `--trace` flags create one deterministic batch envelope:

```bash
python roadmap_cli.py reconcile roadmap.json \
  --trace <trace_uid> --trace <trace_uid>
```

Repeated trace UIDs are deduplicated and the remaining UIDs are sorted. The
batch contains one proposal per trace, a `covered`/`novel`/`unresolved`
summary, duplicate groups, and a `batch_digest`; it is still a read-only
preview. The digest carries the batch base revision, so applying it after a
concurrent write returns `E_CONFLICT`. Applying a valid batch coalesces novel
findings with the same obligation key into one WorkItem and links every Trace.

After Human review, apply one proposal with its exact digest and a retry key:

```bash
python roadmap_cli.py apply roadmap.json <proposal_id> \
  --approved-digest <proposal_digest> --idempotency-key <key>
```

The receipt is persisted as operational metadata while the trace disposition
and any novel WorkItem are canonical state. Reusing the same key returns the
same receipt; a changed proposal or digest with that key is rejected.

## Placement

Placement separates Human outline position from WorkItem identity and
scheduling. A canonical placement has this shape:

```json
{
  "id": "p1",
  "kind": "primary",
  "work_uid": "<immutable work uid>",
  "parent_uid": "<immutable outline parent uid>",
  "outline_rank": 0
}
```

`outline_rank` is zero-based sibling order only; it never implies a `blocks`
edge, priority, or execution sequence. The migration command creates a new
artifact, projects each non-root plan node from ordered `children`, preserves
all Work UIDs and edges, and leaves the source byte-identical:

```bash
python roadmap_cli.py migrate-placements source.json --output target.sqlite
python roadmap_cli.py placement list target.sqlite
```

The list command derives `work_id` and `parent_id` for display. Those IDs are
convenience addresses, not durable Placement or Work identity.

```bash
python roadmap_cli.py placement add-reference roadmap.json <work_uid> <parent_uid>
python roadmap_cli.py placement move roadmap.json <placement_id> <parent_uid> --rank 1
```

Reference and move operations only change Placement facts. They do not copy the
WorkItem or duplicate its status, decisions, leases, or completion state.

## Typed group/work migration

```bash
python roadmap_cli.py migrate-types source.json --output typed.json
```

The explicit migration classifies the root and every plan node with children as
`node_type: group`; plan leaves become `node_type: work`. It copies the source
to a new JSON or SQLite artifact, preserves UIDs, Decisions, Status, Edges,
leases and source bytes, and refuses an existing target. A migrated work node
cannot receive decomposition children; adding a child to a migrated group
continues to use the existing tree API.

## Generic ChangeSet

The closed ChangeSet seam accepts an inline JSON array:

```bash
python roadmap_cli.py changeset preview roadmap.json --changes '[
  {"kind":"work.patch","work_uid":"<uid>","patch":{"label":"Renamed"}},
  {"kind":"edge.put","from_uid":"<uid>","to_uid":"<uid>","type":"blocks"}
]'
```

`changeset apply` requires the exact preview digest and an idempotency key. The
candidate state is copied, all operations are applied, and final validation is
performed before either carrier commits. Supported operation kinds are
`work.create`, `work.patch`, `work.coalesce`, `work.supersede`,
`placement.put/move/reference`, `edge.put/remove/replace`, `decision.append`,
and `trace.disposition`. An optional `scope` is an inclusive plan subtree: the
preview expands opaque Edge and Placement references and rejects any operation
whose WorkItem, endpoint, Decision target, or prompted-by Trace escapes that
subtree. The scope is included in the digest and is therefore part of Human
approval. Omitting it preserves the existing unrestricted behavior.

When a Placement array exists, `tree`, `section`, and `render` use it as the
Human outline source. Primary placements retain the old tree shape; reference
placements are text-marked `↪ reference (same WorkItem, not a copy):` and never duplicate WorkItem state. The arrow is a redundant visual hint; the text alone carries the meaning in plain-text and screen-reader linear reading.

## Budget and exit criteria

`mode: explore` says "there is unknown here"; `budget` says how far the
exploration may go, and `exit_criteria` says when an `exploit` node is done.

- `max_children` — how many children this node may grow. `add` under a node at
  its cap fails with `E_BUDGET_EXCEEDED` (exit code 3) and changes nothing.
  Shrinking the cap does not reject children that already exist.
- `max_rounds` — how many times the node may be **started**. A start is any
  transition into `in_progress`; the first one writes `rounds: 1`. Reopening a
  node past its cap fails the same way. A node created by `init` counts as
  already started.
- Units are structural, never tokens: token counts are not comparable across
  models and cannot be estimated while planning. Use `--fields` / `--format`
  for token economy instead.
- `exit_criteria` is stored and returned, never evaluated — the CLI cannot judge
  natural language, and an unmet criterion does not block completion. Treat it
  as the checklist a Human or Agent reads before ticking `[x]`.

```bash
python roadmap_cli.py update roadmap.json 1-2 --max-children 3 --max-rounds 2
python roadmap_cli.py update roadmap.json 1-2 --exit-criteria "三项对比跑完" --exit-criteria "结论写进 decisions"
python roadmap_cli.py update roadmap.json 1-2 --clear-budget --clear-exit-criteria
```

Neither `budget` nor `exit_criteria` appears in the Markdown view by default;
they live in the fact source and in `get` output.

## Status and mode display

| Status | Icon | Meaning |
|--------|------|---------|
| `pending` | `[ ]` | Not started |
| `in_progress` | `[~]` | In progress |
| `completed` | `[x]` | Completed |
| `blocked` | `[!]` | Blocked — derived on read from `blocks` edges; not a stored status |

| Mode | Tag | Meaning |
|------|-----|---------|
| `explore` | `[X+]` | Direction, scope, or priority is still being explored |
| `exploit` | `[Y+]` | Direction is settled and work is being deepened |

Tree output uses `[status icon][mode tag] id. label`.

## Blocked is derived, never stored

`blocked` and `blocked_reason` are computed **on read** from `blocks` edges —
the edges are the only source of truth. Nothing writes them into the carrier.

- A node is blocked when a `blocks` edge points at it whose `from` node is not
  `completed`. `blocked_reason` lists the ids of those edges, so a stalled node
  can be explained rather than just reported.
- `get <node>` adds `blocked: true` and `blocked_reason: [...]` to the node it
  returns. When nothing blocks it, **both fields are absent** — not `false`.
- The tree and Markdown views render a blocked node with the `[!]` icon, so the
  Human view and the Agent view cannot disagree. `blocked_reason` stays in `get`:
  a tree line has no room for an edge-id list, and the Human reading it wants the
  icon, not the ids.
- `--status blocked` is refused with `E_INVALID_STATUS` (exit code 1). Letting a
  Human write `blocked` would create a second source of truth that can disagree
  with the edges.
- `informs`, `derives-from` and `supersedes` edges never block.

```bash
python roadmap_cli.py edge add roadmap.json 1-1 1-2 --type blocks
python roadmap_cli.py get roadmap.json 1-2     # + "blocked": true, "blocked_reason": ["e1"]
python roadmap_cli.py update roadmap.json 1-1 --status completed
python roadmap_cli.py get roadmap.json 1-2     # both fields gone, same read
python roadmap_cli.py edge remove roadmap.json e1
python roadmap_cli.py get roadmap.json 1-2     # both fields gone, same read
```

## The blocked chain in Markdown

The tree stays the Human's main view and edges do not enter it by default. But a
tree line can only carry an icon, so it cannot answer "who is holding this up".
When **anything is blocked**, both Markdown views gain a short section that does:

```markdown
<!-- `render` — the Human's md file: collapsed, one line of sight -->
<details><summary>阻塞链：2 个节点被阻塞</summary>

- 1-2. 实现 ← e1: 1-1. 设计 [ ]
- 1-3. 上线 ← e2: 1-1. 设计 [ ], e3: 1-2. 实现 [ ]

</details>

<!-- `section` — explicit export: plain, greppable -->
### 阻塞链

- 1-2. 实现 ← e1: 1-1. 设计 [ ]
```

Both lists are the same data rendered twice. The difference is deliberate:

| View | Form | Why |
|------|------|-----|
| `render` (written into the linked md file) | collapsed `<details>` | dependency info is there when wanted and out of the way when it isn't — you should not have to read a DAG to see progress |
| `section` (stdout) | plain `### 阻塞链` | it is consumed by pipes and greps; HTML there is noise |

There is no `--deps` flag. The blocked chain ships in the collapsed form, and
`section --all` is the non-collapsed answer to the same question.

At most 5 blocked nodes are listed (sorted by id, `BLOCKED_CHAIN_LIMIT`); anything
beyond that is folded into a final line that says how many were dropped, and the
summary reports the **true total**, not the number shown. A summary that quietly
under-reports is worse than no summary.

Every entry names the blocked node, the edge ids holding it up, and each of those
predecessors with its current icon — omitting the predecessor would send the
Human back to counting JSON to find out who to chase.

**When nothing is blocked, neither view changes by a single byte.** That is a hard
acceptance criterion, not a hope; a control case renders the same roadmap with a
pinned pre-edge implementation from the test fixtures and compares bytes.

Deriving instead of storing is a deliberate trade: a stored `blocked` needs a
list of "when to recompute" triggers (add edge, remove edge, predecessor
completed, `delete`, `supersedes`, carrier migration…), and missing one is
silent staleness. Recomputing per read is O(V+E) — the write commands already
load the whole graph.

## Scheduling query (read-only, derived)

The three scheduling queries (`ready`, `critical-path`, `impact`) are computed
from `blocks` edges on every read — no counters, no stored fields (a counter would
be a second source of truth next to the edges,
exactly the thing the derived-`blocked` decision set out to kill).

- `ready(node)` = `status == pending` **and** no `blocks` predecessor with
  `status != completed`. It is a work-claiming query, so `in_progress` is
  excluded even though it is technically "unblocked" — the set answers "what can
  I start next", not "what is not blocked".
- `critical_path` walks only `blocks` edges among nodes with `status !=
  completed` and returns the single longest chain. A completed node is dropped
  from the induced subgraph first, so finishing a predecessor shortens the chain
  in the very next read. Ties (equal-length chains) break by the smallest start
  id to keep the output deterministic across reads.
- `impact(node)` follows `blocks` edges downstream from `node` and returns every
  reachable node except `node` itself, sorted by id. It is the "if I change this,
  what must I re-check" view; completed downstream nodes are included on purpose —
  a finished successor that depends on a changed predecessor is exactly the rework
  risk worth surfacing. `informs` / `derives-from` / `supersedes` edges do not
  carry scheduling, so they never appear in an impact set.

In every query, "unfinished" means `status != completed` and "blocks" means the
`blocks` edge type — the same boundary `blocked` uses. `ready` does not consult
leases: a node another agent has claimed still appears in the ready set, because
readiness answers "what is unblocked", not "what is unclaimed". That clause is
left as one explicit branch, not a flag, so adding lease-awareness later touches
one place.

## Node naming

Node names must be **self-explainable**: the name alone should say what will be done. Use the parent as context for the complete scope.

- Good: `文章处理后端流水线`, `数据库层异步IO重构`, `用户认证OAuth2集成`
- Avoid generic names such as `优化`, `重构`, `修复`, `处理`, or `完成`.

When using `add` or `update --label`, check that the name is self-explainable. Warn the Human about a generic name, but may continue.

## Safe label changes

When `update --label` changes the meaning of a node (not just its wording), ask:

> "`node({id}. {旧name})` 将更新为 `node({id}. {新name})`，是否要新建 sub-node 对应偏差，避免跟踪遗漏？"

After the Human answers:

1. If yes, run `update --label`, then immediately `add` a child with the old name and `pending` status.
2. If no, run `update --label` without an extra node.

Meaning shift examples:

- Triggers: `文章+视频处理` → `文章处理` (scope narrowed); `日志系统` → `文档系统` (subject replaced).
- Does not trigger: `文章处理` → `文章处理流水线` (wording refined).

## Parent status synchronization

After `update --status`, `add`, or `delete`, the system synchronizes status upward:

- All children `completed` → parent becomes `completed`.
- Any child is not `completed` → parent cannot remain `completed` and is downgraded to `in_progress`.

The cascade continues through ancestors to the root.

## 依赖边、派生状态与调度语义

依赖是树之外的一层正交边：`blocks` 是硬依赖，`supersedes` 表示取代关系，
两者各自不许成环并会返 `E_CYCLE`。plan→plan 的 `informs` / `derives-from`
只是上下文与来源追溯，允许成环。trace 因果边另有更严格的层方向与无环规则：
`mainline`、`prompted-by`、跨层 `derives-from` 共同构成无环因果图，`reference`
允许成环。删节点会级联删掉触及它的边并报告条数——边不能比它的节点活得久。

`blocked` / `blocked_reason` 是**读取时从 `blocks` 边派生的，永不落盘**：
`get <node>` 在有未完成前驱时附带这两个字段（reason 是阻塞它的边 id 列表），
前驱一完成或边一删，同一次读里就消失；`tree` / md 渲染里同一个节点显示 `[!]`，
Human 视图与 Agent 视图不会对同一事实给出两个答案。`--status blocked` 被拒并返
回 `E_INVALID_STATUS`（退出码 1）——人写的 blocked 会与边推导出的 blocked 打架。

树的一行只装得下一个图标，装不下"被谁挡住"。所以当**有东西被阻塞**时，md 两个
视图都多出一小节阻塞链，每条说清哪个节点被哪几条边挡住（含边 id 与前驱）：
`render` 写进关联 md 文件时把它折进 `<details>`（依赖图不占视线），`section`
把它打平成 `### 阻塞链`（那是给管道用的）。最多列 5 个节点，其余写明数量不静默
丢掉。**没有任何东西被阻塞时，两个视图的输出一个字节都不变**——这条有控制例守着，
不是"应该差不多"。

调度查询（`ready` / `critical-path` / `impact`）是**读取时从 `blocks` 边派生**的，
只读、不拿整图锁：`ready` 是"现在能开工哪些节点"（pending 且无未完成 `blocks` 前驱，
`in_progress` 不算），`critical-path` 是"最长的未完工 `blocks` 链"（已完成节点不计入、
平局取最小起点 id），`impact <node>` 是"改这个节点会波及哪些下游"（只沿 `blocks` 顺流、
不含自身、含已完成下游以预警返工）。三者边界与 `blocked` 一致——只有 `blocks` 参与；
两个载体输出逐字节相同。

两个载体（single-file JSON、sqlite）对边的行为完全一致，同一套验收跑两遍：`migrate --to <carrier>` 会把边一起带走。
两个载体的两个 Markdown 视图（`render` 写进 md 的轻量视图与 `section` 的导出视图）
共用同一份模板，逐字节相同——模板曾各抄一份并漂移，抄两份本身就是缺陷。
