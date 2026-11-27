"""zj-dp-driven §9 实跑观察指标（metrics 采集，Phase-4c）。

Design baseline: docs/designs/zj-dp-driven-skill-design.md §9（5 metric 种子）/ §8 exit condition。

**本模块只交付「可重复测量方法」**：§9 的 exit condition 是「5 个 metric 均有可重复测量方法 +
首份实跑数据落地」。首份实跑数据只能来自真实 destination 的推进（Project B），因此本报告里
所有阈值一律标 `calibrated: false`（token / 轮次 连先验都不设，§9 明令），绝不声称已达基线。

架构（Phase-4c 拍板：全 A 方案）
--------------------------------
* **事件通道 = sidecar JSONL**（`<db-stem>.events.jsonl`，与 carrier 同过程区，§5.4）。
  日志是**观察历史**，不是状态：§3.1 状态单一源要求任何派生
  （`node_view / task_view / pool / is_complete / render / suggest`）**永不读它**——
  由 `test_dp_driven_metrics.py::test_events_inert_to_state` 机械锁死（注入任意事件后
  `render()`/`suggest()` 输出字节相等）。物理分文件正是为了让这条红线可测。
* **写入方 = CLI 层**（决策 2）：`dp_driven_model.py` 保持纯状态机，事件由 `dp_driven_cli.py`
  的各写命令在单写者锁内追加。直接用库的调用方不产事件，属刻意留白而非遗漏。
* **内聚命中率 = 事件证据 + Human annotate**（决策 3）：`orchestrate --execute` 落 optimizer
  产出 plan 的 id 集合，`metrics annotate` 记 Human 的 `kept|split|regrouped` 判定；
  未标注的 plan **不进分母**、单列 `unannotated_plans`，不把缺数据冒充成绩。
* **回灌正确性 = 双记账审计**（决策 4）：§9 原式（blocked 重算调用次数）在本实现里恒无意义——
  blocked 从不缓存、每次现推（§3.2）。等价的可测形式是**独立重实现** §3.2 项级规则，
  与 `node_view` 输出比对，计不一致数（`reflow_check`）。审计范围限于 §3.2 项级；
  §3.6 F2 商图（plan 级）由既有锁测试覆盖，此处不二次实现以免边界细节造成假阳。

Metric 一览（键名与设计页 §9 表逐项对齐）
----------------------------------------
| key | §9 行 | 来源 |
|---|---|---|
| `token_per_effort` | 单 effort token 消耗 | `metrics record --type token`（外部事实，CLI 视野外） |
| `orchestration_rounds` | 编排轮次 | 自动：`orchestrate --execute` 事件数 |
| `cohesion_hit_rate` | 内聚命中率 | annotate verdicts over optimizer-applied plans |
| `reflow_correctness` | 回灌正确性 | `reflow_check(model)` 双记账 |
| `settlement_trigger_rate` | 结算轮触发率 | settlement 事件 / (orchestrate + settlement) |
"""

from __future__ import annotations

import json
import os
import time

from dp_driven_model import (
    DpDriven, DpDrivenError, EDGE_BLOCKS, KIND_FINDING, KIND_TICKET,
    S_ABANDONED, S_DONE, S_OPEN, TERMINAL_STATUSES,
)

EVENT_TYPES = ("orchestrate", "settlement", "plan_terminal", "reassign",
               "membership", "token", "verdict")

VERDICTS = ("kept", "split", "regrouped")

# §9 表初估目标；`calibrated` 恒 False，直到 Project B 首份实跑数据落地。
_SEED_TARGETS = {
    "token_per_effort": {"threshold": None, "direction": None},      # §9 [未决]：不设先验
    "orchestration_rounds": {"threshold": None, "direction": None},  # §9 [未决]：不设先验
    "cohesion_hit_rate": {"threshold": 80.0, "direction": "gte"},
    "reflow_correctness": {"threshold": 100.0, "direction": "eq"},
    "settlement_trigger_rate": {"threshold": 10.0, "direction": "lte"},
}

