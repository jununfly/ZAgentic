#!/usr/bin/env python3
"""Fence-aware Markdown section splitter (generic, consumer-agnostic).

Lifted from zj-discuss/check_subdoc.py so any consumer of zj-doc-collab can split
a Markdown document into (heading, body) pairs without depending on the discuss
skill. The logic is identical; no consumer vocabulary is encoded here.

Usage:

    from markdown_sections import split_sections
    sections = split_sections(text)  # list of (heading, body)
"""


def split_sections(text):
    """Split Markdown into (heading, body) pairs by ATX headings.

    Fence-aware: lines inside a ``` / ~~~ code fence are never treated as
    headings, even if they start with ``#``. This keeps a digest block (or any
    code block) inert to viewpoint/conclusion detection.
    """
    sections = []
    heading = None
    body = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            body.append(line)  # a fence delimiter is content of the section
            continue
        if not in_fence and line.startswith("#"):
            if heading is not None:
                sections.append((heading, "\n".join(body)))
            heading = line.strip()
            body = []
        else:
            body.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body)))
    return sections


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: markdown_sections.py <file>", file=sys.stderr)
        raise SystemExit(1)
    data = open(sys.argv[1], encoding="utf-8").read()
    for heading, body in split_sections(data):
        print(heading)
        print("---")
        print(body)
        print()
