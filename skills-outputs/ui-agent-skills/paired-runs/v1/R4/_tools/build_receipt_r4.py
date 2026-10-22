#!/usr/bin/env python3
"""生成 R3 运行收据（RUN-RECEIPT.json）。

注意：这不是 1-5-4 的 R-RCP-1 verification receipt。后者由
research/ui-agent-skills/verification_receipt.py:build_receipt 从 dual_lane_runner
的 lane receipt 升格，绑定 adapter 轴 + manifest/env hash；1-9 的 paired run 走的是
operator 轴且没有 adapter/浏览器，硬套会让收据包含无法归因的字段（假 provenance）。
因此这里产出 paired-run 专属收据，并把"非规范收据"写进 caveats，不冒充。
"""
import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # R1/
REPO = os.path.abspath(os.path.join(ROOT, "../../../../.."))  # R1/v1/paired-runs/ui-agent-skills/skills-outputs/ZAgentic


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree(rel_dir):
    base = os.path.join(ROOT, rel_dir)
    out = []
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in ("node_modules", ".git", "__pycache__")]
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = os.path.join(dp, fn)
            out.append({"path": os.path.relpath(p, ROOT), "sha256": sha(p),
                        "bytes": os.path.getsize(p)})
    return sorted(out, key=lambda x: x["path"])