_NOT_CALIBRATED = "测量方法已实现；阈值待 Project B 首份实跑数据校准（§9 exit condition 后半）"


def _iso_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def default_events_path(db_path: str) -> str:
    """`<db-stem>.events.jsonl` beside the carrier (process zone; §5.4)."""
    stem = db_path
    for ext in (".sqlite", ".sqlite3", ".db"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return stem + ".events.jsonl"


def append_event(db_path: str, etype: str, *, kind: str | None = None,
                 ref_id: int | None = None, agent: str | None = None,
                 value: float | None = None, payload: dict | list | None = None,
                 now: str | None = None) -> dict:
    """Append one observation line to the sidecar log (callers hold the single-writer lock).

    `value` carries a numeric observation (e.g. token count); `payload` carries structure
    (e.g. the optimizer's applied steps). `now` is caller-supplied so tests stay
    deterministic; when omitted the CLI/session clock is used.
    Raises E_METRICS_LOG on an unknown event type — the log must not silently accept
    anything the reader cannot interpret.
    """
    if etype not in EVENT_TYPES:
        raise DpDrivenError("E_METRICS_LOG", f"未知事件类型 {etype!r}，可用 {EVENT_TYPES}")
    if kind is not None and kind not in (KIND_FINDING, KIND_TICKET, "plan"):
        raise DpDrivenError("E_METRICS_LOG", f"未知事件 kind {kind!r}")
    event = {
        "type": etype, "at": now or _iso_now(), "kind": kind, "ref_id": ref_id,
        "agent": agent, "value": value, "payload": payload,
    }
    path = default_events_path(db_path)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def read_events(db_path: str) -> list[dict]:
    """Read the sidecar log. No file ⇒ no events (fresh carrier). Malformed line ⇒
    E_METRICS_LOG with the offending line number (never silently skipped)."""
    path = default_events_path(db_path)
    if not os.path.exists(path):
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                raise DpDrivenError("E_METRICS_LOG", f"{path}:{lineno} 不是合法 JSON 行（{e}）")
            if not isinstance(row, dict) or row.get("type") not in EVENT_TYPES:
                raise DpDrivenError("E_METRICS_LOG", f"{path}:{lineno} 事件结构非法")
            out.append(row)
    return out


def count_by_type(events: list[dict]) -> dict[str, int]:
    counts = {t: 0 for t in EVENT_TYPES}
    for e in events:
        counts[e["type"]] += 1
    return counts


def reflow_check(model: DpDriven) -> dict:
    """§9 metric-4 as a double-entry audit (decision 4).

    Independently re-derives §3.2 item-level `blocked` straight from the edge set, then
    compares against `node_view`'s derived view. Any disagreement is a violation
    (structural staleness would be the failure mode if blocked were ever cached).
    """
    def status_of(kind: str, rid: int) -> str:
        table = model.data["tickets"] if kind == KIND_TICKET else model.data["findings"]
        return table[str(rid)]["status"]

    violations = []
    checked = 0
    nodes = ([(KIND_TICKET, t["id"]) for t in model.data["tickets"].values()]
             + [(KIND_FINDING, f["id"]) for f in model.data["findings"].values()])
    for kind, nid in sorted(nodes):
        checked += 1
        st = status_of(kind, nid)
        # ── independent recomputation (§3.2 literal rule) ──
        expect_reasons = [
            e["id"] for e in sorted(model.data["edges"], key=lambda x: x["id"])
            if e["type"] == EDGE_BLOCKS and (e["to_kind"], e["to_id"]) == (kind, nid)
            and st == S_OPEN and status_of(e["from_kind"], e["from_id"]) != S_DONE
        ]
        hold = (model.data["tickets"] if kind == KIND_TICKET else model.data["findings"]
                )[str(nid)].get("external_hold")
        expect_shown = bool(expect_reasons) or (hold is not None)
        # ── the system under audit ──
        got = model.node_view(kind, nid)
        got_reasons = got.get("blocked_reason") or []
        if bool(sorted(got_reasons)) != bool(sorted(expect_reasons)):
            violations.append({"kind": kind, "ref_id": nid, "field": "blocked",
                               "expected": sorted(expect_reasons), "got": sorted(got_reasons)})
        if bool(got.get("shown_blocked")) is not expect_shown:
            violations.append({"kind": kind, "ref_id": nid, "field": "shown_blocked",
                               "expected": expect_shown, "got": bool(got.get("shown_blocked"))})
    correct = (checked - len({(v["kind"], v["ref_id"]) for v in violations})) if checked else 0
    return {
        "checked": checked,
        "violations": violations,
        "correct": checked > 0 and not violations,
        "rate_pct": round(100.0 * correct / checked, 2) if checked else None,
    }


def optimizer_applied_plans(events: list[dict]) -> list[int]:
    """Plan ids created by `orchestrate --execute` (evidence for cohesion hit rate)."""
    ids: list[int] = []
    for e in events:
        if e["type"] != "orchestrate" or not isinstance(e.get("payload"), list):
            continue
        for step in e["payload"]:
            if isinstance(step, dict) and step.get("action") == "new_plan" and step.get("task_id") is not None:
                ids.append(int(step["task_id"]))
    return sorted(set(ids))


def verdicts(events: list[dict]) -> dict[int, str]:
    out: dict[int, str] = {}
    for e in events:
        if e["type"] == "verdict" and e.get("kind") == "plan" and e.get("ref_id") is not None:
            v = (e.get("payload") or {}).get("verdict")
            if v in VERDICTS:
                out[int(e["ref_id"])] = v        # last annotation wins
    return out


def report(model: DpDriven, events: list[dict], *, audit: bool = True) -> dict:
    """Assemble the 5 §9 metrics. Pure read over model + log; deterministic."""
    counts = count_by_type(events)
    orch = counts["orchestrate"]
    settle = counts["settlement"]
    rounds = orch + settle

    tokens = round(sum(float(e["value"] or 0) for e in events if e["type"] == "token"), 4)
    token_events = counts["token"]

    applied = optimizer_applied_plans(events)
    marks = verdicts(events)
    marked = [p for p in applied if p in marks]
    dist = {v: sum(1 for p in marked if marks[p] == v) for v in VERDICTS}
    kept = dist["kept"]
    hit = round(100.0 * kept / len(marked), 2) if marked else None

    settle_rate = round(100.0 * settle / rounds, 2) if rounds else None

    audit_out = reflow_check(model) if audit else None
    reflow_rate = audit_out["rate_pct"] if audit_out else None

    metrics = {
        "token_per_effort": {
            "value": tokens if token_events else None, "unit": "tokens/session",
            "recorded": token_events, "threshold": _SEED_TARGETS["token_per_effort"]["threshold"],
            "direction": None, "calibrated": False,
            "note": "外部事实，需 `metrics record --type token`；§9 明令不设先验阈值",
        },
        "orchestration_rounds": {
            "value": rounds, "unit": "count",
            "threshold": None, "direction": None, "calibrated": False,
            "breakdown": {"orchestrate": orch, "settlement": settle},
        },
        "cohesion_hit_rate": {
            "value": hit, "unit": "%",
            "threshold": _SEED_TARGETS["cohesion_hit_rate"]["threshold"],
            "direction": _SEED_TARGETS["cohesion_hit_rate"]["direction"],
            "calibrated": False,
            "denominator": {"annotated": len(marked), **dist},
            "unannotated_plans": [p for p in applied if p not in marks],
            "optimizer_plans": applied,
        },
        "reflow_correctness": {
            "value": reflow_rate, "unit": "%",
            "threshold": _SEED_TARGETS["reflow_correctness"]["threshold"],
            "direction": _SEED_TARGETS["reflow_correctness"]["direction"],
            "calibrated": False,
            "audit": audit_out,
        },
        "settlement_trigger_rate": {
            "value": settle_rate, "unit": "%",
            "threshold": _SEED_TARGETS["settlement_trigger_rate"]["threshold"],
            "direction": _SEED_TARGETS["settlement_trigger_rate"]["direction"],
            "calibrated": False,
        },
    }
    return {
        "metrics": metrics,
        "calibration": {"state": "uncalibrated", "note": _NOT_CALIBRATED},
        "events": {"total": len(events), "by_type": counts,
                   "path": default_events_path(model.db_path)},
        "graph": {
            "destination": model.data["meta"].get("destination", ""),
            "tasks": len(model.data["tasks"]), "tickets": len(model.data["tickets"]),
            "findings": len(model.data["findings"]), "edges": len(model.data["edges"]),
            "is_complete": model.is_complete(),
        },
    }


def render_report_md(model: DpDriven, rep: dict) -> str:
    """Markdown rendering of `report()` for the §5.2 governance corpus (deterministic)."""
    g, m, ev = rep["graph"], rep["metrics"], rep["events"]
    lines = ["# Metrics report (§9)", ""]
    lines.append(f"- destination: {g['destination']}")
    lines.append(f"- is_complete: {g['is_complete']}")
    lines.append(f"- events: {ev['total']} 行 @ {ev['path']}")
    lines.append(f"- calibration: **{rep['calibration']['state']}** — {rep['calibration']['note']}")
    lines.append("")
    lines.append("| Metric | Value | Unit | Seed target | Calibrated |")
    lines.append("| --- | --- | --- | --- | --- |")
    order = ("token_per_effort", "orchestration_rounds", "cohesion_hit_rate",
             "reflow_correctness", "settlement_trigger_rate")
    for key in order:
        e = m[key]
        val = "-" if e["value"] is None else e["value"]
        th = e.get("threshold")
        arrow = {"gte": "≥", "lte": "≤", "eq": "="}.get(e.get("direction"), "—")
        tgt = f"{arrow}{th}" if th is not None else "—（§9 未决）"
        lines.append(f"| {key} | {val} | {e['unit']} | {tgt} | {str(e['calibrated']).lower()} |")
    lines.append("")
    coh = m["cohesion_hit_rate"]
    lines.append("## Cohesion evidence (§3.6 F3 / §4.2)")
    lines.append("")
    lines.append(f"- optimizer-applied plans: {coh['optimizer_plans'] or '—'}")
    lines.append(f"- annotated: {coh['denominator']}")
    lines.append(f"- unannotated (excluded from denominator): {coh['unannotated_plans'] or '—'}")
    lines.append("")
    aud = m["reflow_correctness"]["audit"]
    lines.append("## Reflow audit (§3.2 double-entry)")
    lines.append("")
    if aud is None:
        lines.append("- not run")
    else:
        lines.append(f"- items checked: {aud['checked']}")
        lines.append(f"- correct: {aud['correct']}")
        if aud["violations"]:
            lines.append("")
            lines.append("| kind | ref_id | field | expected | got |")
            lines.append("| --- | --- | --- | --- | --- |")
            for v in aud["violations"]:
                lines.append(f"| {v['kind']} | {v['ref_id']} | {v['field']} | {v['expected']} | {v['got']} |")
    lines.append("")
    return "\n".join(lines)


def write_report_md(model: DpDriven, out_path: str, *, events: list[dict] | None = None,
                    audit: bool = True) -> str:
    """Write the report to out_path only (§5.4 placement discipline). Returns path."""
    rep = report(model, events if events is not None else read_events(model.db_path),
                 audit=audit)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report_md(model, rep))
    return out_path


__all__ = ["EVENT_TYPES", "VERDICTS", "append_event", "read_events", "count_by_type",
           "default_events_path", "optimizer_applied_plans", "verdicts", "reflow_check",
           "report", "render_report_md", "write_report_md"]
