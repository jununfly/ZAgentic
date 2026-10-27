#!/usr/bin/env python3
"""Generic launch-pack engine for zj-doc-collab.

A *static* generator: it only reads Markdown and writes Markdown; it never
starts, orchestrates, or contacts an Agent session. The design decision behind
that boundary: building a session runtime would reclassify the whole approach,
so the generator stays inert.

What is generic (belongs in the base skill):

- parsing the *declared required role set* out of a sub-document
- parsing a role-matrix table into a key -> {name, stance, intro, is_base} pool
- parsing the signal -> optional-role table
- rendering one launch pack per role from a **parameterized** template

What the consumer supplies (kept out of the base):

- the role-matrix *content* (its role pool + per-role gated methods)
- the per-role **executor command** (e.g. ``zj-discuss-view --role X <path>``)
- the role-method *reference path* shown inside each pack
- the pack / prep *templates* (consumer-specific wording)

Usage (consumer side, e.g. zj-discuss/launch_pack.py):

    from launch_pack_core import (
        parse_declared_set, load_role_pool, load_signals,
        render_pack, generate_prep, generate,
    )
    generate(subdoc, roles, out, matrix,
             pack_template=PACK_TEMPLATE,            # consumer's wording
             executor_cmd_template="zj-discuss-view --role {key} {subdoc}")
"""

import argparse
import re
import sys
from pathlib import Path

DECLARED_SET_RE = re.compile(r"声明必需角色集\s*[：:]\s*(.+)")
SPLIT_RE = re.compile(r"[,，、;；]")
STRIP_CHARS = " \t`\"'*_\u00a0"


class Refusal(Exception):
    """Raised when the generator must refuse rather than guess."""


def parse_declared_set(text):
    """Extract the declared required role keys from a sub-document body."""
    match = DECLARED_SET_RE.search(text)
    if not match:
        return []
    raw = match.group(1)
    keys = []
    for part in SPLIT_RE.split(raw):
        key = part.strip(STRIP_CHARS).strip()
        if key:
            keys.append(key)
    return keys


def load_role_pool(matrix_path):
    """Parse key -> {name, stance, intro, is_base} out of the role matrix table."""
    matrix_path = Path(matrix_path)
    if not matrix_path.exists():
        raise Refusal("role matrix not found: {}".format(matrix_path))

    pool = {}
    for raw_line in matrix_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        key = cells[0].strip(STRIP_CHARS)
        name = cells[1].strip(STRIP_CHARS)
        if not key or key.lower() == "key":
            continue
        if set(key) <= set("-: "):
            continue
        pool[key] = {
            "name": name,
            "stance": cells[3].strip(STRIP_CHARS) if len(cells) > 3 else "",
            "intro": cells[5].strip(STRIP_CHARS) if len(cells) > 5 else "",
            "is_base": "✅" in cells[2] if len(cells) > 2 else False,
        }
    if not pool:
        raise Refusal("no roles parsed from {}".format(matrix_path))
    return pool


SIGNAL_HEADER_RE = re.compile(r"信号\s*[（(]?\s*子问题触及")
ROLE_KEY_IN_CELL_RE = re.compile(r"^\s*([A-Za-z]+)\s*[（(]")


def load_signals(matrix_path):
    """Map role key -> trigger-signal text from the role-matrix signal table."""
    matrix_path = Path(matrix_path)
    if not matrix_path.exists():
        raise Refusal("role matrix not found: {}".format(matrix_path))
    signals = {}
    in_signal_table = False
    for raw_line in matrix_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            if in_signal_table:
                break
            continue
        if SIGNAL_HEADER_RE.search(line):
            in_signal_table = True
            continue
        if not in_signal_table:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        m = ROLE_KEY_IN_CELL_RE.match(cells[-1])
        if not m:
            continue
        signals[m.group(1)] = cells[0]
    return signals


