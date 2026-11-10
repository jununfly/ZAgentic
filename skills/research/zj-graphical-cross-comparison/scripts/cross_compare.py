#!/usr/bin/env python3
"""zj-graphical-cross-comparison — 产品项目图式横比模型的操作化仪器。

把《产品项目图式横比模型》的纸面契约变成确定性机械闸门与摘要计算。
权威方法论 SSOT 是源仓库 docs/agreements/product-project-graphical-cross-comparison-model.md，
仅源仓库维护、不随 skill 安装；本文件与其 references 是可操作映射，不复制模型本体。

纪律:
- 只做确定性校验与计算，不做语义裁决。场景集给定、未决关系裁决、场景内语义等价、
  可选场景集盲区核对一律归 Human；脚本只验这些裁决是否留痕、形状是否合法。
- 摘要指标恒标注 not_for_conclusion，不得用于排序 / 裁决 / 回灌 / 优先级。
- YAML 是 agreement 定义的一等 SoT 形态，脚本按扩展名直接消费；复用仓库既有 PyYAML，
  缺失时明确报错而非静默降级。JSON 是 YAML 1.2 的合法实例，供无 PyYAML 环境零依赖运行。
- 无显式 --out 不写任何文件，避免污染安装树。

子命令:
  init      写出一份最小输入模板(JSON)，必须给 --out
  validate  加载 bundle -> 跑 CHK-01..11 -> 打印结果；有 ERROR 时 exit 1
  report    先跑闸门，通过后计算摘要指标；--out 可选，缺省只打印
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "zj-graphical-cross-comparison/bundle/v1"

VALID_VERDICTS = {"native", "adapted", "unsupported", "unknown"}
VALID_CONTEXT_VERDICTS = {"satisfied", "violated", "unknown"}
VALID_CONTEXT_KINDS = {"constraint", "data-contract", "external-dep", "actor"}
VALID_RELATION_KINDS = {"mutually-exclusive", "ordering"}
VALID_SOURCES = {"evidence", "human-ruling", "assumption"}
VALID_NODE_KINDS = {"feature": "F::", "capability": "T::"}
ID_PREFIXES = {
    "F", "T", "S", "X", "D", "RC", "CTX", "SC", "DE", "SCENE-SET", "RULING", "EQ",
}
FORBIDDEN_SCENE_FIELDS = {"nodes", "modules", "module", "members", "implementation", "required-nodes"}
CHECK_CODES = tuple(f"CHK-{n:02d}" for n in range(1, 12))
ELEMENT_FIELDS = (
    "nodes", "slice-edges", "cross-cutting-paths", "dependency-edges",
    "relation-constraints", "context-entries",
)


@dataclass(frozen=True)
class Check:
    code: str
    severity: str
    problems: tuple[str, ...] = ()
    note: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_id(value: Any) -> bool:
    if not isinstance(value, str) or "::" not in value:
        return False
    prefix, tail = value.split("::", 1)
    return prefix in ID_PREFIXES and bool(tail.strip())


def graphs_of(data: dict) -> list[dict]:
    return [g for g in as_list(data.get("graphs")) if isinstance(g, dict)]


def scene_set_of(data: dict) -> dict:
    value = data.get("scene-set")
    return value if isinstance(value, dict) else {}


def node_map(graph: dict) -> dict[str, dict]:
    return {
        n.get("id"): n
        for n in as_list(graph.get("nodes"))
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    }


def context_ids(data: dict) -> set[str]:
    result = set()
    for entry in as_list(scene_set_of(data).get("context-entries")):
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            result.add(entry["id"])
    for graph in graphs_of(data):
        for entry in as_list(graph.get("context-entries")):
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                result.add(entry["id"])
    return result


def all_node_index(data: dict) -> set[str]:
    return {
        f"{g.get('project')}::{nid}"
        for g in graphs_of(data)
        for nid in node_map(g)
    }


def graph_label(graph: dict, index: int) -> str:
    return graph.get("project") or f"graphs[{index}]"


def is_ctx_id(value: Any) -> bool:
    return str(value).startswith("CTX::")


def check_01(data: dict) -> Check:
    problems: list[str] = []
    if data.get("schema") != SCHEMA:
        problems.append(f"schema 必须等于 {SCHEMA}")
    scene_set = scene_set_of(data)
    for key in ("id", "version-pin", "source"):
        if not nonempty(scene_set.get(key)):
            problems.append(f"scene-set.{key} 缺失或非字符串")
    for scene in as_list(scene_set.get("scenes")):
        if not isinstance(scene, dict) or not valid_id(scene.get("id")):
            problems.append(f"scene-set.scenes 存在非法稳定 ID: {scene}")
    seen_global: set[str] = set()
    for index, graph in enumerate(graphs_of(data)):
        label = graph_label(graph, index)
        if not nonempty(graph.get("project")):
            problems.append(f"{label}: project 缺失")
        if not nonempty(graph.get("version-pin")):
            problems.append(f"{label}: version-pin 缺失（每项目须固定版本）")
        seen_local: set[str] = set()
        for field in ELEMENT_FIELDS:
            for item in as_list(graph.get(field)):
                if not isinstance(item, dict):
                    problems.append(f"{label}.{field} 含非对象元素")
                    continue
                ident = item.get("id")
                if not valid_id(ident):
                    problems.append(f"{label}.{field} 存在非法稳定 ID: {ident}")
                    continue
                if ident in seen_local:
                    problems.append(f"{label}.{field} ID 重复: {ident}")
                seen_local.add(ident)
        for item in as_list(graph.get("undeclared-relations")):
            if isinstance(item, dict) and not nonempty(item.get("id")):
                problems.append(f"{label}.undeclared-relations 存在无 id 条目")
    for item in as_list(data.get("difference-entries")):
        if not isinstance(item, dict):
            problems.append("difference-entries 含非对象元素")
            continue
        ident = item.get("id")
        if not valid_id(ident):
            problems.append(f"difference-entries 存在非法稳定 ID: {ident}")
        elif ident in seen_global:
            problems.append(f"difference-entries ID 重复: {ident}")
        else:
            seen_global.add(ident)
    return Check("CHK-01", "error", tuple(problems), "版本与稳定 ID")


def check_02(data: dict) -> Check:
    problems: list[str] = []
    for index, graph in enumerate(graphs_of(data)):
        label = graph_label(graph, index)
        nodes = node_map(graph)
        for ident, node in nodes.items():
            expected = VALID_NODE_KINDS.get(node.get("kind"))
            if expected is None:
                problems.append(f"{label}: 节点 {ident} 的 kind 只能是 feature / capability")
            elif not ident.startswith(expected):
                problems.append(f"{label}: 节点 {ident} 的 ID 前缀与 kind 不符，应为 {expected}")
        slices = [s for s in as_list(graph.get("slice-edges")) if isinstance(s, dict)]
        slice_ids = {s.get("id") for s in slices}
        for s in slices:
            members = as_list(s.get("members"))
            if not members:
                problems.append(f"{label}: 竖切片 {s.get('id')} 的 members 为空")
            for member in members:
                if member not in nodes:
                    problems.append(f"{label}: 竖切片 {s.get('id')} 的成员 {member} 不属于 V")
                if is_ctx_id(member):
                    problems.append(f"{label}: 上下文条目 {member} 不得进入 S.members")
            has_feature = any(nodes.get(m, {}).get("kind") == "feature" for m in members)
            has_capability = any(nodes.get(m, {}).get("kind") == "capability" for m in members)
            if not (has_feature and has_capability):
                problems.append(f"{label}: 竖切片 {s.get('id')} 须至少含 1 个 F 与 1 个 T")
            scenario = s.get("scenario")
            if not isinstance(scenario, dict) or any(
                not nonempty(scenario.get(k)) for k in ("start", "end", "observable")
            ):
                problems.append(f"{label}: 竖切片 {s.get('id')} 缺少起点 / 终点 / 可观察结果")
        for dep in as_list(graph.get("dependency-edges")):
            if not isinstance(dep, dict):
                continue
            if dep.get("relation", "requires") != "requires":
                problems.append(f"{label}: 依赖边 {dep.get('id')} 的语义只能是 requires")
            for endpoint in ("from", "to"):
                target = dep.get(endpoint)
                if target not in nodes:
                    problems.append(f"{label}: 依赖边 {dep.get('id')} 的 {endpoint} 不属于 V")
                if is_ctx_id(target):
                    problems.append(f"{label}: 上下文条目不得进入有向依赖图")
        for path in as_list(graph.get("cross-cutting-paths")):
            if not isinstance(path, dict):
                continue
            for ref in as_list(path.get("appears_in")):
                if ref not in slice_ids:
                    problems.append(f"{label}: 横切路径 {path.get('id')} 的 appears_in 指向不存在的竖切片 {ref}")
        for rc in as_list(graph.get("relation-constraints")):
            if not isinstance(rc, dict):
                continue
            if rc.get("kind") not in VALID_RELATION_KINDS:
                problems.append(f"{label}: 图内关系约束 {rc.get('id')} 的 kind 非法")
            for member in as_list(rc.get("members")):
                if member not in nodes or is_ctx_id(member):
                    problems.append(f"{label}: 图内关系约束 {rc.get('id')} 的成员 {member} 非法")
    return Check("CHK-02", "error", tuple(problems), "竖切片、节点与依赖边合法性")


def check_03(data: dict) -> Check:
    unruled: list[str] = []
    for index, graph in enumerate(graphs_of(data)):
        label = graph_label(graph, index)
        for relation in as_list(graph.get("undeclared-relations")):
            if not isinstance(relation, dict):
                continue
            if not nonempty(relation.get("ruling-by")) or not nonempty(relation.get("effective-version")):
                unruled.append(f"{label}::{relation.get('id')}")
    if not unruled:
        return Check("CHK-03", "error", (), "未决关系已全部裁决")
    # 未裁决关系一律 fail-closed：无论是否已有 difference-entries，都阻塞进入 Stage 3（不得签发报告）。
    return Check(
        "CHK-03", "error",
        (f"未裁决关系按 fail-closed 处理，阻塞进入 Stage 3: {', '.join(unruled)}",),
        "未决关系与 fail-closed",
    )
def check_04(data: dict) -> Check:
    problems: list[str] = []
    scene_set = scene_set_of(data)
    if scene_set.get("derived-from-graphs") is not False:
        problems.append("场景集须显式声明 derived-from-graphs: false（外部尺子，不来自任何 Graph）")
    for entry in as_list(scene_set.get("scenes")) + as_list(scene_set.get("context-entries")):
        if not isinstance(entry, dict):
            continue
        for forbidden in FORBIDDEN_SCENE_FIELDS:
            if forbidden in entry:
                problems.append(f"场景集条目 {entry.get('id')} 含禁止字段 {forbidden}（不得规定节点 / 模块 / 实现划分）")
    return Check("CHK-04", "error", tuple(problems), "场景集外部性")


def check_05(data: dict) -> Check:
    problems: list[str] = []
    index = all_node_index(data)
    for ruling in as_list(data.get("equivalence-rulings")):
        if not isinstance(ruling, dict):
            continue
        label = ruling.get("id", "unnamed")
        for side in ("left", "right"):
            if ruling.get(side) not in index:
                problems.append(f"等价裁决 {label} 的 {side} 未指向已存在的跨项目节点")
        if not nonempty(ruling.get("left-acceptance")) or not nonempty(ruling.get("right-acceptance")):
            problems.append(f"等价裁决 {label} 须引用双方 acceptance")
        if not nonempty(ruling.get("ruling-by")):
            problems.append(f"等价裁决 {label} 缺裁决人")
    return Check("CHK-05", "error", tuple(problems), "场景内语义等价裁决")


def check_06(data: dict) -> Check:
    problems: list[str] = []
    known_contexts = context_ids(data)
    for de in as_list(data.get("difference-entries")):
        if not isinstance(de, dict):
            continue
        label = de.get("id", "unnamed")
        verdict = de.get("verdict")
        if verdict not in VALID_VERDICTS:
            problems.append(f"{label}: 供给 verdict 非法: {verdict}")
        if verdict in ("native", "adapted") and not as_list(de.get("evidence-refs")):
            problems.append(f"{label}: {verdict} 须绑定一手材料证据")
        if verdict == "adapted" and not nonempty(de.get("adaptation-target")):
            problems.append(f"{label}: adapted 须点明适配对象")
        if verdict == "unsupported" and not nonempty(de.get("negative-statement-ref")):
            problems.append(f"{label}: unsupported 须绑定一手材料中的显式否定陈述")
        if verdict == "unknown" and not nonempty(de.get("verification-plan")):
            problems.append(f"{label}: unknown 须附最小验证计划，且不进清单定量部分")
        refs = set(as_list(de.get("context-refs")))
        verdicts = [cv for cv in as_list(de.get("context-verdicts")) if isinstance(cv, dict)]
        if refs != {cv.get("ref") for cv in verdicts}:
            problems.append(f"{label}: context-refs 与 context-verdicts 的 ref 集合不一致")
        for cv in verdicts:
            ref = cv.get("ref")
            if ref not in known_contexts:
                problems.append(f"{label}: 上下文引用 {ref} 不存在")
            state = cv.get("verdict")
            if state not in VALID_CONTEXT_VERDICTS:
                problems.append(f"{label}: 上下文判定 {state} 非法，不可与供给四态混用")
            if state == "unknown" and not nonempty(cv.get("verification-plan")):
                problems.append(f"{label}: 上下文 unknown 须附最小验证计划")
            if state == "violated" and not nonempty(cv.get("negative-evidence-ref")):
                problems.append(f"{label}: 上下文 violated 须绑定显式否定证据")
    return Check("CHK-06", "error", tuple(problems), "供给四态与上下文三态判据")


def check_07(data: dict) -> Check:
    review = data.get("optional-scene-pool-review")
    problems: list[str] = []
    if not isinstance(review, dict) or not nonempty(review.get("notes")):
        problems.append("可选场景集核对留痕缺失或 notes 为空")
    return Check(
        "CHK-07", "error", tuple(problems),
        "逐项目原样摘录与零语义操作属 Human 复核项；脚本只验核对留痕存在",
    )


def check_08(data: dict) -> Check:
    problems: list[str] = []
    for index, graph in enumerate(graphs_of(data)):
        label = graph_label(graph, index)
        connected: set[str] = set()
        for s in as_list(graph.get("slice-edges")):
            if isinstance(s, dict):
                connected.update(as_list(s.get("members")))
        orphan = {ident for ident in node_map(graph) if ident not in connected}
        declared = set(as_list(graph.get("orphan-nodes")))
        if orphan != declared:
            problems.append(
                f"{label}: 孤儿节点须显式列出并进入缺口清单；计算得 {sorted(orphan)}，登记得 {sorted(declared)}"
            )
    return Check("CHK-08", "warning", tuple(problems), "孤儿节点为就绪度提示，不阻塞")


def check_09(data: dict) -> Check:
    problems: list[str] = []
    sections = [s for s in as_list(data.get("report-sections")) if isinstance(s, dict)]
    if len(sections) != 8:
        problems.append(f"报告须八节齐全，当前 {len(sections)} 节")
    if [s.get("n") for s in sections] != list(range(1, 9)):
        problems.append("报告小节编号须为 1..8 且顺序固定")
    for section in sections:
        sources = as_list(section.get("sources"))
        if not sources or any(source not in VALID_SOURCES for source in sources):
            problems.append(f"报告第 {section.get('n')} 节须标明证据 / Human 裁决 / 假设三类来源")
    if data.get("summary-metrics-usage") != "display-only":
        problems.append("summary-metrics-usage 必须为 display-only；摘要指标不参与结论")
    return Check("CHK-09", "error", tuple(problems), "报告结构与结论载体")


def check_10(data: dict) -> Check:
    problems: list[str] = []
    seen: set[str] = set()

    def inspect(entries: list[Any], expected_scope: str, label: str) -> None:
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append(f"{label} 含非对象上下文条目")
                continue
            ident = entry.get("id")
            if not valid_id(ident) or not is_ctx_id(ident):
                problems.append(f"{label}: 上下文条目 ID {ident} 非法")
            elif ident in seen:
                problems.append(f"{label}: 上下文条目 ID 重复 {ident}")
            else:
                seen.add(ident)
            if entry.get("scope") != expected_scope:
                problems.append(f"{label}: {ident} 的 scope 应为 {expected_scope}")
            if entry.get("kind") not in VALID_CONTEXT_KINDS:
                problems.append(f"{label}: {ident} 的 kind 非法")
            if not nonempty(entry.get("statement")) or not nonempty(entry.get("evidence-ref")):
                problems.append(f"{label}: {ident} 缺 statement 或 evidence-ref")
            for forbidden in ("nodes", "members", "modules"):
                if forbidden in entry:
                    problems.append(f"{label}: {ident} 不得携带图元素字段 {forbidden}")

    inspect(as_list(scene_set_of(data).get("context-entries")), "domain", "scene-set.context-entries")
    for index, graph in enumerate(graphs_of(data)):
        inspect(as_list(graph.get("context-entries")), "project",
                f"{graph_label(graph, index)}.context-entries")
    return Check("CHK-10", "error", tuple(problems), "上下文条目契约：旁挂、不进 V / S.members / 依赖图")


def run_checks(data: Any) -> list[Check]:
    if not isinstance(data, dict):
        return [Check(code, "error", ("bundle 顶层必须是对象",)) for code in CHECK_CODES]
    return [
        check_01(data), check_02(data), check_03(data), check_04(data), check_05(data),
        check_06(data), check_07(data), check_08(data), check_09(data), check_10(data),
        check_11(data),
    ]


def check_11(data: dict) -> Check:
    """场景映射裁决留痕：每条 slice->scene 映射须带 ruling-ref 与 ruling-by，且引用合法。

    契约要求 scene-mapping[] 为「slice -> scene，带 ruling-ref 与 ruling-by」；
    机械验留痕与引用合法性，裁决内容归 Human（与 CHK-03 同一纪律）。
    竖切片引用沿用跨项目限定形态 ``<project>::<slice-id>``（与 difference-entries
    的 supporting-slices 一致），短形态 ``<slice-id>`` 亦接受。
    """
    problems: list[str] = []
    scene_ids = {s.get("id") for s in as_list(scene_set_of(data).get("scenes"))}
    qualified_slice_ids: set[str] = set()
    short_slice_ids: set[str] = set()
    for graph in graphs_of(data):
        for s in as_list(graph.get("slice-edges")):
            if isinstance(s, dict):
                short_slice_ids.add(s.get("id"))
                qualified_slice_ids.add(f"{graph.get('project')}::{s.get('id')}")
    for index, entry in enumerate(as_list(data.get("scene-mapping"))):
        if not isinstance(entry, dict):
            problems.append(f"scene-mapping[{index}] 必须是对象")
            continue
        if not nonempty(entry.get("ruling-ref")) or not nonempty(entry.get("ruling-by")):
            problems.append(f"scene-mapping[{index}] 须带 ruling-ref 与 ruling-by（裁决留痕）")
        ref = entry.get("slice")
        if not isinstance(ref, str) or (ref not in qualified_slice_ids and ref not in short_slice_ids):
            problems.append(
                f"scene-mapping[{index}] 的 slice 须引用已存在的竖切片"
                f"（<project>::<slice-id> 或 <slice-id>），得到 {ref!r}"
            )
        scene = entry.get("scene")
        if not isinstance(scene, str) or scene not in scene_ids:
            problems.append(f"scene-mapping[{index}] 的 scene 须引用固定场景集中的场景，得到 {scene!r}")
    return Check("CHK-11", "error", tuple(problems), "场景映射裁决留痕")


def summary_metrics(data: dict) -> dict:
    """摘要指标只作展示；上下文条目与 unknown 元素都不进分子分母的污染路径。"""
    per_graph: list[dict] = []
    undecided_stock = 0
    for index, graph in enumerate(graphs_of(data)):
        label = graph_label(graph, index)
        nodes = [n for n in as_list(graph.get("nodes")) if isinstance(n, dict)]
        slices = [s for s in as_list(graph.get("slice-edges")) if isinstance(s, dict)]
        deps = [d for d in as_list(graph.get("dependency-edges")) if isinstance(d, dict)]
        paths = [p for p in as_list(graph.get("cross-cutting-paths")) if isinstance(p, dict)]
        constraints = [r for r in as_list(graph.get("relation-constraints")) if isinstance(r, dict)]
        undecided_stock += sum(
            1 for r in as_list(graph.get("undeclared-relations"))
            if isinstance(r, dict) and not nonempty(r.get("ruling-by"))
        )

        elements = nodes + slices + deps + paths + constraints
        bound = sum(1 for item in elements if nonempty(item.get("evidence-ref")))
        node_ids = {n.get("id") for n in nodes}
        adjacency: dict[str, set[str]] = {ident: set() for ident in node_ids}
        for dep in deps:
            source, target = dep.get("from"), dep.get("to")
            if source in adjacency and target in adjacency:
                adjacency[source].add(target)

        reach: dict[str, set[str]] = {}
        for start in adjacency:
            seen: set[str] = set()
            stack = list(adjacency[start])
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                stack.extend(adjacency.get(current, ()))
            reach[start] = seen

        visited: set[str] = set()
        scc_sizes: list[int] = []
        for node in adjacency:
            if node in visited:
                continue
            component = {node} | {
                other for other in adjacency
                if other != node and other in reach[node] and node in reach[other]
            }
            visited |= component
            if len(component) > 1:
                scc_sizes.append(len(component))

        slice_hits: dict[str, int] = {}
        for s in slices:
            for member in as_list(s.get("members")):
                slice_hits[member] = slice_hits.get(member, 0) + 1
        connected = {member for member, count in slice_hits.items() if count >= 1}
        shared = {member for member, count in slice_hits.items() if count >= 2}
        fan_in = {
            node: sum(1 for source in adjacency if node in adjacency[source])
            for node in adjacency
        }
        total_nodes = len(node_ids) or 1
        per_graph.append({
            "project": label,
            "evidence-binding-coverage": round(bound / (len(elements) or 1), 4),
            "slice-coverage": round(len(connected & node_ids) / total_nodes, 4),
            "sharing-degree": round(len(shared & node_ids) / total_nodes, 4),
            "scc-size-distribution": sorted(scc_sizes),
            "max-dependency-closure": max((len(r) + 1 for r in reach.values()), default=0),
            "fan-in-distribution": fan_in,
            "note": "无向连通分量不进入本模型；SCC 只统计环",
        })
    return {
        "not_for_conclusion": True,
        "usage": "display-only",
        "graphs": per_graph,
        "undecided-stock": undecided_stock,
    }


def template() -> dict:
    return {
        "schema": SCHEMA,
        "scene-set": {
            "id": "SCENE-SET::v1",
            "version-pin": "<固定版本>",
            "source": "<产品域一手材料>",
            "derived-from-graphs": False,
            "scenes": [{"id": "SC::example", "start": "<起点>", "end": "<终点>", "observable": "<可观察结果>"}],
            "context-entries": [],
        },
        "graphs": [{
            "project": "P1",
            "version-pin": "<commit-or-release>",
            "nodes": [
                {"id": "F::example", "kind": "feature", "statement": "<可独立陈述>",
                 "acceptance": "<可独立验收>", "evidence-ref": ""},
                {"id": "T::example", "kind": "capability", "statement": "<可独立陈述>",
                 "acceptance": "<可独立验收>", "evidence-ref": ""},
            ],
            "slice-edges": [{
                "id": "S::example", "members": ["F::example", "T::example"],
                "scenario": {"start": "<起点>", "end": "<终点>", "observable": "<可观察结果>"},
                "evidence-ref": "",
            }],
            "cross-cutting-paths": [],
            "dependency-edges": [],
            "relation-constraints": [],
            "context-entries": [],
            "undeclared-relations": [],
            "orphan-nodes": [],
        }],
        "scene-mapping": [],
        "equivalence-rulings": [],
        "optional-scene-pool-review": {"pool-size": 0, "covered": 0, "project-specific": 0, "notes": "<Human 核对留痕>"},
        "difference-entries": [],
        "report-sections": [
            {"n": n, "title": title, "sources": ["evidence"]}
            for n, title in enumerate((
                "图清单与版本 pin", "场景映射表与裁决记录", "差异条目清单", "可选场景集核对留痕",
                "场景内语义等价裁决记录", "摘要指标（标注不参与结论）", "与母模型的可选回灌素材",
                "完成标准自检",
            ), 1)
        ],
        "summary-metrics-usage": "display-only",
    }


def is_yaml_path(path: str) -> bool:
    return Path(path).suffix.lower() in (".yaml", ".yml")


def load(path: str) -> dict:
    """YAML 与 JSON 都是一等输入；YAML 与 agreement 的 SoT 形状字面一致。"""
    with open(path, encoding="utf-8") as handle:
        if is_yaml_path(path):
            try:
                import yaml
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "YAML bundle requires PyYAML; install requirements.txt or use a .json bundle"
                ) from exc
            data = yaml.safe_load(handle)
            if not isinstance(data, dict):
                raise ValueError("YAML bundle must be a mapping at the top level")
            return data
        return json.load(handle)


def render_document(data: dict, path: str) -> str:
    """按目标扩展名输出：YAML 与 agreement 字面一致，JSON 为零依赖等价实例。"""
    if is_yaml_path(path):
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError("YAML output requires PyYAML; use a .json --out path") from exc
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def print_checks(checks: list[Check], stream=None) -> tuple[int, int]:
    """诊断默认走 stdout；report 子命令改走 stderr，保持 stdout 是纯 JSON。"""
    stream = stream or sys.stdout
    errors = 0
    warnings = 0
    for check in checks:
        if check.ok:
            print(f"PASS {check.code}  {check.note}", file=stream)
            continue
        if check.severity == "warning":
            warnings += 1
            print(f"WARN {check.code}  {check.note}", file=stream)
        else:
            errors += 1
            print(f"FAIL {check.code}  {check.note}", file=stream)
        for problem in check.problems:
            print(f"       - {problem}", file=stream)
    print(f"\n{len(checks)} checks: {errors} ERROR, {warnings} WARN", file=stream)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="产品项目图式横比模型的确定性闸门仪器")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="写出最小输入模板")
    p_init.add_argument("--out", required=True, help="输出路径（.yaml/.yml 或 .json）；必须显式给出")

    p_validate = sub.add_parser("validate", help="只跑 CHK-01..11")
    p_validate.add_argument("--input", required=True, help="bundle 路径（YAML 或 JSON）")

    p_report = sub.add_parser("report", help="跑闸门并计算摘要指标")
    p_report.add_argument("--input", required=True, help="bundle 路径（YAML 或 JSON）")
    p_report.add_argument("--out", default=None, help="可选（.yaml/.yml 或 .json）；不给则只打印")

    args = parser.parse_args(argv)
    if args.command == "init":
        try:
            rendered = render_document(template(), args.out)
        except (RuntimeError, OSError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        print(f"template written: {args.out}")
        return 0

    try:
        data = load(args.input)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: unable to read bundle: {exc}", file=sys.stderr)
        return 1
    checks = run_checks(data)
    diagnostic_stream = sys.stderr if args.command == "report" else sys.stdout
    errors, _ = print_checks(checks, diagnostic_stream)
    if errors:
        print("不得签发横比报告；产出只能作为过程材料。", file=sys.stderr)
        return 1
    if args.command == "validate":
        return 0

    metrics = summary_metrics(data)
    if args.out:
        try:
            rendered = render_document(metrics, args.out)
        except (RuntimeError, OSError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        print(f"metrics written: {args.out}")
    else:
        sys.stdout.write(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
