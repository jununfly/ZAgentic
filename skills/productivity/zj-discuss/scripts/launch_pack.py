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
        }
    if not pool:
        raise Refusal("no roles parsed from {}".format(matrix_path))
    return pool


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
        description="Generate one ready-to-paste launch pack per declared role."
    )
    parser.add_argument("subdoc", help="path to the sub-document")
    parser.add_argument("--roles", help="override the declared required set, comma separated")
    parser.add_argument("--out", help="output directory (default: <subdoc dir>/briefings)")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="role matrix path")
    parser.add_argument(
        "--allow-custom", action="store_true", help="accept role keys outside the pool"
    )
    args = parser.parse_args(argv)

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
