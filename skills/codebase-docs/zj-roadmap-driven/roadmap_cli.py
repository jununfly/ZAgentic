"""
zj-roadmap-driven CLI — 路线图确定性操作入口

每条命令输入确定 → 输出确定，Agent 可直接拼命令，无需推断。

用法:
  python roadmap_cli.py <command> <args...>

命令:
  init    <roadmap_path> --title "..." [--description "..."] [--md-file "..."]
              [--storage single|bundle] [--snapshot-interval N]

  add     <json_path> <parent_id> "<label>"
              [--status pending|in_progress|completed]   # blocked 派生，不可设
              [--mode explore|exploit]
              [--max-children N] [--max-rounds N]
              [--exit-criteria "判据"]...

  update  <json_path> <node_id>
              [--label "..."] [--status ...] [--mode ...] [--notes "..."]
              [--max-children N] [--max-rounds N]
              [--exit-criteria "判据"]...
              [--clear-budget] [--clear-exit-criteria]

  预算触顶（节点长太多子节点 / 被开工太多次）返回 E_BUDGET_EXCEEDED，退出码 3。

  delete  <json_path> <node_id>              # 删除节点及所有子节点
                                            # 级联删掉触及被删子树的边，并报告条数

  edge    add <json_path> <from> <to> --type blocks|informs|supersedes|derives-from
                                            # 记一条依赖边；只有 blocks 不许成环
  edge    list <json_path> [--node <id>]     # 列出边，可按节点过滤入边与出边
  edge    remove <json_path> <edge_id>       # 删掉一条边
  edge    migrate <json_path>                # 存量显示 id 边一次性转成 uid（#106 S4）

  get     <json_path> <node_id>              # 获取节点详情 (JSON)
                                             # 有未完成 blocks 前驱时附带派生字段
                                             # blocked / blocked_reason（不落盘）

  tree    <json_path> [node_id] [--depth N]  # 树形文本视图

  decide  <json_path> <node_id> "<question>" "<answer>" ["<note>"]

  remove-decision <json_path> <node_id> --index N | --question "..."
              # 删除决策 (按索引或按问题文本), 用于清理重复/误记

  decisions <json_path> [node_id]            # 列出决策

  render  <json_path>                        # 渲染 Markdown section 到关联 md 文件

  section <roadmap_path> [--all] [--max-depth N] [--max-bytes N]
                                            # bounded Markdown section (stdout)

  link    <json_path> <md_file>              # 关联 md 文件

  unlock  <json_path>                        # 显式删除残留 lock 目录

  stats   <json_path>                        # 统计信息

  recommend-storage <roadmap_path> [--measure]
                                            # 只读建议单 JSON 或 bundle

  validate <json_path>                       # 验证数据完整性

  migrate <json_path> --to bundle [--output <bundle_path>]
              # 显式把 legacy JSON 转为 sharded bundle；源文件不改写

  path    <json_path> <node_id>              # 获取从根到节点的路径

  siblings <json_path> <node_id>             # 获取兄弟节点

  focus   <json_path>                        # 获取当前施工点

  critical-path <json_path>                  # 关键路径：依赖图里最长的未完工链（#81）
                                            # 只读、不拿锁

  impact  <json_path> <node_id>             # 影响集：改 node_id 会波及的下游节点（#81）
                                            # 只读、不拿锁
"""

import sys
import json
import os
from contextlib import ExitStack
from pathlib import Path

# 将自身所在目录加入 path，确保能 import roadmap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadmap import (
    Roadmap,
    RoadmapError,
    RoadmapLockTimeout,
    exit_code_for,
    roadmap_file_lock,
    status_icon,
    unlock_roadmap,
)
from roadmap_bundle import BundleError, RoadmapBundle
from storage_advisor import recommend_storage


# 可以重复出现、每次追加一条值的参数（`--exit-criteria` 可给多条判据）。
MULTI_VALUE_FLAGS = frozenset({"exit-criteria"})


def _store(args: dict, key: str, value: str) -> None:
    if key in MULTI_VALUE_FLAGS:
        bucket = args.setdefault(key, [])
        if not isinstance(bucket, list):
            bucket = [bucket]
        bucket.append(value)
        args[key] = bucket
    else:
        args[key] = value


