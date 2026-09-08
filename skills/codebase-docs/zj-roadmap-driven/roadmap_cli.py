"""
zj-roadmap-driven CLI — 路线图确定性操作入口

每条命令输入确定 → 输出确定，Agent 可直接拼命令，无需推断。

用法:
  python roadmap_cli.py <command> <args...>

命令:
  init    <roadmap_path> --title "..." [--description "..."] [--md-file "..."]
              [--storage single|bundle] [--snapshot-interval N]

  add     <json_path> <parent_id> "<label>"
              [--status pending|in_progress|completed|blocked]
              [--mode explore|exploit]

  update  <json_path> <node_id>
              [--label "..."] [--status ...] [--mode ...] [--notes "..."]

  delete  <json_path> <node_id>              # 删除节点及所有子节点

  get     <json_path> <node_id>              # 获取节点详情 (JSON)

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
"""

import sys
import json
import os
from contextlib import ExitStack
from pathlib import Path

# 将自身所在目录加入 path，确保能 import roadmap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadmap import Roadmap, RoadmapLockTimeout, roadmap_file_lock, unlock_roadmap
from roadmap_bundle import BundleError, RoadmapBundle
from storage_advisor import recommend_storage


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
                args[key] = value
                i += 1
                continue
            key = stripped
            i += 1
            if i < len(argv) and not argv[i].startswith("--"):
                args[key] = argv[i]
                i += 1
            else:
                args[key] = "true"  # flag 类参数
        else:
            args["positional"].append(a)
            i += 1
    return args


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


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
    )
    r.save()
    _print_json(node)


def cmd_update(args: dict):
    r = _load_roadmap(args["positional"][0])
    node = r.update_node(
        node_id=args["positional"][1],
        label=args.get("label"),
        status=args.get("status"),
        mode=args.get("mode"),
        notes=args.get("notes"),
    )
    r.save()
    _print_json(node)


def cmd_delete(args: dict):
    r = _load_roadmap(args["positional"][0])
    deleted = r.delete_node(args["positional"][1])
    r.save()
    print(f"Deleted: {deleted}")


def cmd_get(args: dict):
    r = _load_roadmap(args["positional"][0])
    _print_json(r.get_node(args["positional"][1]))


def cmd_tree(args: dict):
    r = _load_roadmap(args["positional"][0])
    root = args["positional"][1] if len(args["positional"]) > 1 else "1"
    default_depth = 2 if getattr(r, "is_bundle", False) else 10
    depth = int(args.get("depth", default_depth))
    print(r.get_tree(root, depth))


def cmd_decide(args: dict):
    r = _load_roadmap(args["positional"][0])
    d = r.add_decision(
        node_id=args["positional"][1],
        question=args["positional"][2],
        answer=args["positional"][3],
        note=args["positional"][4] if len(args["positional"]) > 4 else "",
    )
    r.save()
    _print_json(d)


def cmd_decisions(args: dict):
    r = _load_roadmap(args["positional"][0])
    node_id = args["positional"][1] if len(args["positional"]) > 1 else None
    _print_json(r.get_decisions(node_id))


def cmd_remove_decision(args: dict):
    r = _load_roadmap(args["positional"][0])
    node_id = args["positional"][1]
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
    _print_json(r.stats())


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
    path_ids = r.get_path(args["positional"][1])
    for pid in path_ids:
        node = r.get_node(pid)
        print(f"  {pid}. {node['label']}")


def cmd_siblings(args: dict):
    r = _load_roadmap(args["positional"][0])
    sibs = r.get_siblings(args["positional"][1])
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
        _print_json({"focus": focus_id, "label": node["label"], "status": node["status"]})
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


# ── 命令路由 ──────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "add": cmd_add,
    "update": cmd_update,
    "delete": cmd_delete,
    "get": cmd_get,
    "tree": cmd_tree,
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
}


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
    lock_commands = {"init", "add", "update", "delete", "decide", "remove-decision", "render", "link"}
    try:
        if cmd in lock_commands:
            with roadmap_file_lock(args["positional"][0]):
                COMMANDS[cmd](args)
        else:
            COMMANDS[cmd](args)
    except RoadmapLockTimeout as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except (BundleError, FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
