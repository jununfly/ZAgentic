#!/usr/bin/env python3
"""1-9 R1-pilot 机械校验器（Q1 日志纯度 / Q2 盲性 / Q3 operator 契约）。

只读 lanemap 的 hid 列表；默认不输出 hid→lane 映射（unseal 前保持盲）。
报告写 stdout，由 shell 重定向落盘（避免 python 直写 workspace 触发沙箱策略）。

用法：
  python3 _tools/pilot_check.py [--unseal]
退出码：0 = 全部硬检查通过；1 = 有硬检查失败。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

NODE = "/Users/bilibili/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # R1-pilot/
REPO = os.path.abspath(os.path.join(ROOT, "../../../../.."))  # R1-pilot/v1/paired-runs/ui-agent-skills/skills-outputs/ZAgentic
CSS_BASELINE_VALUE = re.compile(r":\s*baseline\s*;?\s*$", re.IGNORECASE)
FIXTURE = os.path.join(REPO, "tests/ui-agent-skills/fixtures/form/F-1")
EVENT_ENUM = {"start", "action", "validate", "submit", "rework", "wait", "complete", "abandon"}
LEAK_PATTERNS = [
    r"direct[\s_-]*prompt",
    r"skills[\s_-]*path",
    r"zj-ui-",
    r"\blane\b",
    r"\bbaseline\b",
    r"\bcontrol[\s_-]*group\b",
    r"对照组",
    r"实验组",
]
LEAK_TOKENS = [re.compile(p, re.IGNORECASE) for p in LEAK_PATTERNS]
EXPECTED_FIELDS = ["final_state", "persisted", "error_fields", "submit_blocked"]

hard_fail = []
soft_notes = []


def fail(msg):
    hard_fail.append(msg)


def note(msg):
    soft_notes.append(msg)


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def check_events(hid):
    path = os.path.join(ROOT, hid, "events.jsonl")
    res = {"path": f"{hid}/events.jsonl", "exists": os.path.isfile(path)}
    if not res["exists"]:
        fail(f"{hid}: events.jsonl missing")
        return res
    raw = open(path, "rb").read()
    lines = [ln for ln in raw.decode("utf-8", "replace").split("\n") if ln.strip()]
    res["lines"] = len(lines)
    res["bytes"] = len(raw)
    seqs, tss, events, bad = [], [], [], []
    for i, ln in enumerate(lines, 1):
        try:
            obj = json.loads(ln)
        except Exception as e:
            bad.append(f"line {i}: not JSON ({e})")
            continue
        for k in ("seq", "ts", "fixture", "event", "detail"):
            if k not in obj:
                bad.append(f"line {i}: missing key {k}")
        if obj.get("event") not in EVENT_ENUM:
            bad.append(f"line {i}: event {obj.get('event')!r} not in enum")
        if not isinstance(obj.get("seq"), int):
            bad.append(f"line {i}: seq not int")
        else:
            seqs.append(obj["seq"])
        ts = parse_iso(obj.get("ts", ""))
        if ts is None:
            bad.append(f"line {i}: ts not ISO8601 Z ({obj.get('ts')!r})")
        else:
            tss.append(ts)
        events.append(obj.get("event"))
    res["bad_lines"] = bad[:10]
    res["seq_strictly_increasing"] = all(b - a == 1 for a, b in zip(seqs, seqs[1:])) and (not seqs or seqs[0] == 1)
    res["ts_non_decreasing"] = all(b >= a for a, b in zip(tss, tss[1:]))
    res["event_counts"] = {e: events.count(e) for e in sorted(set(events))}
    res["rework_count"] = events.count("rework")
    res["wait_count"] = events.count("wait")
    # append-only 旁证：mtime 不早于最后一条 ts
    if tss:
        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        res["mtime_after_last_ts"] = mtime >= tss[-1]
        if not res["mtime_after_last_ts"]:
            fail(f"{hid}: events.jsonl mtime {mtime.isoformat()} < last ts {tss[-1].isoformat()} (post-hoc rewrite suspect)")
    # 完成时延：首个 start -> complete
    if "start" in events and "complete" in events:
        t0 = tss[events.index("start")]
        t1 = tss[len(events) - 1 - events[::-1].index("complete")]
        res["completion_latency_s"] = round((t1 - t0).total_seconds(), 1)
    if "complete" not in events:
        res["completed"] = False
        fail(f"{hid}: no complete event")
    else:
        res["completed"] = True
    if bad:
        fail(f"{hid}: {len(bad)} malformed event lines")
    if not res["seq_strictly_increasing"]:
        fail(f"{hid}: seq not strictly increasing from 1 -> {seqs[:8]}")
    if not res["ts_non_decreasing"]:
        fail(f"{hid}: ts not monotonic")
    return res


def check_run_meta(hid):
    path = os.path.join(ROOT, hid, "run_meta.json")
    if not os.path.isfile(path):
        fail(f"{hid}: run_meta.json missing")
        return {}
    try:
        m = json.load(open(path))
    except Exception as e:
        fail(f"{hid}: run_meta.json not JSON ({e})")
        return {}
    for k in ("role", "lane_hidden_id", "config_hash", "budget_used", "operator_id"):
        if k not in m:
            fail(f"{hid}: run_meta missing {k}")
    if m.get("lane_hidden_id") not in (None, hid):
        fail(f"{hid}: run_meta.lane_hidden_id mismatch ({m.get('lane_hidden_id')})")
    for forbidden in ("lane_condition", "mode", "lane"):
        if forbidden in m:
            fail(f"{hid}: run_meta leaks {forbidden} (must live only in _sealed/{hid}.profile.json)")
    b = m.get("budget_used", {}) or {}
    tc = b.get("tool_calls")
    if isinstance(tc, int) and tc > 60:
        fail(f"{hid}: tool_calls {tc} exceeds budget 60")
    if b.get("tokens") is not None:
        note(f"{hid}: tokens reported as {b.get('tokens')} — operator-side token count is not verifiable, treat as unmeasured")
    return m


def check_artifact(hid):
    adir = os.path.join(ROOT, hid, "artifact")
    res = {"dir": f"{hid}/artifact", "exists": os.path.isdir(adir)}
    if not res["exists"]:
        fail(f"{hid}: artifact/ missing")
        return res, None
    files = []
    for dp, _, fns in os.walk(adir):
        for fn in fns:
            files.append(os.path.relpath(os.path.join(dp, fn), adir))
    res["files"] = sorted(files)
    entry = os.path.join(adir, "run-f1.mjs")
    if not os.path.isfile(entry):
        fail(f"{hid}: artifact/run-f1.mjs missing")
        return res, None
    proc = subprocess.run(
        [NODE, "run-f1.mjs",
         os.path.join(FIXTURE, "input.json"), os.path.join(FIXTURE, "expected.json")],
        cwd=adir, capture_output=True, text=True, timeout=120,
    )
    res["run_exit"] = proc.returncode
    out_lines = [l for l in proc.stdout.strip().split("\n") if l.strip()]
    payload = None
    for ln in reversed(out_lines):
        try:
            payload = json.loads(ln)
            break
        except Exception:
            continue
    res["run_stdout_tail"] = (proc.stdout or "")[-400:]
    res["run_stderr_tail"] = (proc.stderr or "")[-400:]
    res["result_payload"] = payload
    if proc.returncode != 0:
        fail(f"{hid}: run-f1.mjs exit {proc.returncode}")
    if not isinstance(payload, dict):
        fail(f"{hid}: run-f1.mjs did not emit a JSON result line")
        return res, None
    exp = json.load(open(os.path.join(FIXTURE, "expected.json")))
    diffs = [f for f in EXPECTED_FIELDS if payload.get(f) != exp.get(f)]
    if diffs:
        fail(f"{hid}: result mismatch vs expected.json on {diffs}")
    res["matches_expected"] = not diffs
    gates = payload.get("human_gates") or []
    res["submit_gate_signed"] = any(g.get("role") == "user" and g.get("signed") is True and g.get("at_step") == 3 for g in gates)
    if not res["submit_gate_signed"]:
        fail(f"{hid}: submit human gate not signed at step 3")
    return res, payload


def check_blindness(hid):
    adir = os.path.join(ROOT, hid, "artifact")
    hits = []
    scanned = 0
    suppressed = []
    if os.path.isdir(adir):
        for dp, _, fns in os.walk(adir):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    lines = open(p, "r", encoding="utf-8", errors="ignore").read().lower().split("\n")
                except Exception:
                    continue
                scanned += 1
                for lineno, txt in enumerate(lines, 1):
                    for tok in LEAK_TOKENS:
                        if not tok.search(txt):
                            continue
                        # CSS 属性值 baseline（align-items/vertical-align 等）不是泄漏，记 suppressed 留痕
                        if tok.pattern == r"\bbaseline\b" and CSS_BASELINE_VALUE.search(txt):
                            suppressed.append({"file": os.path.relpath(p, adir), "line": lineno, "token": tok.pattern, "reason": "css property value"})
                            continue
                        hits.append({"file": os.path.relpath(p, adir), "line": lineno, "token": tok.pattern})
    # checked==0 绝不判 PASS（防假绿）：没扫到文件就是 not_checked
    if scanned == 0:
        status = "not_checked"
        res = {"hid": hid, "scanned_files": 0, "status": status, "leak_hits": [], "clean": None}
        note(f"{hid}: blindness scan skipped (0 artifact files) -> not_checked")
    else:
        res = {"hid": hid, "scanned_files": scanned, "status": "clean" if not hits else "leaked",
               "leak_hits": hits, "suppressed_hits": suppressed, "clean": not hits}
        if hits:
            fail(f"{hid}: artifact contains lane-revealing tokens: {sorted({h['token'] for h in hits})}")
    dpath = os.path.join(ROOT, "observer", f"defects-{hid}.json")
    if os.path.isfile(dpath):
        try:
            d = json.load(open(dpath))
            res["observer_lane_guess"] = d.get("blindness_probe", {}).get("lane_guess")
            res["observer_confidence"] = d.get("blindness_probe", {}).get("confidence")
            res["observer_defect_count"] = len(d.get("defects", []))
        except Exception as e:
            fail(f"{hid}: defects-{hid}.json unreadable ({e})")
    else:
        note(f"{hid}: observer defects not yet present")
    return res


def main():
    unseal = "--unseal" in sys.argv
    lanemap = json.load(open(os.path.join(ROOT, "_sealed/lanemap.json")))
    hids = sorted(lanemap["map"].keys())
    report = {
        "pilot": "R1-pilot",
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hids": hids,
        "fixture": "F-1",
        "node": NODE,
        "per_hid": {},
    }
    for hid in hids:
        report["per_hid"][hid] = {
            "events": check_events(hid),
            "run_meta": check_run_meta(hid),
            "artifact": check_artifact(hid)[0],
            "blindness": check_blindness(hid),
        }
    # 跨 lane 可比性：raw requirement 与 fixture 输入必须同一份
    req = os.path.join(ROOT, "raw-requirement.md")
    report["same_input_requirement_sha256_prefix"] = None
    if os.path.isfile(req):
        import hashlib
        report["same_input_requirement_sha256_prefix"] = hashlib.sha256(open(req, "rb").read()).hexdigest()[:16]
    report["verdict"] = "PASS" if not hard_fail else "FAIL"
    report["hard_failures"] = hard_fail
    report["soft_notes"] = soft_notes
    if unseal:
        report["unsealed_map"] = lanemap["map"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    sys.exit(main())
