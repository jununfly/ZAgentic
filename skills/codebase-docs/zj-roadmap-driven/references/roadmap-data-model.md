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

There is no `--deps` flag. Story 45 asked for "a collapsed section **or** a
separate `--deps` output"; the collapsed form is the one that shipped, and
`section --all` is the non-collapsed answer to the same question.

At most 5 blocked nodes are listed (sorted by id, `BLOCKED_CHAIN_LIMIT`); anything
beyond that is folded into a final line that says how many were dropped, and the
summary reports the **true total**, not the number shown. A summary that quietly
under-reports is worse than no summary.

Every entry names the blocked node, the edge ids holding it up, and each of those
predecessors with its current icon — omitting the predecessor would send the
Human back to counting JSON to find out who to chase.

**When nothing is blocked, neither view changes by a single byte.** That is a hard
acceptance criterion, not a hope; a control case renders the same roadmap with the
pre-P1 implementation (`git show a8ee1b9:...`) and compares bytes.

Deriving instead of storing is a deliberate trade: a stored `blocked` needs a
list of "when to recompute" triggers (add edge, remove edge, predecessor
completed, `delete`, `supersedes`, carrier migration…), and missing one is
silent staleness. Recomputing per read is O(V+E) — the write commands already
load the whole graph.

## Scheduling query (read-only, derived)

The three scheduling queries (`ready`, `critical-path`, `impact`) are computed
from `blocks` edges on every read — no counters, no stored fields (Story 24 is
deferred to P3; a counter would be a second source of truth next to the edges,
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
`blocks` edge type — the same boundary `blocked` uses. The lease clause in the
spec's readiness rule (Story 20) is P2's work and is not implemented yet; it is
left as one explicit branch, not a flag, so adding it later touches one place.

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
