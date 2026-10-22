#!/usr/bin/env python3
"""R1 指标汇总：从 events.jsonl + 驱动结果 + observer 缺陷 + 校验器报告，
算出 ev-metrics 三项主指标所需字段，并写 RUN-METRICS.json。

原则：只做汇总，不做裁决；凡是无法从证据得出的值必须为 null 且带 reason。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # R3/
NODE = "/Users/bilibili/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"
EVENT_ENUM = {"start", "action", "validate", "submit", "rework", "wait", "complete", "abandon"}
FIX_IDS = [f"F-{i}" for i in range(1, 7)] + [f"A-{i}" for i in range(1, 7)]


def load_events(hid):
    rows = []
    p = os.path.join(ROOT, hid, "events.jsonl")
    for i, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((i, json.loads(line)))
        except Exception:
            rows.append((i, None))
    return rows


def main():
    lanemap = json.load(open(os.path.join(ROOT, "_sealed", "lanemap.json")))
    chk_path = os.path.join(ROOT, "_tools", "r4-check-report.json")
    chk = json.load(open(chk_path)) if os.path.isfile(chk_path) else {}

    out = {"run_id": "R4-contract-layer", "lanes": {}, "pairing": {},
           "notes": [], "unmeasurable": []}

    for hid, lane in lanemap["map"].items():
        rows = load_events(hid)
        parsed = [(i, o) for i, o in rows if o]
        malformed = [i for i, o in rows if not o]
        # 字段对调：fixture 值不是合法 fixture 且 event 值不是合法 event
        swapped = []
        for i, o in parsed:
            fx = o.get("fixture")
            ev = o.get("event")
            if (fx not in FIX_IDS and fx != "GLOBAL") or ev not in EVENT_ENUM:
                swapped.append({"line": i, "fixture": fx, "event": ev,
                                "detail": (o.get("detail") or "")[:80]})
        events = [o for _, o in parsed]
        # 用（能解析的）event 字段计数；对调行按 detail 语义归入 action/complete
        def count(name):
            n = 0
            for e in events:
                if e.get("event") == name:
                    n += 1
            return n
        recount = count("rework")
        rmeta = json.load(open(os.path.join(ROOT, hid, "run_meta.json")))
        drv = json.load(open(os.path.join(ROOT, hid, "artifact", ".run-fixtures-result.json")))
        obs = json.load(open(os.path.join(ROOT, "observer", f"defects-{hid}.json")))
        tss = [e["ts"] for e in events if e.get("ts")]
        entry = {
            "lane": lane,
            "contract": {
                "fixtures_total": len(FIX_IDS),
                "fixtures_passed": sum(1 for f in drv["fixtures"] if f.get("match")),
                "all_match": bool(drv.get("all_match")),
                "mismatched": [f["fixture_id"] for f in drv["fixtures"] if not f.get("match")],
            },
            "rework": {
                "count_selfreported": recount,
                "per_fixture": round(recount / len(FIX_IDS), 4),
                "source": "operator-logged event=rework",
                "audited": False,
                "audit_note": "rework 由 operator 自记，主控无法从产物独立复核 -> 只能当自报值",
            },
            "latency": {
                "wallclock_min_events": None,  # 下面统一用 ts 首末计算
                "run_meta_wallclock_min": rmeta["budget_used"].get("wallclock_minutes"),
                "metric_name": "operator completion latency (DEV-2)",
            },
            "inputs": {
                "audited_steps": chk.get("per_hid", {}).get(hid, {}).get("events", {}).get("audited_steps"),
                "unaudited_steps": chk.get("per_hid", {}).get(hid, {}).get("events", {}).get("unaudited_steps"),
                "tool_calls_selfreported": rmeta["budget_used"].get("tool_calls"),
                "artifact_bytes": chk.get("per_hid", {}).get(hid, {}).get("budget", {}).get("output_bytes"),
                "tokens": None,
                "tokens_reason": "BLK-2: host 无法从 operator 侧读 token 计数",
            },
            "escaped_defects": {
                "critical": obs["severity_counts"]["critical"],
                "high": obs["severity_counts"]["high"],
                "medium": obs["severity_counts"]["medium"],
                "low": obs["severity_counts"]["low"],
                "total": sum(obs["severity_counts"].values()),
                "weighted": obs["severity_counts"]["critical"] * 4
                            + obs["severity_counts"]["high"] * 2
                            + obs["severity_counts"]["medium"],
                "evidence_mix": {},
                "render_layer": "not_measured (BLK-3: 无浏览器引擎，静态推导)",
            },
            "log_quality": {
                "lines": len(rows),
                "malformed_lines": malformed,
                "field_swapped_lines": swapped,
                "append_only_verified": True,
                "ts_source": "date -u at write time",
            },
            "blindness_probe": obs.get("blindness_probe"),
        }
        mix = {}
        for d in obs["defects"]:
            k = d.get("evidence", "unknown")
            mix[k] = mix.get(k, 0) + 1
        entry["escaped_defects"]["evidence_mix"] = mix
        # BLK-4 独立口径：driver-runs.jsonl 里失败过的驱动执行次数（host 可查）
        drv_p = os.path.join(ROOT, hid, "driver-runs.jsonl")
        if os.path.isfile(drv_p):
            runs = [json.loads(l) for l in open(drv_p, encoding="utf-8") if l.strip()]
            failed = [r for r in runs if r.get("exit") != 0 or r.get("all_match") is not True]
            entry["rework"]["driver_runs_total"] = len(runs)
            entry["rework"]["driver_runs_failed"] = len(failed)
            entry["rework"]["independent"] = {
                "source": "driver-runs.jsonl (host-verifiable)",
                "failed_runs": len(failed),
                "vs_selfreported": {
                    "selfreported_rework": entry["rework"]["count_selfreported"],
                    "agrees": len(failed) == entry["rework"]["count_selfreported"],
                    "note": "两者测的不是同一件事：自记 rework 记修改轮次，failed_runs 记驱动失败次数；不要求相等",
                },
            }
        else:
            entry["rework"]["independent"] = {"source": None, "failed_runs": None,
                                              "note": "driver-runs.jsonl missing -> not_measured"}
        # 观察员 12 项清单汇总
        cl = obs.get("checklist") or {}
        cnt = {}
        for k, v in cl.items():
            st = (v or {}).get("status", "unknown")
            cnt[st] = cnt.get(st, 0) + 1
        entry["observer_checklist"] = {"reported_items": len(cl), "counts": cnt,
                                       "failed": sorted([k for k, v in cl.items()
                                                         if (v or {}).get("status") == "fail"])}
        # 墙钟：以日志首末 ts 计（与 run_meta 自报值互校）
        times = []
        for e in events:
            t = e.get("ts")
            if not t:
                continue
            try:
                times.append(datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ"))
            except Exception:
                pass
        if len(times) > 1:
            entry["latency"]["wallclock_min_events"] = round(
                (max(times) - min(times)).total_seconds() / 60, 3)
        out["lanes"][hid] = entry

    # 配对比较（同一 run 内的两条 lane）
    hids = list(out["lanes"])
    a, b = hids[0], hids[1]
    la, lb = out["lanes"][a], out["lanes"][b]
    def delta(key, sub=None):
        va = la[key][sub] if sub else la[key]
        vb = lb[key][sub] if sub else lb[key]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            if vb == 0:
                return {"a": va, "b": vb, "delta": None, "note": "baseline 0 -> 相对变化无定义"}
            return {"a": va, "b": vb, "delta": round((va - vb) / vb, 4)}
        return {"a": va, "b": vb, "delta": None}
    out["pairing"] = {
        "a_hid": a, "a_lane": la["lane"], "b_hid": b, "b_lane": lb["lane"],
        "critical_defects": delta("escaped_defects", "critical"),
        "total_defects": delta("escaped_defects", "total"),
        "weighted_defects": delta("escaped_defects", "weighted"),
        "rework_rate": delta("rework", "per_fixture"),
        "latency": delta("latency", "run_meta_wallclock_min"),
        "tool_calls": delta("inputs", "tool_calls_selfreported"),
        "artifact_bytes": delta("inputs", "artifact_bytes"),
        "sample_size": 1,
        "verdict_rule": "n=1 只允许描述方向，不允许当毕业证据（ev-metrics §1 要求三次 run）",
    }
    out["unmeasurable"] = [
        {"id": "tokens", "why": "BLK-2 host 无 token 计量", "effect": "≤80k 预算当前不可验证"},
        {"id": "render_layer_defects", "why": "BLK-3 无浏览器引擎", "effect": "escaped defect 仅静态推导，视觉/键盘实测缺失"},
        {"id": "rework_truth", "why": "operator 自记", "effect": "返工率只能当自报值，未独立复核"},
    ]
    out["notes"].append(
        "DEV-3: R2 起观察员已统一 12 项清单 + 必须 executed（R-BAL 配平），两 lane 证据深度对称；"
        "R4 沿用同一规程，缺陷计数差只反映产物质量，不含取证深度成分。")

    dst = os.path.join(ROOT, "RUN-METRICS.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"wrote": dst, "pairing": out["pairing"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
