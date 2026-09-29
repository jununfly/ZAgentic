#!/usr/bin/env python3
"""Static launch-pack generator for zj-discuss.

Replaces the Human's manual copy/paste of per-role briefings. Given one
sub-document, it reads that sub-document's **declared required role set** and
writes one ready-to-paste launch pack per role.

This is deliberately a *static* generator:

- it only reads Markdown and writes Markdown;
- it never starts, orchestrates, or contacts an Agent session;

the design decision behind that boundary is recorded in
``docs/designs/zj-discuss/architecture.md`` (building a session runtime would
reclassify the whole approach, so the generator stays inert).

Usage:

    python3 launch_pack.py <sub-doc-path> [--roles B,C,A] [--out DIR]
                           [--matrix PATH] [--allow-custom]
    python3 launch_pack.py --prep [--matrix PATH] [--signals T,S,O] [--out FILE]
"""

import argparse
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = SKILL_DIR / "references" / "role-matrix.md"

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
    """Parse key -> {name, stance, intro} out of the role matrix table."""
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
    """Map role key -> trigger-signal text from role-matrix's signal table.

    The signal table (``| 信号（子问题触及…） | 建议追加角色 |``) lives below the
    main role table; parsing it keeps the prep list's "推荐理由" column a single
    source (role-matrix), so the prep command cannot drift from the matrix.
    """
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
            continue  # separator or malformed row
        m = ROLE_KEY_IN_CELL_RE.match(cells[-1])
        if not m:
            continue
        signals[m.group(1)] = cells[0]
    return signals


PREP_TEMPLATE = """# 准备阶段角色推荐（zj-discuss 静态生成 · 单一数据源 = role-matrix.md）

> 本清单由 `launch_pack.py --prep` 从 `references/role-matrix.md` 程序化生成，
> 每个角色强制带「一句话简介」——准备阶段 AI 自由文本不再是无强制缺口（bug1 修复）。
> Human 确认/调整后，锁定集合成为该子文档的 **declared required set**。

## 推荐参与角色（base 必需集，永远推荐）
| key | 角色 | 一句话简介 | 推荐理由 |
| --- | --- | --- | --- |
{base_rows}

## 其他可选角色（候选池，按子问题信号增删）
| key | 角色 | 一句话简介 | 触发信号（命中即建议加入） |
| --- | --- | --- | --- |
{opt_rows}

> 用法：把本清单原样粘贴进子文档「准备阶段」区块；base 集默认全选，可选角色按
> 子问题触及的信号由 Human 增删。不要靠 AI 自觉补简介——本表即唯一真相源。
"""


BASE_REASON = {
    "B": "base 必需集：覆盖执行 / 落地",
    "C": "base 必需集：覆盖用户价值 / 生态·竞品",
    "A": "base 必需集：覆盖约束 / 长期一致",
}


def _build_prep_row(role, info, extra):
    return "| {key} | {name} | {intro} | {extra} |".format(
        key=role,
        name=info.get("name") or role,
        intro=info.get("intro") or "（见 role-matrix.md）",
        extra=extra,
    )


def generate_prep(matrix_path, signals=None, limit=None):
    """Render the preparation-phase role list from the role matrix (single source).

    Returns Markdown with two tables: the base required set (each carrying a
    one-line intro + why-base) and the rest of the candidate pool (each carrying
    a one-line intro + its trigger signal). This is the script-driven replacement
    for the AI-free-text prep list that dropped role intros (bug1).
    """
    pool = load_role_pool(matrix_path)
    signals = signals if signals is not None else load_signals(matrix_path)
    base_rows, opt_rows = [], []
    for role, info in pool.items():
        if info.get("is_base"):
            base_rows.append(_build_prep_row(role, info, BASE_REASON.get(role, "base 必需集成员")))
        elif limit is None or role in limit:
            opt_rows.append(_build_prep_row(role, info, signals.get(role, "（见 role-matrix.md 信号表）")))
    if not opt_rows:
        opt_rows.append("| — | （无候选池角色） | — | — |")
    return PREP_TEMPLATE.format(
        base_rows="\n".join(base_rows), opt_rows="\n".join(opt_rows)
    )


