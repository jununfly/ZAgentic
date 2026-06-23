"""
zj-roadmap-driven CLI — 路线图确定性操作入口

每条命令输入确定 → 输出确定，Agent 可直接拼命令，无需推断。

用法:
  python roadmap_cli.py <command> <args...>

命令:
  init    <json_path> --title "..." [--description "..."] [--md-file "..."]

  add     <json_path> <parent_id> "<label>"
              [--status pending|in_progress|completed|blocked]
              [--mode explore|exploit]

  update  <json_path> <node_id>
              [--label "..."] [--status ...] [--mode ...] [--notes "..."]

  delete  <json_path> <node_id>              # 删除节点及所有子节点

  get     <json_path> <node_id>              # 获取节点详情 (JSON)

  tree    <json_path> [node_id] [--depth N]  # 树形文本视图

  decide  <json_path> <node_id> "<question>" "<answer>" ["<note>"]

  decisions <json_path> [node_id]            # 列出决策

  render  <json_path>                        # 渲染 Markdown section 到关联 md 文件

  section <json_path>                        # 输出 Markdown section 文本 (stdout)

  link    <json_path> <md_file>              # 关联 md 文件

  stats   <json_path>                        # 统计信息

  validate <json_path>                       # 验证数据完整性

  import  <json_path> <md_file>              # 从 md 文件导入路线图

  path    <json_path> <node_id>              # 获取从根到节点的路径

  siblings <json_path> <node_id>             # 获取兄弟节点

  focus   <json_path>                        # 获取当前施工点
"""

import sys
import json
import os

# 将自身所在目录加入 path，确保能 import roadmap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadmap import Roadmap


def _parse_args(argv: list[str]) -> dict:
    """解析命令行参数，返回命名参数 dict。"""
    args: dict = {"positional": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            i += 1
            if i < len(argv) and not argv[i].startswith("--"):
                args[key] = argv[i]
            else:
                args[key] = "true"  # flag 类参数
        else:
            args["positional"].append(a)
            i += 1
    return args


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init(args: dict):
    r = Roadmap(args["positional"][0])
    r.init(
        title=args.get("title", "Untitled"),
        description=args.get("description", ""),
        md_file=args.get("md-file", ""),
    )
    r.save()
    print(f"Created: {r.json_path}")


def cmd_add(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    node = r.add_node(
        parent_id=args["positional"][1],
        label=args["positional"][2],
        status=args.get("status", "pending"),
        mode=args.get("mode", "explore"),
    )
    r.save()
    _print_json(node)


def cmd_update(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
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
    r = Roadmap(args["positional"][0])
    r.load()
    deleted = r.delete_node(args["positional"][1])
    r.save()
    print(f"Deleted: {deleted}")


def cmd_get(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    _print_json(r.get_node(args["positional"][1]))


def cmd_tree(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    root = args["positional"][1] if len(args["positional"]) > 1 else "1"
    depth = int(args.get("depth", 10))
    print(r.get_tree(root, depth))


def cmd_decide(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    d = r.add_decision(
        node_id=args["positional"][1],
        question=args["positional"][2],
        answer=args["positional"][3],
        note=args["positional"][4] if len(args["positional"]) > 4 else "",
    )
    r.save()
    _print_json(d)


def cmd_decisions(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    node_id = args["positional"][1] if len(args["positional"]) > 1 else None
    _print_json(r.get_decisions(node_id))


def cmd_render(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    result = r.write_markdown_section()
    if result:
        print(f"Written to: {result}")
    else:
        print("No md_file linked. Use 'link' command first.")


def cmd_section(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    print(r.render_full_section())


def cmd_link(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    r.link_md_file(args["positional"][1])
    r.save()
    print(f"Linked to: {os.path.abspath(args['positional'][1])}")


def cmd_stats(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    _print_json(r.stats())


def cmd_validate(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    errors = r.validate()
    if errors:
        print(f"Found {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Valid.")


def cmd_path(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    path_ids = r.get_path(args["positional"][1])
    for pid in path_ids:
        node = r.get_node(pid)
        print(f"  {pid}. {node['label']}")


def cmd_siblings(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    sibs = r.get_siblings(args["positional"][1])
    if sibs:
        for sid in sibs:
            node = r.get_node(sid)
            print(f"  {sid}. {node['label']}")
    else:
        print("(no siblings)")


def cmd_focus(args: dict):
    r = Roadmap(args["positional"][0])
    r.load()
    focus_id = r.get_current_focus()
    if focus_id:
        node = r.get_node(focus_id)
        _print_json({"focus": focus_id, "label": node["label"], "status": node["status"]})
    else:
        print("(no in-progress leaf node)")


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
    "render": cmd_render,
    "section": cmd_section,
    "link": cmd_link,
    "stats": cmd_stats,
    "validate": cmd_validate,
    "path": cmd_path,
    "siblings": cmd_siblings,
    "focus": cmd_focus,
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
    COMMANDS[cmd](args)


if __name__ == "__main__":
    main()
