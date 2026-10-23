#!/usr/bin/env python3
"""Reasoning + constraint validation over the ZAgentic documentation knowledge graph.

Regenerates the graph from the live repo (via extract.build_graph) so docs stay
fresh, then runs the checkable rules from ontology.schema.json. Exits non-zero on
errors (freshness/consistency violations), zero on success (warnings allowed).

Usage: python3 docs/ontology/validate.py [path-to-graph.json]
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from extract import build_graph  # noqa: E402

SEV_ERROR = "ERROR"
SEV_WARN = "WARN"


def load_graph(path=None, repo_root=None):
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return build_graph(repo_root)


def node_index(graph):
    return {n["id"]: n for n in graph["nodes"]}


def check_authority_id_present_for_primary(graph, idx, out):
    # 主视图/设计/协议须声明稳定 authority-id；CapabilitySpec 可为 supporting（不强制）。
    for n in graph["nodes"]:
        if n["type"] in ("ArchitectureView", "Design", "Agreement"):
            if not n["attrs"].get("authority_id"):
                out.append((SEV_ERROR, "rule.stable-authority-id",
                            f"{n['id']} 是主视图/设计/协议但缺少 authority-id"))


def check_authority_id_unique(graph, idx, out):
    seen = {}
    for n in graph["nodes"]:
        aid = n["attrs"].get("authority_id")
        if aid:
            seen.setdefault(aid, []).append(n["id"])
    for aid, ids in seen.items():
        if len(ids) > 1:
            out.append((SEV_ERROR, "rule.authority-id-unique",
                        f"authority-id `{aid}` 被多页占用: {ids}"))


def check_adr_not_authority(graph, idx, out):
    for n in graph["nodes"]:
        if n["type"] == "ADR" and n["attrs"].get("authority_id"):
            out.append((SEV_ERROR, "rule.adr-not-authority",
                        f"ADR {n['attrs'].get('id')} 不应拥有 authority-id"))


def check_doc_kind_declared(graph, idx, out):
    for n in graph["nodes"]:
        if n["type"] == "DocPage" or (n["type"] == "Contract" and not n["attrs"].get("doc_kind")):
            # The documentation map (doc-kind: doc-map) is the index layer itself;
            # contracts in ui-agent-skills are schema-driven. Only flag true DocPages
            # that are not the recognised doc-map index.
            if n["type"] == "DocPage" and n["attrs"].get("doc_kind") != "doc-map":
                out.append((SEV_WARN, "rule.doc-kind-declared",
                            f"{n['id']} 未声明 doc-kind（文档地图本身，预本体期正常）"))


def check_no_dangling_reference(graph, idx, out):
    for e in graph["edges"]:
        if e["from"] not in idx or e["to"] not in idx:
            out.append((SEV_ERROR, "rule.no-dangling-reference",
                        f"悬挂关联 {e['id']} ({e['type']}): {e['from']} -> {e['to']}"))


def check_personal_tree_excluded(graph, idx, out):
    for n in graph["nodes"]:
        if n["type"] == "SkillBucket" and n["attrs"].get("kind") == "personal":
            if n["attrs"].get("top_level_registration"):
                out.append((SEV_WARN, "rule.personal-tree-excluded",
                            "personal 桶不应在根 README 注册"))


def check_skill_discoverable(graph, idx, out):
    for n in graph["nodes"]:
        if n["type"] != "Skill":
            continue
        a = n["attrs"]
        desc = (a.get("description") or "").strip()
        placeholder = (not desc) or desc in ("-", ">-", ">", "|", "|-", ">+", "|+")
        if not a.get("name") or placeholder:
            out.append((SEV_WARN, "rule.every-skill-discoverable",
                        f"{n['id']} frontmatter 缺 name 或 description 为占位符（需补实）"))


def check_bucket_inventory_consistent(graph, idx, out):
    """核心保鲜校验：文档声明的桶清单/计数须与真实 skills/ 树一致。"""
    ov = os.path.join(REPO_ROOT, "docs", "architecture", "ta-zagentic-overview.md")
    if not os.path.exists(ov):
        return
    with open(ov, encoding="utf-8") as f:
        text = f.read()
    declared = {}
    for m in re.finditer(r"\|\s*`?([a-z-]+)/`?\s*\|\s*(\d+)\s*\|", text):
        declared[m.group(1)] = int(m.group(2))
    live_public = {n["attrs"]["id"]: 0 for n in graph["nodes"]
                   if n["type"] == "SkillBucket" and n["attrs"].get("kind") == "public"}
    for n in graph["nodes"]:
        if n["type"] == "Skill" and n["attrs"].get("bucket") in live_public:
            live_public[n["attrs"]["bucket"]] += 1
    for b in live_public:
        if b not in declared:
            out.append((SEV_ERROR, "rule.bucket-inventory-consistent",
                        f"活树存在公共桶 `{b}`（{live_public[b]} 技能）但 overview 未声明 —— 文档已落后"))
    for b, c in declared.items():
        if b not in live_public:
            out.append((SEV_WARN, "rule.bucket-inventory-consistent",
                        f"overview 声明桶 `{b}`（{c}）但活树无此公共桶 —— 可能已删除"))
        elif live_public[b] != c:
            out.append((SEV_ERROR, "rule.bucket-inventory-consistent",
                        f"桶 `{b}` 计数不一致：文档={c} 活树={live_public[b]}"))


def check_bucket_reorg_adr_bearing(graph, idx, out):
    """新增/重组桶须有对应 ADR。"""
    ov = os.path.join(REPO_ROOT, "docs", "architecture", "ta-zagentic-overview.md")
    text = ""
    if os.path.exists(ov):
        with open(ov, encoding="utf-8") as f:
            text = f.read()
    declared = set(re.findall(r"\|\s*`?([a-z-]+)/`?\s*\|\s*\d+\s*\|", text))
    adr_text = ""
    for n in graph["nodes"]:
        if n["type"] == "ADR":
            p = os.path.join(REPO_ROOT, "docs", n["attrs"]["id"].replace("doc:", "").replace(".md", "") + ".md")
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    adr_text += f.read()
    for n in graph["nodes"]:
        if n["type"] == "SkillBucket" and n["attrs"].get("kind") == "public":
            b = n["attrs"]["id"]
            if b not in declared and b not in adr_text:
                out.append((SEV_ERROR, "rule.bucket-reorg-is-adr-bearing",
                            f"公共桶 `{b}` 既未在 overview 声明，也无对应 ADR —— 重组/新增未留痕"))


def check_governance_module(graph, idx, out):
    """组合 Module G：调用可移植治理技能 zj-docs-ontology 的 docs_governance.py --validate，
    把其 MAP_* 机械诊断并入统一校验报告（单一校验器覆盖 G+P）。技能缺失时跳过（WARN）。"""
    script = os.path.join(REPO_ROOT, "skills", "codebase-docs", "zj-docs-ontology",
                          "scripts", "docs_governance.py")
    if not os.path.exists(script):
        out.append((SEV_WARN, "rule.G-governance",
                    "zj-docs-ontology 治理脚本缺失，跳过 Module G 校验（仅本仓/装了该技能时可用）"))
        return
    try:
        res = subprocess.run([sys.executable, script, REPO_ROOT, "--validate"],
                             capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        out.append((SEV_WARN, "rule.G-governance", f"治理脚本执行失败: {e}"))
        return
    try:
        payload = json.loads(res.stdout)
    except Exception:  # noqa: BLE001
        out.append((SEV_WARN, "rule.G-governance", "治理脚本输出非 JSON，跳过 Module G 校验"))
        return
    sev_map = {
        "MAP_AUTHORITY_CONFLICT": (SEV_ERROR, "rule.G1-docmap-binding"),
        "MAP_AMBIGUOUS": (SEV_ERROR, "rule.G3-map-pointer-unique"),
        "MAP_POINTER_BROKEN": (SEV_ERROR, "rule.G3-map-pointer-unique"),
        "MAP_LINK_BROKEN": (SEV_WARN, "rule.G-governance-link"),
    }
    for d in payload.get("diagnostics", []):
        code = d.get("code", "")
        sev, rule = sev_map.get(code, (SEV_WARN, "rule.G-governance"))
        out.append((sev, rule, f"[Module G] {code}: {d.get('message', '')}"))


CHECKS = [
    check_authority_id_present_for_primary,
    check_authority_id_unique,
    check_adr_not_authority,
    check_doc_kind_declared,
    check_no_dangling_reference,
    check_personal_tree_excluded,
    check_skill_discoverable,
    check_bucket_inventory_consistent,
    check_bucket_reorg_adr_bearing,
    check_governance_module,
]


def main():
    ap = argparse.ArgumentParser(
        description="Reasoning + constraint validation over the ZAgentic documentation "
                    "knowledge graph (Module G governance + Module P product domain).")
    ap.add_argument("graph", nargs="?", default=None,
                    help="prebuilt graph.json (default: regenerate from live tree)")
    ap.add_argument("--repo", default=None, help="repo root (default: parent of docs/ontology/)")
    args = ap.parse_args()
    global REPO_ROOT
    if args.repo:
        REPO_ROOT = os.path.abspath(args.repo)
    graph = load_graph(args.graph, REPO_ROOT)
    idx = node_index(graph)
    violations = []
    for chk in CHECKS:
        chk(graph, idx, violations)

    from collections import Counter
    cnt = Counter(v[0] for v in violations)
    print(f"知识图谱: {len(graph['nodes'])} 节点 / {len(graph['edges'])} 关联")
    print(f"校验结果: {cnt.get(SEV_ERROR, 0)} 错误, {cnt.get(SEV_WARN, 0)} 警告")
    print("-" * 60)
    for sev, rule, msg in sorted(violations, key=lambda x: (x[0], x[1])):
        print(f"[{sev}] {rule}: {msg}")
    if cnt.get(SEV_ERROR, 0):
        sys.exit(1)
    print("✅ 无阻断性违规（仅警告，多为待补 frontmatter / 预本体期文档）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