def _parse_args(argv: list[str]) -> dict:
    """解析命令行参数，返回命名参数 dict。

    Supports both `--key value` and `--key=value` forms. Bare flags
    (`--key` with no value) become the string `"true"`.
    """
    args: dict = {"positional": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            stripped = a[2:]
            # Support --key=value as a single token.
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                _store(args, key, value)
                i += 1
                continue
            key = stripped
            i += 1
            if i < len(argv) and not argv[i].startswith("--"):
                _store(args, key, argv[i])
                i += 1
            else:
                _store(args, key, "true")  # flag 类参数
        else:
            args["positional"].append(a)
            i += 1
    return args


def _exit_criteria_arg(args: dict) -> list | None:
    """取出 --exit-criteria；无值标志（`--exit-criteria` 不带文本）视为参数错误。"""
    raw = args.get("exit-criteria")
    if raw is None:
        return None
    values = raw if isinstance(raw, list) else [raw]
    if any(v == "true" for v in values):
        raise ValueError("--exit-criteria 需要给出判据文本")
    return [v for v in values if v] or None


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _fmt_args(args: dict):
    """从命令行参数抽取输出格式控制；三者都没给时返回 None（= 现状不变）。"""
    fmt = args.get("format")
    fields = args.get("fields")
    quiet = args.get("quiet") == "true"
    if fmt is None and fields is None and not quiet:
        return None
    return {"fmt": fmt, "fields": fields, "quiet": quiet}


def _project(data, fields):
    """按逗号分隔的字段名投影。`fields` 为空则原样返回。"""
    if not fields:
        return data
    keys = [k.strip() for k in fields.split(",") if k.strip()]
    if isinstance(data, list):
        return [{k: item.get(k) for k in keys if k in item} for item in data]
    return {k: data.get(k) for k in keys if k in data}


def _render_table(rows: list, md: bool):
    """把 list-of-dicts 渲染成文本表或 Markdown 表。空时给占位。"""
    if not rows:
        print("(empty)")
        return
    cols = list(rows[0].keys())
    str_rows = [[str(item.get(c, "")) for c in cols] for item in rows]
    if md:
        lines = ["| " + " | ".join(cols) + " |",
                 "| " + " | ".join("---" for _ in cols) + " |"]
        lines += ["| " + " | ".join(sr) + " |" for sr in str_rows]
        print("\n".join(lines))
        return
    widths = [max([len(c)] + [len(sr[i]) for sr in str_rows]) for i, c in enumerate(cols)]
    fmt_row = lambda cells: "  ".join(cells[i].ljust(widths[i]) for i in range(len(cols)))
    lines = [fmt_row(cols), fmt_row(["-" * w for w in widths])]
    lines += [fmt_row(sr) for sr in str_rows]
    print("\n".join(lines))


def _emit(data, fmt=None, fields=None, quiet=False):
    """统一输出发射器（#104 S5）。

    - fmt ∈ {json, md, table}，默认 json
    - fields：逗号投影键（对 list 每行 / 单 dict 投影）
    - quiet：只打每项 id（一行一个）

    调用方只在 `--format`/`--fields`/`--quiet` 任一显式出现时走本函数，
    否则逐字节保持现状（见 `_fmt_args`）；因此默认行为完全向后兼容。
    """
    fmt = fmt or "json"
    if fmt not in ("json", "md", "table"):
        raise ValueError(f"--format 仅支持 json/md/table，收到: {fmt}")
    if quiet:
        rows = data if isinstance(data, list) else [data]
        for item in rows:
            print(item.get("id", ""))
        return
    projected = _project(data, fields)
    if fmt == "json":
        _print_json(projected)
        return
    rows = (
        [{"key": k, "value": v} for k, v in projected.items()]
        if isinstance(projected, dict)
        else projected
    )
    _render_table(rows, md=(fmt == "md"))


def _load_roadmap(path: str):
    """Select storage by the path shape, then load one command-facing adapter."""
    roadmap = RoadmapBundle(path) if Path(path).is_dir() else Roadmap(path)
    roadmap.load()
    return roadmap


def cmd_init(args: dict):
    path = args["positional"][0]
    storage = args.get("storage", "single")
    seed = Roadmap(path)
    data = seed.init(
        title=args.get("title", "Untitled"),
        description=args.get("description", ""),
        md_file=args.get("md-file", ""),
    )
    if storage == "bundle":
        bundle = RoadmapBundle.create_from_data(path, data, int(args.get("snapshot-interval", 100)))
        print(f"Created bundle: {bundle.path}")
        return
    if storage != "single":
        raise ValueError("--storage must be single or bundle")
    seed.save()
    print(f"Created: {seed.json_path}")


def cmd_add(args: dict):
    r = _load_roadmap(args["positional"][0])
    node = r.add_node(
        parent_id=args["positional"][1],
        label=args["positional"][2],
        status=args.get("status", "pending"),
        mode=args.get("mode", "explore"),
        max_children=args.get("max-children"),
        max_rounds=args.get("max-rounds"),
        exit_criteria=_exit_criteria_arg(args),
    )
    r.save()
    _print_json(node)


def cmd_update(args: dict):
    r = _load_roadmap(args["positional"][0])
    node = r.update_node(
        node_id=r.resolve_node(args["positional"][1]),
        label=args.get("label"),
        status=args.get("status"),
        mode=args.get("mode"),
        notes=args.get("notes"),
        max_children=args.get("max-children"),
        max_rounds=args.get("max-rounds"),
        exit_criteria=_exit_criteria_arg(args),
        clear_budget=args.get("clear-budget") == "true",
        clear_exit_criteria=args.get("clear-exit-criteria") == "true",
    )
    r.save()
    _print_json(node)


def cmd_delete(args: dict):
    r = _load_roadmap(args["positional"][0])
    deleted = r.delete_node(r.resolve_node(args["positional"][1]))
    r.save()
    print(f"Deleted: {deleted}")
    # 没有边时不追加这一行：delete 的输出必须和 P1 之前逐字节一致。
    cascade = getattr(r, "last_edge_cascade", None) or {}
    if cascade.get("total"):
        breakdown = ", ".join(f"{t} {n}" for t, n in sorted(cascade["by_type"].items()))
        print(f"Removed edges: {cascade['total']} ({breakdown})")


def cmd_edge(args: dict):
    """`edge <action> <roadmap_path> ...` —— 动作在前，因为这是一组子命令。

    与其他命令"路径永远在第一位"不同：`edge` 带子动作，路径位置固定为
    第二位（`git remote add` 同款），否则路径位置会随动作漂移。
    """
    action = args["positional"][0]
    r = _load_roadmap(args["positional"][1])
    if action == "add":
        edge = r.add_edge(
            r.resolve_node(args["positional"][2]),
            r.resolve_node(args["positional"][3]),
            args.get("type", "blocks"),
        )
        r.save()
        _print_json(edge)
        return
    if action == "remove":
        edge = r.remove_edge(args["positional"][2])
        r.save()
        _print_json(edge)
        return
    if action == "list":
        rows = r.list_edges(args.get("node"))
        fa = _fmt_args(args)
        if fa:
            _emit(rows, **fa)
        else:
            _print_json({"edges": rows})
        return
    if action == "migrate":
        n = r.migrate_edges()
        if n:
            r.save()
        print(f"Migrated {n} edge endpoint(s) to uid.")
        return
    raise ValueError(f"未知 edge 动作: {action}")


def cmd_get(args: dict):
    r = _load_roadmap(args["positional"][0])
    # 读视图：派生字段（blocked / blocked_reason）在这里算出，不落盘。
    # 用户可用显示 id 或 uid 引用节点（#105 S3）。
    data = r.get_node_view(r.resolve_node(args["positional"][1]))
    fa = _fmt_args(args)
    if fa:
        _emit(data, **fa)
    else:
        _print_json(data)


def cmd_tree(args: dict):
    r = _load_roadmap(args["positional"][0])
    root = r.resolve_node(args["positional"][1]) if len(args["positional"]) > 1 else "1"
    default_depth = 2 if getattr(r, "is_bundle", False) else 10
    depth = int(args.get("depth", default_depth))
    print(r.get_tree(root, depth))


def cmd_ready(args: dict):
    """就绪集（#81）：pending 且没有未完成的 blocks 前驱。

    只读查询，不拿整图锁——为它拿锁会把并发读串行化，还可能撞上锁超时（退出码
    2），那是写命令才该有的失败模式。
    """
    r = _load_roadmap(args["positional"][0])
    nodes = r.ready_nodes()
    fa = _fmt_args(args)
    if fa:
        _emit([{"id": n["id"], "label": n["label"], "status": n["status"]} for n in nodes], **fa)
        return
    if not nodes:
        # 空集要说出来：静默的空输出无法与"命令没跑"区分。
        print("No ready nodes.")
        return
    for node in nodes:
        print(f"{node['id']}. {node['label']} {status_icon(node)}")


def cmd_critical_path(args: dict):
    """关键路径（#81, Story #21）：依赖图里最长的未完工链。

    只读查询，不拿整图锁（与 `ready` 同款：为它拿锁会把并发读串行化，
    还可能撞上锁超时——那是写命令才该有的失败模式）。
    """
    r = _load_roadmap(args["positional"][0])
    path = r.critical_path()
    fa = _fmt_args(args)
    if fa:
        rows = [{"id": nid, "label": r.get_node(nid)["label"], "status": r.get_node(nid)["status"]} for nid in path]
        _emit(rows, **fa)
        return
    if not path:
        print("No unfinished chain.")
        return
    for nid in path:
        node = r.get_node(nid)
        print(f"{nid}. {node['label']} {status_icon(node)}")


def cmd_impact(args: dict):
    """影响集（#81, Story #22）：改 node_id 会波及的下游节点（不含自身）。

    只读查询，不拿整图锁（与 `ready` / `critical-path` 同款）。
    """
    r = _load_roadmap(args["positional"][0])
    affected = r.impact(r.resolve_node(args["positional"][1]))
    fa = _fmt_args(args)
    if fa:
        rows = [{"id": nid, "label": r.get_node(nid)["label"], "status": r.get_node(nid)["status"]} for nid in affected]
        _emit(rows, **fa)
        return
    if not affected:
        print("No downstream impact.")
        return
    for nid in affected:
        node = r.get_node(nid)
        print(f"{nid}. {node['label']} {status_icon(node)}")


def cmd_decide(args: dict):
    r = _load_roadmap(args["positional"][0])
    d = r.add_decision(
        node_id=r.resolve_node(args["positional"][1]),
        question=args["positional"][2],
        answer=args["positional"][3],
        note=args["positional"][4] if len(args["positional"]) > 4 else "",
    )
    r.save()
    _print_json(d)


def cmd_decisions(args: dict):
    r = _load_roadmap(args["positional"][0])
    node_id = r.resolve_node(args["positional"][1]) if len(args["positional"]) > 1 else None
    data = r.get_decisions(node_id)
    fa = _fmt_args(args)
    if fa:
        _emit(data, **fa)
    else:
        _print_json(data)


def cmd_remove_decision(args: dict):
    r = _load_roadmap(args["positional"][0])
    node_id = r.resolve_node(args["positional"][1])
    index = int(args["index"]) if args.get("index") is not None else None
    question = args.get("question")
    removed = r.remove_decision(node_id, index=index, question=question)
    r.save()
    print(f"Removed: {removed} decision(s) from {node_id}")


def cmd_render(args: dict):
    r = _load_roadmap(args["positional"][0])
    result = r.write_markdown_section()
    if result:
        print(f"Written to: {result}")
    else:
        print("No md_file linked. Use 'link' command first.")


def cmd_section(args: dict):
    r = _load_roadmap(args["positional"][0])
    print(r.render_full_section(
        all_nodes=args.get("all") == "true",
        max_depth=int(args.get("max-depth", 2)),
        max_bytes=int(args["max-bytes"]) if args.get("max-bytes") is not None else None,
    ))


def cmd_link(args: dict):
    r = _load_roadmap(args["positional"][0])
    r.link_md_file(args["positional"][1])
    r.save()
    print(f"Linked to: {os.path.abspath(args['positional'][1])}")


def cmd_stats(args: dict):
    r = _load_roadmap(args["positional"][0])
    data = r.stats()
    fa = _fmt_args(args)
    if fa:
        _emit(data, **fa)
    else:
        _print_json(data)


def cmd_recommend_storage(args: dict):
    _print_json(recommend_storage(args["positional"][0], measure=args.get("measure") == "true"))


def cmd_validate(args: dict):
    r = _load_roadmap(args["positional"][0])
    errors = r.validate()
    if errors:
        print(f"Found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Valid.")


def cmd_path(args: dict):
    r = _load_roadmap(args["positional"][0])
    path_ids = r.get_path(r.resolve_node(args["positional"][1]))
    fa = _fmt_args(args)
    if fa:
        rows = [{"id": pid, "label": r.get_node(pid)["label"], "status": r.get_node(pid)["status"]} for pid in path_ids]
        _emit(rows, **fa)
        return
    for pid in path_ids:
        node = r.get_node(pid)
        print(f"  {pid}. {node['label']}")


def cmd_siblings(args: dict):
    r = _load_roadmap(args["positional"][0])
    sibs = r.get_siblings(r.resolve_node(args["positional"][1]))
    fa = _fmt_args(args)
    if fa:
        rows = [{"id": sid, "label": r.get_node(sid)["label"], "status": r.get_node(sid)["status"]} for sid in sibs]
        _emit(rows, **fa)
        return
    if sibs:
        for sid in sibs:
            node = r.get_node(sid)
            print(f"  {sid}. {node['label']}")
    else:
        print("(no siblings)")


def cmd_focus(args: dict):
    r = _load_roadmap(args["positional"][0])
    focus_id = r.get_current_focus()
    if focus_id:
        node = r.get_node(focus_id)
        data = {"focus": focus_id, "label": node["label"], "status": node["status"]}
        fa = _fmt_args(args)
        if fa:
            _emit(data, **fa)
        else:
            _print_json(data)
    else:
        print("(no in-progress leaf node)")


def cmd_unlock(args: dict):
    lock_dir = unlock_roadmap(args["positional"][0])
    print(f"Unlocked: {lock_dir}")


def cmd_migrate(args: dict):
    source = Path(args["positional"][0]).expanduser().resolve()
    if args.get("to") != "bundle":
        raise ValueError("migrate requires --to bundle")
    default_output = source.with_suffix(".bundle") if source.suffix else Path(f"{source}.bundle")
    output = Path(args.get("output", str(default_output))).expanduser().resolve()
    interval = int(args.get("snapshot-interval", 100))
    lock_paths = sorted({str(source), str(output)})
    with ExitStack() as stack:
        for lock_path in lock_paths:
            stack.enter_context(roadmap_file_lock(lock_path))
        bundle = RoadmapBundle.migrate_from_legacy(source, output, interval)
    print(f"Migrated: {source} -> {bundle.path}")


def cmd_context(args: dict):
    """来龙去脉（#104 S5）：上游（依赖谁）/下游（谁依赖我）/阻塞链。"""
    r = _load_roadmap(args["positional"][0])
    data = r.context(r.resolve_node(args["positional"][1]))
    fa = _fmt_args(args)
    if fa:
        _emit(data, **fa)
    else:
        _print_json(data)


def cmd_next(args: dict):
    """就绪优先建议（#104 S5）：建议接下来开工的就绪节点。"""
    r = _load_roadmap(args["positional"][0])
    data = r.next_nodes()
    fa = _fmt_args(args)
    if fa:
        _emit(data, **fa)
    else:
        _print_json(data)


# ── 命令路由 ──────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "add": cmd_add,
    "update": cmd_update,
    "delete": cmd_delete,
    "get": cmd_get,
    "tree": cmd_tree,
    "ready": cmd_ready,
    "critical-path": cmd_critical_path,
    "impact": cmd_impact,
    "edge": cmd_edge,
    "decide": cmd_decide,
    "decisions": cmd_decisions,
    "remove-decision": cmd_remove_decision,
    "render": cmd_render,
    "section": cmd_section,
    "link": cmd_link,
    "unlock": cmd_unlock,
    "stats": cmd_stats,
    "recommend-storage": cmd_recommend_storage,
    "validate": cmd_validate,
    "path": cmd_path,
    "siblings": cmd_siblings,
    "focus": cmd_focus,
    "migrate": cmd_migrate,
    "context": cmd_context,
    "next": cmd_next,
}