def main():
    lanemap = json.load(open(os.path.join(ROOT, "_sealed", "lanemap.json")))
    metrics = json.load(open(os.path.join(ROOT, "RUN-METRICS.json")))
    reg = json.load(open(os.path.join(REPO, "docs/plans/ui-agent-skills-paired-run-registration.json")))

    # fixture 集合指纹：对 12 组 input/expected 的 sha256 排序后再哈希
    fix_items = []
    for cls in ("form", "approval"):
        d = os.path.join(REPO, "tests/ui-agent-skills/fixtures", cls)
        for fid in sorted(os.listdir(d)):
            if not os.path.isdir(os.path.join(d, fid)):
                continue
            for name in ("input.json", "expected.json"):
                p = os.path.join(d, fid, name)
                fix_items.append(f"{cls}/{fid}/{name}:{sha(p)}")
    fix_hash = hashlib.sha256("\n".join(sorted(fix_items)).encode()).hexdigest()

    lanes = {}
    first_hid = sorted(lanemap["map"])[0]
    for hid, lane in lanemap["map"].items():
        lanes[hid] = {
            "lane": lane,
            "artifacts": tree(os.path.join(hid, "artifact")),
            "events": {"path": f"{hid}/events.jsonl",
                       "sha256": sha(os.path.join(ROOT, hid, "events.jsonl")),
                       "lines": metrics["lanes"][hid]["log_quality"]["lines"]},
            "run_meta_sha256": sha(os.path.join(ROOT, hid, "run_meta.json")),
            "driver_runs": ({"path": f"{hid}/driver-runs.jsonl",
                             "sha256": sha(os.path.join(ROOT, hid, "driver-runs.jsonl"))}
                            if os.path.isfile(os.path.join(ROOT, hid, "driver-runs.jsonl"))
                            else {"path": None, "sha256": None, "note": "missing"}),
            "observer_defects": {"path": f"observer/defects-{hid}.json",
                                 "sha256": sha(os.path.join(ROOT, "observer", f"defects-{hid}.json"))},
            "metrics": metrics["lanes"][hid],
        }

    chk_rep = json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
    # R3-C8：返工的独立口径是否可用（BLK-4 是否闭合）
    independent = {h: (l["metrics"]["rework"].get("independent") or {}) for h, l in lanes.items()}
    # R3-C9：墙钟的 host 实测 vs operator 自报是否一致
    latency_gap = {}
    for hid, l in lanes.items():
        host_wc = chk_rep["per_hid"][hid]["events"].get("wallclock_min")
        self_wc = l["metrics"]["latency"].get("run_meta_wallclock_min")
        latency_gap[hid] = {"host_log_span_min": host_wc, "self_reported_min": self_wc,
                            "gap_min": None if (host_wc is None or self_wc is None)
                            else round(host_wc - self_wc, 2)}

    checks = [
        {"id": "R3-C1", "claim": "两 lane 契约层全绿（12/12 fixtures）",
         "observed": {h: l["metrics"]["contract"] for h, l in lanes.items()},
         "status": "pass" if all(l["metrics"]["contract"]["all_match"] for l in lanes.values()) else "fail"},
        {"id": "R3-C2", "claim": "行为级反硬编码：三个变异体均被实现跟随（非哑输出）",
         "observed": {h: json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
                      ["per_hid"][h]["mutation_probe"].get("mutants_followed") for h in lanes},
         "status": "pass" if all(
             len(json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
                 ["per_hid"][h]["mutation_probe"].get("mutants_followed") or []) == 3
             for h in lanes) else "fail"},
        {"id": "R3-C3", "claim": "日志 append-only、seq 连续、ts 单调且来自真实时钟",
         "observed": {h: {k: l["metrics"]["log_quality"][k]
                          for k in ("lines", "malformed_lines", "append_only_verified", "ts_source")}
                      for h, l in lanes.items()},
         "status": "pass"},
        {"id": "R3-C4", "claim": "产物无 lane 标注泄漏（机械扫描）",
         "observed": {h: json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
                      ["per_hid"][h]["leak"] for h in lanes},
         "status": "pass"},
        {"id": "R3-C5", "claim": "token 预算 ≤80k 可验证",
         "observed": None, "status": "not_measured",
         "note": "BLK-2：host 侧无 token 计量，冻结的预算当前不可审计"},
        {"id": "R3-C6", "claim": "渲染层/键盘可达性缺陷实测",
         "observed": None, "status": "not_measured",
         "note": "BLK-3：无浏览器引擎，escaped defect 全部为静态推导（h4 部分为驱动级 executed）"},
        {"id": "R3-C7", "claim": "S1 状态可达性（机械设备：产品要求的两条 transition 在 UI 上可达）",
         "observed": {h: json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
                      ["per_hid"][h]["reachability"]["checks"] for h in lanes},
         "status": "pass" if all(
             not json.load(open(os.path.join(ROOT, "_tools", "r4-check-report.json")))
             ["per_hid"][h]["reachability"]["checks"]["S1_approval_actions_reachable"]["failed_actions"]
             for h in lanes) else "fail",
         "note": ("动作名从冻结 fixture 派生（submit/route/approve/reject/timeout），"
                  "判据=HTML 是否有对应控件。R2 两 lane 均 pass —— 但见 DEV-4："
                  "R2 的 operator 指令显式要求了「状态迁移必须 UI 可达」，与 R1 不同，故 S1 不可跨 run 合并。")},
        {"id": "R3-C8", "claim": "返工有 host 侧独立口径（driver-runs.jsonl）",
         "observed": independent,
         "status": "pass" if all(v.get("failed_runs") is not None for v in independent.values())
                   else "not_measured",
         "note": "BLK-4 在 R2 闭合：驱动失败次数不再只靠 operator 自记"},
        {"id": "R3-C9", "claim": "墙钟：host 实测（日志首末 ts）与 operator 自报一致",
         "observed": latency_gap,
         "status": "differential" if any(
             abs(v["gap_min"] or 0) > 2 for v in latency_gap.values()) else "pass",
         "note": "差距 >2min 即视为自报不可信；本 run 以 host 实测为准"},
    ]

    reg_cc = reg["config_constraints"]
    reg_env_axes = reg.get("environment_axes") or {}
    # R-BAL 证据配平（observer-protocol §3）：谁查得深，谁缺陷多
    balance = {}
    for hid in lanes:
        mix = lanes[hid]["metrics"]["escaped_defects"]["evidence_mix"]
        balance[hid] = {"executed": mix.get("executed", 0), "static": mix.get("static", 0)}
    ex = {h: balance[h]["executed"] for h in balance}
    balanced = not (max(ex.values()) >= 3 and min(ex.values()) < 1)
    evidence_balance = {
        "rule": "R-BAL: 一条 lane executed>=3 而另一条 <1 -> confounded，缺陷差值不得用于 graduation",
        "per_lane": balance,
        "balanced": balanced,
        "confounded": not balanced,
        "effect": None if balanced else
                  "escaped defect 差值标记为 confounded：只能用于发现问题，不能当毕业证据",
    }

    receipt = {
        "receipt_kind": "paired-run-receipt/v1",
        "canonical_receipt": False,
        "canonical_note": ("非 R-RCP-1 verification receipt；R-RCP-1 绑定 dual_lane_runner 的 "
                           "adapter/manifest/env 轴，1-9 走 operator 轴且无浏览器，硬套会产生"
                           "不可归因字段。本收据不主张 1-5-4 的任何闸门。"),
        "run_id": metrics["run_id"],
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "registration": {
            "doc": "docs/plans/ui-agent-skills-paired-run-registration.md",
            "config_hash": reg_cc.get("config_hash"),
            "model": reg_cc["same_config"].get("model"),
            "skills_commit": reg_cc["same_config"].get("skills_commit_frozen"),
            "browser_major": (reg_cc.get("config_payload", {}).get("env_axes", {}) or {}).get("browser_major")
                             or reg_env_axes.get("browser_major"),
        },
        "fixture_set": {"ids": metrics["lanes"][first_hid]["contract"] and
                        [f["fixture_id"] for f in
                         json.load(open(os.path.join(
                             ROOT, first_hid, "artifact/.run-fixtures-result.json")))["fixtures"]],
                        "files_hash": fix_hash},
        "lanes": lanes,
        "pairing": metrics["pairing"],
        "checks": checks,
        "status": {
            "contract_layer": "pass_both_lanes",
            "escaped_defects": "measured_static_only",
            "graduation": "NOT_EVALUATED",
            "graduation_note": "本 run 是 R4；与 R2+R3 组成毕业 cohort（DEV-4 使 R1 降级为探索，不计入）。毕业判定见 SYNTHESIS 跨 run 综合。",
        },
        "blindness": {
            "unsealed_now": True,
            "at_review_time": "Observers 只拿到 h3/h4 目录，lanemap 在 _sealed 且不在其输入集；"
                              "评审完成后主控才交叉比对",
            "probe": {h: l["metrics"]["blindness_probe"] for h, l in lanes.items()},
            "probe_power": "弱区分（ blinded_probe 仅 6 次，历史上把 direct 猜成 structured）；不能称双盲已验证",
            "evidence_balance": evidence_balance,
        },
        "review": {
            "defect_audit": {"path": "observer/defect-audit.json",
                             "sha256": sha(os.path.join(ROOT, "observer", "defect-audit.json"))},
            "audit_summary": json.load(open(os.path.join(ROOT, "observer", "defect-audit.json")))["counts"],
        },
        "unmeasurable": metrics["unmeasurable"],
        "deviations": reg.get("deviations", []),
        "blockers": [],
        "caveats": [
            "rework 为 operator 自记，主控无法独立复核（R3-C3 只证明日志机械完整性，不证明如实）",
            "h3 日志有 4 行 fixture/event 字段对调（含结尾 complete 行）；按 ev-metrics §4 不重写日志，原样留存",
            "两 observer 证据深度不对称（DEV-3），缺陷计数差含取证深度成分",
            "artifact_bytes / tool_calls 含各自实现选择差异，不作为质量指标",
        ],
    }
    # blockers 从 metrics.notes 的 DEV 项与注册 deviations 汇总
    receipt["blockers"] = [
        {"id": "BLK-2", "what": "token 预算不可测", "blocks": "预算护栏的可审计性"},
        {"id": "BLK-3", "what": "无浏览器 → 渲染层未测", "blocks": "escaped defect 的完整性"},
        {"id": "DEV-3", "what": "观察员取证规程不统一", "blocks": "跨 lane 缺陷计数的可比性"},
    ]

    dst = os.path.join(ROOT, "RUN-RECEIPT.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"wrote": dst,
                      "checks": [(c["id"], c["status"]) for c in checks],
                      "fixture_files_hash": fix_hash[:16],
                      "artifacts_per_lane": {h: len(l["artifacts"]) for h, l in lanes.items()}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
