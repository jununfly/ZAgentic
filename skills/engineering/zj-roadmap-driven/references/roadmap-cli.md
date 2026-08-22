# Roadmap CLI reference

All roadmap operations use the skill's `roadmap_cli.py`. Inputs are deterministic and the Python dependency is standard-library-only (Python 3.8+).

## Commands

```bash
# Initialize
python roadmap_cli.py init <json_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]

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
python roadmap_cli.py render <json_path>
python roadmap_cli.py section <json_path>
python roadmap_cli.py link <json_path> <md_file>
python roadmap_cli.py tree <json_path> [<node_id>] [--depth 3]
python roadmap_cli.py path <json_path> <node_id>
python roadmap_cli.py siblings <json_path> <node_id>
python roadmap_cli.py focus <json_path>
python roadmap_cli.py validate <json_path>
python roadmap_cli.py stats <json_path>
```

`render` writes the lightweight Markdown view (tree depth=2, current focus, and one level of the focus subtree). `section` writes the fully expanded view to stdout. `focus` returns the first in-progress leaf.

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
python roadmap_cli.py section roadmap.json
```

## Script location and write safety

Scripts live beside this skill:

```text
<skill_dir>/roadmap.py        # core library
<skill_dir>/roadmap_cli.py    # CLI entry point
```

After the skill is loaded, locate them with `$SKILL_DIR` or an absolute path.

Write commands use `<json_path>.lock/` and atomic JSON/Markdown writes. Do not run write commands for the same JSON in parallel. A stale lock is not cleared automatically; the timeout reports its owner and path so it can be checked before `unlock`.

Deleting a node recursively deletes its children; confirm the target first.

## Demos

- `demos/roadmap_demo.json` — an AI-Native personal compounding-tool-system roadmap.
- `demos/ZJ_ROADMAP_section_demo.md` — standard output rendered from JSON.