# 写命令走整图锁；`edge` 按子动作区分，因为 `edge list` 是只读。
LOCK_COMMANDS = frozenset(
    {"init", "add", "update", "delete", "decide", "remove-decision", "render", "link"}
)
EDGE_WRITE_ACTIONS = frozenset({"add", "remove", "migrate"})


def _needs_lock(cmd: str, args: dict) -> bool:
    """是否要为这次调用拿整图锁。

    只读的 `edge list` 不拿锁：为它拿锁会把并发读串行化，还让读命令
    可能撞上锁超时（退出码 2），那是写命令才该有的失败模式。
    """
    if cmd != "edge":
        return cmd in LOCK_COMMANDS
    return args["positional"][0] in EDGE_WRITE_ACTIONS


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    args = _parse_args(sys.argv[2:])
    try:
        if _needs_lock(cmd, args):
            with roadmap_file_lock(args["positional"][0]):
                COMMANDS[cmd](args)
        else:
            COMMANDS[cmd](args)
    except RoadmapLockTimeout as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except RoadmapError as e:
        # 稳定错误码在行首，Agent 按 code 分支，不要匹配后半句的人类文案。
        print(f"Error: {e.code}: {e}", file=sys.stderr)
        sys.exit(exit_code_for(e))
    except (BundleError, FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