# Neutral templates: the base never hardcodes a consumer's executor command or
# role-method path. Consumers pass their own templates + executor_cmd_template.
GENERIC_PACK_TEMPLATE = """# 启动包：角色 {{key}}（{{name}}）

> 由 `zj-doc-collab` 静态生成器生成的一次性文本。Human 把本文件原样粘贴到**一个全新的
> 独立 Agent 会话**。生成器只写文件，不发起会话、不联网、不做编排。

## 你的角色

- **role key：** `{{key}}`
- **角色：** {{name}}
- **结构立场：** {{stance}}
- **一句话简介：** {{intro}}
- **gated method（牙齿）：** {{role_method_ref}}

## 第一步（不可跳过）

```
Read `{{subdoc}}`
Read {{role_method_ref}}
```

## 第二步：加载 companion 并写视角

```
{{executor_cmd}}
```

## 硬契约 reminder

1. **Read the original** —— 观点必须来自你读到的原文。
2. **No relayed summaries** —— 拒绝 Human 转述的其他角色口径，那不是独立视角。
3. **No "refute A" framing** —— 你不是被派来反驳谁，你是被派来换一个结构位置看问题。
4. **Mark your source** —— 写入视角时以 `视角来源: 跨会话独立Agent` 开头。
5. **Cite with a locator** —— 「发现」须带能回溯到原文的定位：`原文 L96` /
   `原文 <file> Lxx` / `原文 ## 章节`。
6. **Fill the placeholders** —— 模板里 `<主题>` / `<...>` 是未填占位，照抄不算证据。
"""

GENERIC_PREP_TEMPLATE = """# 准备阶段角色推荐（zj-doc-collab 静态生成 · 单一数据源 = role-matrix）

> 本清单由 launch_pack 从 role-matrix 程序化生成，每个角色强制带「一句话简介」。

## 推荐参与角色（base 必需集，永远推荐）
| key | 角色 | 一句话简介 | 推荐理由 |
| --- | --- | --- | --- |
| {base_rows} |

## 其他可选角色（候选池，按子问题信号增删）
| key | 角色 | 一句话简介 | 触发信号（命中即建议加入） |
| --- | --- | --- | --- |
| {opt_rows} |
"""


def render_pack(role, role_info, subdoc_path, pack_template=GENERIC_PACK_TEMPLATE,
                executor_cmd="", role_method_ref="（见 role-matrix）"):
    """Render one launch pack's text for a single role."""
    text = (pack_template
            .replace("{{key}}", role)
            .replace("{{name}}", role_info.get("name") or role)
            .replace("{{stance}}", role_info.get("stance") or "（见 role-matrix）")
            .replace("{{intro}}", role_info.get("intro") or "（见 role-matrix）")
            .replace("{{subdoc}}", str(subdoc_path))
            .replace("{{executor_cmd}}", executor_cmd)
            .replace("{{role_method_ref}}", role_method_ref))
    return text


def _build_prep_row(role, info, extra):
    return "| {key} | {name} | {intro} | {extra} |".format(
        key=role,
        name=info.get("name") or role,
        intro=info.get("intro") or "（见 role-matrix）",
        extra=extra,
    )


def generate_prep(pool, signals=None, base_reason=None,
                  prep_template=GENERIC_PREP_TEMPLATE, limit=None):
    """Render the preparation-phase role list from a parsed role pool."""
    base_reason = base_reason or (lambda r: "base 必需集成员")
    sig = signals if signals is not None else {}
    base_rows, opt_rows = [], []
    for role, info in pool.items():
        if info.get("is_base"):
            base_rows.append(_build_prep_row(role, info, base_reason(role)))
        elif limit is None or role in limit:
            opt_rows.append(_build_prep_row(role, info, sig.get(role, "（见 role-matrix 信号表）")))
    if not opt_rows:
        opt_rows.append("| — | （无候选池角色） | — | — |")
    return prep_template.format(
        base_rows="\n".join(base_rows), opt_rows="\n".join(opt_rows)
    )


def _ensure_dir(path):
    path = Path(path)
    if path.exists():
        return
    try:
        path.mkdir(parents=True)
    except OSError:
        if not path.exists():
            raise


