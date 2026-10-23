#!/usr/bin/env python3
"""Extract the ZAgentic documentation knowledge graph (A-Box) from the live repo.

Scans `skills/` (buckets + skills) and `docs/` (doc pages with frontmatter) and
emits a JSON graph: nodes (entities) + edges (typed relations). The live code
tree is the source of truth; this regenerates the graph so docs stay fresh.

Writes JSON to stdout. Redirect to docs/ontology/graph.json.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
PERSONAL_DIR = os.path.join(REPO_ROOT, "personal")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

PLATFORMS = ["claude", "codex", "workbuddy"]


# YAML block-scalar indicators we must fold into the value instead of treating
# the marker itself as the value (the naive regex would catch ">-" / "|" and
# report a real multi-line description as an empty placeholder).
_BLOCK_MARKERS = {"-", ">-", ">", "|", "|-", ">+", "|+", ""}


def parse_frontmatter(text):
    fm = {}
    if not text.startswith("---"):
        return fm
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return fm
    end = None
    for j in range(1, len(lines)):
        if lines[j].strip() == "---":
            end = j
            break
    if end is None:
        return fm
    block = lines[1:end]
    k = 0
    while k < len(block):
        line = block[k]
        if not line.strip():
            k += 1
            continue
        m = re.match(r"(\s*)([A-Za-z0-9_-]+)\s*:\s*(.*)", line)
        if not m:
            k += 1
            continue
        indent = len(m.group(1))
        key = m.group(2)
        val = m.group(3).strip()
        if val in _BLOCK_MARKERS:
            # Fold the following more-indented block into this key's value.
            content = []
            kk = k + 1
            base = None
            while kk < len(block):
                nl = block[kk]
                if not nl.strip():
                    content.append("")
                    kk += 1
                    continue
                cur = len(nl) - len(nl.lstrip())
                if cur <= indent and re.match(r"\s*[A-Za-z0-9_-]+\s*:", nl):
                    break
                if base is None:
                    base = cur
                content.append(nl[base:] if cur >= base else nl.strip())
                kk += 1
            fm[key] = "\n".join(content).strip()
            k = kk
        else:
            fm[key] = val
            k += 1
    return fm


def doc_subtype(fm, relpath):
    dk = fm.get("doc-kind", "")
    if dk.startswith("architecture"):
        return "ArchitectureView"
    if dk == "adr":
        return "ADR"
    if dk == "agreement":
        return "Agreement"
    if dk in ("prd", "capability-spec"):
        return "CapabilitySpec"
    if "ui-agent-skills" in relpath:
        return "Contract"
    if dk == "design":
        return "Design"
    return "DocPage"


def build_graph(repo_root=None):
    root = os.path.abspath(repo_root) if repo_root else REPO_ROOT
    skills_dir = os.path.join(root, "skills")
    personal_dir = os.path.join(root, "personal")
    docs_dir = os.path.join(root, "docs")

    nodes = []
    edges = []
    seen = set()
    edge_id = 0

    def add_node(nid, ntype, attrs):
        if nid in seen:
            return
        seen.add(nid)
        nodes.append({"id": nid, "type": ntype, "attrs": attrs})

    def add_edge(etype, frm, to):
        nonlocal edge_id
        if frm not in seen or to not in seen:
            return
        edge_id += 1
        edges.append({"id": f"e{edge_id}", "type": etype, "from": frm, "to": to})

    # Platforms (constants)
    for p in PLATFORMS:
        add_node(f"platform:{p}", "Platform", {"id": p, "discovery": "recursive SKILL.md scan"})

    # SkillBucket + Skill from skills/
    if os.path.isdir(skills_dir):
        for bucket in sorted(os.listdir(skills_dir)):
            bpath = os.path.join(skills_dir, bucket)
            if not os.path.isdir(bpath):
                continue
            add_node(f"bucket:{bucket}", "SkillBucket",
                     {"id": bucket, "kind": "public", "readme_index": os.path.exists(os.path.join(bpath, "README.md"))})
            for sroot, _dirs, files in os.walk(bpath):
                if "SKILL.md" in files:
                    rel = os.path.relpath(sroot, skills_dir)
                    parts = rel.split(os.sep)
                    skill_name = parts[1] if len(parts) >= 2 else bucket
                    sid = f"skill:{bucket}/{skill_name}"
                    with open(os.path.join(sroot, "SKILL.md"), encoding="utf-8") as _f:
                        fm = parse_frontmatter(_f.read())
                    add_node(sid, "Skill", {
                        "id": skill_name, "bucket": bucket,
                        "source_path": os.path.relpath(sroot, root),
                        "name": fm.get("name", ""), "description": fm.get("description", ""),
                        "source": fm.get("source", ""),
                    })
                    add_edge("belongsTo", sid, f"bucket:{bucket}")
                    add_edge("discoveredBy", sid, "platform:claude")
                    add_edge("discoveredBy", sid, "platform:codex")
                    add_edge("discoveredBy", sid, "platform:workbuddy")

    # personal/ bucket (parallel tree, excluded from discovery)
    add_node("bucket:personal", "SkillBucket", {"id": "personal", "kind": "personal", "readme_index": False})
    if os.path.isdir(personal_dir):
        for sroot, _dirs, files in os.walk(personal_dir):
            if "SKILL.md" in files:
                rel = os.path.relpath(sroot, root)
                parts = rel.split(os.sep)
                skill_name = parts[1] if len(parts) >= 2 else "personal"
                sid = f"skill:personal/{skill_name}"
                with open(os.path.join(sroot, "SKILL.md"), encoding="utf-8") as _f:
                    fm = parse_frontmatter(_f.read())
                add_node(sid, "Skill", {"id": skill_name, "bucket": "personal",
                                        "source_path": rel, "name": fm.get("name", ""),
                                        "description": fm.get("description", ""), "source": fm.get("source", "")})
                add_edge("belongsTo", sid, "bucket:personal")

    # public buckets install to platforms
    for n in nodes:
        if n["type"] == "SkillBucket" and n["attrs"].get("kind") == "public":
            for p in PLATFORMS:
                add_edge("installedTo", n["id"], f"platform:{p}")

    # Docs
    doc_ids = []
    if os.path.isdir(docs_dir):
        for sroot, _dirs, files in os.walk(docs_dir):
            if "/ontology" in sroot or "\\ontology" in sroot:
                continue
            for f in files:
                if not f.endswith(".md"):
                    continue
                fpath = os.path.join(sroot, f)
                rel = os.path.relpath(fpath, docs_dir)
                with open(fpath, encoding="utf-8") as _f:
                    fm = parse_frontmatter(_f.read())
                category = rel.split(os.sep)[0]
                subtype = doc_subtype(fm, rel)
                did = f"doc:{rel}"
                attrs = {"id": rel, "doc_kind": fm.get("doc-kind", ""),
                         "authority": fm.get("authority", ""),
                         "authority_id": fm.get("authority-id", ""),
                         "bounded_question": fm.get("bounded-question", ""),
                         "category": category}
                if subtype == "ADR":
                    m = re.match(r"zj-adr/(\d+)", rel)
                    attrs["id"] = m.group(1) if m else rel
                    attrs["status"] = fm.get("status", "")
                add_node(did, subtype, attrs)
                doc_ids.append((did, rel, subtype))

    # Doc relations: routesTo (architecture -> any doc) and references (any -> ADR)
    for did, rel, subtype in doc_ids:
        with open(os.path.join(docs_dir, rel), encoding="utf-8") as _f:
            text = _f.read()
        for m in re.finditer(r"\]\(([^)]+)\)", text):
            target = m.group(1)
            if target.startswith("http") or target.startswith("#"):
                continue
            tpath = os.path.normpath(os.path.join(os.path.dirname(rel), target))
            tpath = tpath.replace("\\", "/")
            tid = f"doc:{tpath}"
            if tid not in seen:
                continue
            if tpath.startswith("zj-adr/"):
                add_edge("references", did, tid)
            elif subtype in ("ArchitectureView",) or (subtype == "DocPage" and rel == "README.md"):
                add_edge("routesTo", did, tid)

    out = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo_root": root,
            "sources": ["skills/", "personal/", "docs/ (excl. ontology/)"],
            "ontology": "docs/ontology/ontology.schema.json",
        },
        "nodes": nodes,
        "edges": edges,
    }
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Extract the ZAgentic documentation knowledge graph (A-Box).")
    ap.add_argument("repo", nargs="?", default=None, help="repo root (default: parent of docs/ontology/)")
    ap.add_argument("--repo", dest="repo_opt", default=None, help="repo root (explicit flag)")
    args = ap.parse_args()
    root = args.repo_opt or args.repo
    json.dump(build_graph(root), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