PACK_TEMPLATE = """# 启动包：角色 {{key}}（{{name}}）

> 由 `zj-discuss` 静态生成器生成的一次性文本。Human 把本文件原样粘贴到**一个全新的
> 独立 Agent 会话**。生成器只写文件，不发起会话、不联网、不做编排。

## 你的角色

- **role key：** `{{key}}`
- **角色：** {{name}}
- **结构立场：** {{stance}}
- **一句话简介：** {{intro}}
- **gated method（牙齿）：** `references/role-methods/{{key}}.md` —— 动笔前 `Read` 它，按其中的「角色专属核查清单 + 三字段输出 + 闸门」产出。

> 角色语义以 `references/role-matrix.md` 为唯一真源。你不复述别人，也不反驳别人 ——
> 你从上面这个「结构立场 / 差异锚点」出发独立论证。

## 第一步（不可跳过）

```
Read `{{subdoc}}`
Read `references/role-methods/{{key}}.md`
```

你必须自己 `Read` 这两份原文并形成立场。若没被给出文件，停下来向 Human 要路径。
方法文件规定了本角色的可机械判定核查契约（见 design.md §10.4 项1）。

## 第二步：加载 companion 并写视角

```
zj-discuss-view --role {{key}} {{subdoc}}
```

## 硬契约 reminder

1. **Read the original** —— 观点必须来自你读到的原文。
2. **No relayed summaries** —— 拒绝 Human 转述的其他角色口径，那不是独立视角。
3. **No "refute A" framing** —— 你不是被派来反驳谁，你是被派来换一个结构位置看问题。
4. **Mark your source** —— 写入 `## Agent viewpoints` 时以
   `` 视角来源: 跨会话独立Agent `` 开头。
5. **Answer the open questions** —— 回答该子文档 `## 待讨论问题` 里的 Q1/Q2/…，
   不要复述文件既有内容假装是自己的结论。
"""


def build_pack(role, role_info, subdoc_path):
    """Render one launch pack's text for a single role."""
    return PACK_TEMPLATE.replace("{{key}}", role).replace(
        "{{name}}", role_info.get("name") or role
    ).replace("{{stance}}", role_info.get("stance") or "（见 role-matrix.md）").replace(
        "{{intro}}", role_info.get("intro") or "（见 role-matrix.md）"
    ).replace("{{subdoc}}", str(subdoc_path))


def _ensure_dir(path):
    path = Path(path)
    if path.exists():
        return
    try:
        path.mkdir(parents=True)
    except OSError:
        # The local sitecustomize shim can raise a non-FileExistsError here when
        # the directory already exists; only propagate genuinely failed creation.
        if not path.exists():
            raise


def generate(subdoc_path, roles, out_dir, matrix_path, allow_custom=False):
    """Write one launch pack per role and return the created paths."""
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
            "role(s) {} are not in the candidate pool (see role-matrix.md); "
            "pass --allow-custom to declare them as Human-defined".format(",".join(unknown))
        )

    out_dir = Path(out_dir)
    _ensure_dir(out_dir)

    written = []
    for role in selected:
        info = pool.get(role, {"name": role, "stance": "", "intro": ""})
        target = out_dir / "{}-launchpack-{}.md".format(subdoc_path.stem, role)
        target.write_text(build_pack(role, info, subdoc_path), encoding="utf-8")
        written.append(target)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Static launch-pack / prep-list generator for zj-discuss."
    )
    parser.add_argument("subdoc", nargs="?", help="path to the sub-document (pack mode)")
    parser.add_argument(
        "--prep", action="store_true",
        help="render the preparation-phase role list (single source) instead of packs",
    )
    parser.add_argument("--roles", help="override the declared required set, comma separated")
    parser.add_argument("--out", help="pack mode: output dir; prep mode: output file")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="role matrix path")
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
            text = generate_prep(args.matrix, limit=limit)
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

    out_dir = Path(args.out) if args.out else Path(args.subdoc).resolve().parent / "briefings"

    try:
        packs = generate(args.subdoc, roles, out_dir, args.matrix, args.allow_custom)
    except Refusal as exc:
        print("refused: {}".format(exc), file=sys.stderr)
        return 2

    print("generated {} launch pack(s):".format(len(packs)))
    for pack in packs:
        print("  {}".format(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
