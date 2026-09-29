#!/usr/bin/env python3
"""Deterministic strip+shuffle to produce a blind version of probe-views.md.

Implements盲评协议 §2: remove validity labels, inline 标注 notes, 小结 lines,
汇总 section, 自指偏差声明; shuffle viewpoint order within each role and
renumber. Output: blind-eval/probe-views.blind.md
"""
import re
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "probe-views.md")
OUT_DIR = os.path.join(HERE, "blind-eval")
OUT = os.path.join(OUT_DIR, "probe-views.blind.md")
SEED = 20260929  # fixed for reproducibility

LABEL_RE = re.compile(r"\*\*观点\s*(\d+)\s*\[[^\]]*\]\*\*")
NOTE_RE = re.compile(r"^\s*-\s*标注[：:]")
SUMMARY_RE = re.compile(r"^\*\*[BCA]\s*小结")
SELFBIAS_RE = re.compile(r"^\>\s*自指偏差声明")
ROLE_RE = re.compile(r"^##\s+([BCA])（")
VIEWPOINT_RE = re.compile(r"^\*\*观点\s+\d+\b")
AGGREGATE_RE = re.compile(r"^##\s+汇总数据表")


def strip_label(line: str) -> str:
    return LABEL_RE.sub(r"**观点 \1**", line)


def main():
    with open(SRC, encoding="utf-8") as fh:
        raw = fh.read()

    out_lines = []
    role_blocks = {}  # role -> list of viewpoint block (list of lines)
    cur_role = None
    cur_block = None
    in_aggregate = False

    header_done = False
    for line in raw.splitlines():
        if AGGREGATE_RE.match(line):
            in_aggregate = True
            continue
        if in_aggregate:
            continue
        if SELFBIAS_RE.match(line):
            continue
        m = ROLE_RE.match(line)
        if m:
            cur_role = m.group(1)
            role_blocks.setdefault(cur_role, [])
            cur_block = None
            out_lines.append(line)  # keep role header
            out_lines.append("")     # blank after header
            continue
        if VIEWPOINT_RE.match(line):
            cur_block = [strip_label(line)]
            role_blocks[cur_role].append(cur_block)
            continue
        if NOTE_RE.match(line):
            continue  # drop inline 标注 notes
        if SUMMARY_RE.match(line):
            continue  # drop 小结 lines
        if cur_block is not None:
            cur_block.append(line)
        else:
            out_lines.append(line)

    # Shuffle within each role (fixed seed) and renumber into blind output
    rng = random.Random(SEED)
    blind_lines = []
    for line in out_lines:
        blind_lines.append(line)

    # Now replace the per-role viewpoint blocks with shuffled+renumbered versions.
    # Rebuild from out_lines is messy; instead reconstruct fully from role_blocks.
    final = []
    # rebuild header portion (everything before first role header)
    # Re-read raw to capture header up to first role
    pre = []
    for line in raw.splitlines():
        if ROLE_RE.match(line):
            break
        if SELFBIAS_RE.match(line):
            continue
        if AGGREGATE_RE.match(line):
            continue
        pre.append(line)
    final.extend(pre)
    final.append("")  # blank

    for role in ["B", "C", "A"]:
        # role header line
        header_line = next(l for l in raw.splitlines() if ROLE_RE.match(l) and ROLE_RE.match(l).group(1) == role)
        final.append(header_line)
        final.append("")
        blocks = role_blocks[role]
        order = list(range(len(blocks)))
        rng.shuffle(order)
        for new_idx, old_idx in enumerate(order, start=1):
            blk = blocks[old_idx]
            renamed = []
            for bl in blk:
                renamed.append(re.sub(r"^\*\*观点\s*\d+\*\*", f"**条目 {new_idx}**", bl))
            final.extend(renamed)
            final.append("")  # blank between viewpoints

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(final).rstrip() + "\n")
    print(f"wrote {OUT}")
    print(f"roles/blocks: " + ", ".join(f"{r}={len(role_blocks[r])}" for r in ['B','C','A']))


if __name__ == "__main__":
    main()