def generate(subdoc_path, roles, out_dir, matrix_path,
             pack_template=GENERIC_PACK_TEMPLATE, executor_cmd_template=None,
             role_method_ref_template=None, allow_custom=False):
    """Write one launch pack per role and return the created paths.

    ``executor_cmd_template`` may contain ``{key}`` / ``{subdoc}`` placeholders,
    filled per role. ``role_method_ref_template`` may contain ``{key}``.
    """
    subdoc_path = Path(subdoc_path)
    if not subdoc_path.exists():
        raise Refusal("sub-document not on disk: {}".format(subdoc_path))

    text = subdoc_path.read_text(encoding="utf-8")
    selected = list(roles) if roles else parse_declared_set(text)
    if not selected:
        raise Refusal(
            "{} declares no required role set; pass --roles explicitly".format(subdoc_path)
        )

    pool = load_role_pool(matrix_path)
    unknown = [r for r in selected if r not in pool]
    if unknown and not allow_custom:
        raise Refusal(
            "role(s) {} are not in the candidate pool (see role-matrix); "
            "pass --allow-custom to declare them as Human-defined".format(",".join(unknown))
        )

    out_dir = Path(out_dir)
    _ensure_dir(out_dir)

    written = []
    for role in selected:
        info = pool.get(role, {"name": role, "stance": "", "intro": ""})
        executor_cmd = (executor_cmd_template or "").format(key=role, subdoc=str(subdoc_path))
        role_method_ref = (role_method_ref_template or "（见 role-matrix）").format(key=role)
        target = out_dir / "{}-launchpack-{}.md".format(subdoc_path.stem, role)
        target.write_text(
            render_pack(role, info, subdoc_path, pack_template, executor_cmd, role_method_ref),
            encoding="utf-8",
        )
        written.append(target)
    return written


def _project_root(path: Path) -> Path:
    """Nearest git-repo ancestor of `path`, else the path's own parent.

    ADR 0010: launch-packs are project output, so they land in
    <project-root>/tmp/skills-outputs/<consumer-skill>/<topic>/ rather than
    scattered next to the sub-document.
    """
    cur = Path(path).resolve()
    if cur.is_file():
        cur = cur.parent
    while not (cur / ".git").exists():
        parent = cur.parent
        if parent == cur:
            return Path(path).resolve().parent
        cur = parent
    return cur


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Static launch-pack / prep-list generator (zj-doc-collab base engine)."
    )
    parser.add_argument("subdoc", nargs="?", help="path to the sub-document (pack mode)")
    parser.add_argument(
        "--prep", action="store_true",
        help="render the preparation-phase role list instead of packs",
    )
    parser.add_argument("--roles", help="override the declared required set, comma separated")
    parser.add_argument("--out", help="pack mode: output dir; prep mode: output file")
    parser.add_argument("--matrix", required=True, help="role matrix path")
    parser.add_argument(
        "--allow-custom", action="store_true", help="accept role keys outside the pool"
    )
    parser.add_argument(
        "--signals", help="prep mode: limit optional roles to these keys (comma separated)"
    )
    args = parser.parse_args(argv)

    if args.prep:
        limit = None
        if args.signals:
            limit = {r.strip() for r in SPLIT_RE.split(args.signals) if r.strip()}
        try:
            text = generate_prep(load_role_pool(args.matrix), load_signals(args.matrix),
                                 limit=limit)
        except Refusal as exc:
            print("refused: {}".format(exc), file=sys.stderr)
            return 2
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print("wrote prep list: {}".format(args.out))
        else:
            print(text)
        return 0

    if not args.subdoc:
        parser.print_help()
        return 1

    roles = None
    if args.roles:
        roles = [r.strip() for r in SPLIT_RE.split(args.roles) if r.strip()]

    # ADR 0010: 项目输出 → 项目隔离区，不散落 subdoc 旁。
    subdoc_path = Path(args.subdoc).resolve()
    out_dir = Path(args.out) if args.out else (
        _project_root(subdoc_path)
        / "tmp" / "skills-outputs" / "zj-doc-collab" / subdoc_path.stem
    )

    try:
        packs = generate(args.subdoc, roles, out_dir, args.matrix, allow_custom=args.allow_custom)
    except Refusal as exc:
        print("refused: {}".format(exc), file=sys.stderr)
        return 2

    print("generated {} launch pack(s):".format(len(packs)))
    for pack in packs:
        print("  {}".format(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
