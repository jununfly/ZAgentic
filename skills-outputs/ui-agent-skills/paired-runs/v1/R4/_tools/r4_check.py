#!/usr/bin/env python3
"""1-9 R1（契约层）机械校验器。

闭环两个 pilot 阻断项：
  BLK-1 比对白名单：可比较键 = expected.json 键 − {fixture_id, assertions}；
        嵌套对象按墙钟字段 denylist 归一化（savedAt/timestamp/...）。白名单由冻结 fixture 派生，
        不允许 operator 事后挑选。
  BLK-2 host 侧计量：wallclock / audited tool calls / unaudited ratio / output_bytes 全部由 host 计算；
        token 仍不可测，显式记 null（DEV-3 替代口径）。

额外防假绿：
  - fixture 覆盖数必须等于 12（少报即硬失败）
  - driver 回显的 expected 必须与 frozen expected.json 逐字段相同（防篡改/自证）
  - 硬编码哨兵扫描：expected 有、input 没有的字符串值出现在产物源码里 → 记 suspect

用法：python3 _tools/r1_check.py [--unseal]
退出码：0=全部硬检查通过；1=有硬失败。报告写 stdout（shell 重定向落盘）。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # R1/


def _find_repo(start):
    """向上找仓库根；不数层级（pilot V-1 就是数层级数错的）。"""
    cur = start
    for _ in range(12):
        if os.path.isdir(os.path.join(cur, "tests/ui-agent-skills/fixtures")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    raise SystemExit(f"cannot locate repo root from {start}")


REPO = _find_repo(ROOT)
NODE = "/Users/bilibili/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"
FIXROOT = os.path.join(REPO, "tests/ui-agent-skills/fixtures")

EXPECTED_IDS = [f"F-{i}" for i in range(1, 7)] + [f"A-{i}" for i in range(1, 7)]
META_KEYS = {"fixture_id", "assertions"}
CLOCK_KEYS = re.compile(r"^(savedat|saved_at|createdat|created_at|updatedat|updated_at|timestamp|ts|persistedat|persisted_at|at)$", re.I)
EVENT_ENUM = {"start", "action", "validate", "submit", "rework", "wait", "complete", "abandon"}
LEAK_PATTERNS = [r"direct[\s_-]*prompt", r"skills[\s_-]*path", r"zj-ui-", r"\bcontrol[\s_-]*group\b", r"对照组", r"实验组"]
# 注：不用裸 \blane\b —— 领域代码里的 "recovery lane"/"approver lane"/"escalation lane" 是合法词汇
#（pilot V-2 同类误报：CSS baseline）。只有与比较轴连用的具体 token 才算泄漏。
CSS_PROPS = re.compile(r":\s*baseline\s*;?\s*$", re.I)
BUDGET = {"wallclock_min": 45, "audited_calls": 80, "unaudited_ratio": 0.20}

hard, soft = [], []


def fail(m):
    hard.append(m)


def note(m):
    soft.append(m)


def strip_clock(v):
    """归一化：递归去掉墙钟字段（BLK-1）。"""
    if isinstance(v, dict):
        return {k: strip_clock(x) for k, x in v.items() if not CLOCK_KEYS.match(k)}
    if isinstance(v, list):
        return [strip_clock(x) for x in v]
    return v


def load_fixtures():
    fx = {}
    for cls in ("form", "approval"):
        for fid in sorted(os.listdir(os.path.join(FIXROOT, cls))):
            d = os.path.join(FIXROOT, cls, fid)
            if not os.path.isdir(d):
                continue
            inp = json.load(open(os.path.join(d, "input.json")))
            exp = json.load(open(os.path.join(d, "expected.json")))
            fx[fid] = {"class": cls, "input": inp, "expected": exp,
                       "keys": sorted(set(exp) - META_KEYS)}
    return fx


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def dir_mtime_span(path):
    ts = []
    for dp, _, fns in os.walk(path):
        for fn in fns:
            try:
                ts.append(os.path.getmtime(os.path.join(dp, fn)))
            except OSError:
                pass
    return (min(ts), max(ts)) if ts else (None, None)


def check_events(hid):
    path = os.path.join(ROOT, hid, "events.jsonl")
    r = {"exists": os.path.isfile(path)}
    if not r["exists"]:
        fail(f"{hid}: events.jsonl missing")
        return r
    lines = [l for l in open(path, encoding="utf-8").read().split("\n") if l.strip()]
    seqs, tss, bad, audited, unaudited, unaudited_examples = [], [], [], 0, 0, []
    # BLK-4 的副产品：driver-runs.jsonl 让"跑驱动"这类 cmd 步骤从不可核变为可核。
    # 按 ts 精确配对；一个 driver-runs 条目只能抵一条 cmd 事件。
    drv_ts = {}
    drv_p = os.path.join(ROOT, hid, "driver-runs.jsonl")
    if os.path.isfile(drv_p):
        for ln in open(drv_p, encoding="utf-8").read().split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                t = json.loads(ln).get("ts")
            except Exception:
                continue
            drv_ts[t] = drv_ts.get(t, 0) + 1
    cmd_verified, unverifiable, driver_cmd_events = 0, 0, 0
    for i, ln in enumerate(lines, 1):
        try:
            o = json.loads(ln)
        except Exception as e:
            bad.append(f"line {i} not JSON ({e})")
            continue
        for k in ("seq", "ts", "fixture", "event", "detail"):
            if k not in o:
                bad.append(f"line {i} missing {k}")
        if o.get("event") not in EVENT_ENUM:
            bad.append(f"line {i} event {o.get('event')!r} not in enum")
        if isinstance(o.get("seq"), int):
            seqs.append(o["seq"])
        else:
            bad.append(f"line {i} seq not int")
        t = parse_iso(o.get("ts", ""))
        if t:
            tss.append(t)
        else:
            bad.append(f"line {i} ts not ISO Z")
        detail = o.get("detail") or ""
        files = re.findall(r"file=([^\s]+)", detail)
        if files:
            ok = all(os.path.exists(os.path.join(ROOT, hid, f)) for f in files)
            if ok:
                audited += 1
            else:
                unaudited += 1
                unaudited_examples.append({"seq": o.get("seq"), "files": files})
        elif "cmd=" in detail:
            cname = re.search(r"cmd=([^\s]+)", detail).group(1)
            unaudited += 1
            unaudited_examples.append({"seq": o.get("seq"), "cmd": cname})
            is_driver = ("run-fixtures" in cname) or ("fixtures" in cname and "cat" not in cname)
            if is_driver:
                driver_cmd_events += 1
            # 只有"跑驱动"且能在 driver-runs.jsonl 里按 ts 对上的，才算被独立证据核实
            if is_driver and drv_ts.get(o.get("ts"), 0) > 0:
                drv_ts[o["ts"]] -= 1
                cmd_verified += 1
            else:
                unverifiable += 1
    total_steps = audited + unaudited
    # 比例是启发式；真正要防的是"未记录的产物写入"。改成可直接证伪的覆盖断言：
    # artifact/ 下每个文件都必须出现在某条 file= 事件里，否则存在未记录的变更。
    logged_files = set()
    for ln in lines:
        try:
            o = json.loads(ln)
        except Exception:
            continue
        for f in re.findall(r"file=([^\s]+)", o.get("detail") or ""):
            logged_files.add(f.replace("./", "").lstrip("/"))
    unlogged_artifact = []
    adir = os.path.join(ROOT, hid, "artifact")
    if os.path.isdir(adir):
        for dp, _, fns in os.walk(adir):
            for fn in fns:
                if fn.startswith("."):  # 驱动输出，不算人工产物
                    continue
                if fn == "run-fixtures.mjs":  # 冻结的测试驱动（infra，预置，非 operator 产物）
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), os.path.join(ROOT, hid))
                if rel not in logged_files:
                    unlogged_artifact.append(rel)
    r.update({
        "lines": len(lines), "seq_ok": bool(seqs) and seqs[0] == 1 and all(b - a == 1 for a, b in zip(seqs, seqs[1:])),
        "ts_ok": all(b >= a for a, b in zip(tss, tss[1:])),
        "bad_lines": bad[:8], "audited_steps": audited, "unaudited_steps": unaudited,
        "cmd_verified_steps": cmd_verified, "unverifiable_steps": unverifiable,
        "driver_cmd_events": driver_cmd_events,
        "unlogged_artifact_files": unlogged_artifact,
        "artifact_write_fully_logged": not unlogged_artifact,
        "unaudited_ratio": round(unaudited / max(total_steps, 1), 3),
        "unverifiable_ratio": round(unverifiable / max(total_steps, 1), 3),
        "unaudited_examples": unaudited_examples[:6],
        "rework": sum(1 for l in lines if '"event":"rework"' in l or '"event": "rework"' in l),
        "fixtures_covered": sorted({json.loads(l)["fixture"] for l in lines if l.strip() and "fixture" in l}),
        "wallclock_min": round((tss[-1] - tss[0]).total_seconds() / 60, 2) if len(tss) > 1 else None,
    })
    # 字段串位（fixture/event 写反）属于日志纪律缺陷：不改日志（append-only），只计量并标注
    swapped = [b for b in bad if "not in enum" in b and "GLOBAL" in b]
    if swapped:
        r["log_schema_violations"] = len(swapped)
        note(f"{hid}: {len(swapped)} lines have fixture/event swapped (build-phase only; log NOT rewritten per ev-metrics #4)")
    else:
        r["log_schema_violations"] = 0
    other_bad = [b for b in bad if b not in swapped]
    if other_bad:
        fail(f"{hid}: {len(other_bad)} other malformed event lines -> {other_bad[:3]}")
    if not r["seq_ok"]:
        fail(f"{hid}: seq not strictly 1..n")
    if not r["ts_ok"]:
        fail(f"{hid}: ts not monotonic")
    return r


def check_driver(hid, fx):
    adir = os.path.join(ROOT, hid, "artifact")
    r = {"artifact_exists": os.path.isdir(adir)}
    if not r["artifact_exists"]:
        fail(f"{hid}: artifact/ missing")
        return r
    drv = os.path.join(adir, "run-fixtures.mjs")
    if not os.path.isfile(drv):
        fail(f"{hid}: artifact/run-fixtures.mjs missing")
        return r
    proc = subprocess.run([NODE, "run-fixtures.mjs", FIXROOT], cwd=adir,
                          capture_output=True, text=True, timeout=600)
    r["exit"] = proc.returncode
    payload = None
    for ln in reversed([l for l in (proc.stdout or "").split("\n") if l.strip()]):
        try:
            payload = json.loads(ln)
            break
        except Exception:
            continue
    r["stdout_tail"] = (proc.stdout or "")[-300:]
    r["stderr_tail"] = (proc.stderr or "")[-300:]
    if not isinstance(payload, dict) or "fixtures" not in payload:
        fail(f"{hid}: driver did not emit fixtures JSON")
        return r
    got = {f["fixture_id"]: f for f in payload["fixtures"]}
    r["reported_count"] = len(got)
    # 防假绿：覆盖数必须等于 12
    missing = [i for i in EXPECTED_IDS if i not in got]
    extra = [i for i in got if i not in EXPECTED_IDS]
    if missing or extra:
        fail(f"{hid}: fixture coverage wrong (missing={missing} extra={extra})")
    # 防篡改：driver 回显的 expected 必须与冻结文件一致
    tampered = []
    per_fixture, mismatched = {}, []
    for fid in EXPECTED_IDS:
        if fid not in got:
            continue
        f = got[fid]
        frozen = fx[fid]["expected"]
        echoed = f.get("expected")
        sem = fx[fid]["keys"]
        # 防篡改/自证：driver 回显的 expected 必须恰好是语义键集，且逐字段等于冻结值
        if not isinstance(echoed, dict):
            tampered.append(fid)
        else:
            # 元键（fixture_id / assertions）不参与语义比较：原样回显整个
            # expected.json 是更老实的做法，不该判成篡改（R3 h7 即此情况）
            echo_sem = {k: v for k, v in echoed.items() if k not in META_KEYS}
            if sorted(echo_sem) != sorted(sem):
                tampered.append(fid)
            elif any(strip_clock(echo_sem.get(k)) != strip_clock(frozen.get(k)) for k in sem):
                tampered.append(fid)
        actual = f.get("actual") or {}
        diffs = []
        for k in fx[fid]["keys"]:
            a = strip_clock(actual.get(k))
            e = strip_clock(frozen.get(k))
            if a != e:
                diffs.append({"key": k, "expected": e, "actual": a})
        per_fixture[fid] = {"match": not diffs, "diffs": diffs, "keys_compared": fx[fid]["keys"]}
        if diffs:
            mismatched.append(fid)
    if tampered:
        fail(f"{hid}: driver echoed a modified expected.json for {tampered} (tamper/self-certification)")
    r["per_fixture"] = per_fixture
    r["mismatched"] = mismatched
    r["passed"] = [fid for fid in EXPECTED_IDS if fid in per_fixture and per_fixture[fid]["match"]]
    r["all_match_reported"] = payload.get("all_match")
    if mismatched:
        fail(f"{hid}: {len(mismatched)} fixtures mismatch -> {mismatched[:6]}")
    if proc.returncode != 0:
        fail(f"{hid}: driver exit {proc.returncode}")
    if payload.get("all_match") is not True:
        fail(f"{hid}: driver reports all_match != true")
    # 一致性：driver 自报 all_match 但实际有 mismatch 也算假绿
    if payload.get("all_match") is True and mismatched:
        fail(f"{hid}: false green -- driver claims all_match but {len(mismatched)} mismatch")
    return r


def _fixture_action_names(cls):
    """从冻结 fixture 派生该 class 必须支持的动作名（不硬编码、不猜）。"""
    import glob as _g
    names = set()
    for d in _g.glob(os.path.join(FIXROOT, cls, "*")):
        ip = os.path.join(d, "input.json")
        if not os.path.isfile(ip):
            continue
        try:
            inp = json.load(open(ip))
        except Exception:
            continue
        for a in inp.get("actions", []):
            if a.get("action"):
                names.add(a["action"])
    return sorted(names)


def reachability_probe(hid):
    """S1/S6 可达性（observer-protocol §2）的机械化版本。

    fixture 用 initial_state 直接注入状态，会跳过 transition，因此"目标状态在 UI 上
    有没有入口"永远无法被 fixture 覆盖。这里改为对**产品需求里明确要求的 transition**
    做静态可达性检查：状态机定义了该动作，但视图层从不调用它 => 用户在 UI 上走不到。

    只检需求明写的两条，不臆造：
      - approval.route : "提交后进入审批中"
      - form 的恢复动作 : "失败后用户能改完再提交（可恢复）"
    """
    adir = os.path.join(ROOT, hid, "artifact")
    res = {"checks": {}}

    def read(p):
        try:
            return open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            return ""

    # 1) 审批动作可达性（S1）：动作名从**冻结 fixture** 派生，不靠猜名字。
    #    R2 教训：旧 gate 只认 `route(` 字面量，把 h6 的 `id="route-btn"` 判成 fail（假阴性）。
    #    判据改为：动作必须在 HTML 里有对应控件（id / name / 按钮文案含该动作或中文别名）。
    REQUIRED_APPROVAL_ACTIONS = _fixture_action_names("approval")
    ALIAS = {"route": ["路由", "受理", "送审", "派单"], "approve": ["通过", "同意"],
             "reject": ["驳回", "拒绝"], "timeout": ["超时", "升级"], "submit": ["提交"]}
    # 注意：只按 id 前缀匹配会假阴性（R2 h6 的 route-btn 靠别名过关，R3 h8 的 a-route 直接漏）。
    # 改为：把 HTML 里所有 id/name 值抽出来做**子串**匹配，并把按钮/标签可见文案也纳入。
    ap_machine = ""
    for dp, _, fns in os.walk(os.path.join(adir, "src", "approval")):
        for fn in fns:
            if fn.endswith((".mjs", ".js")):
                ap_machine += read(os.path.join(dp, fn))
    ap_html = ""
    for fn in ("approval.html", "index.html"):
        ap_html += read(os.path.join(adir, fn))
    ap_html_l = ap_html.lower()
    # 视图层 = HTML（含内联 <script>）+ UI 模块；状态机定义不计入
    view_src = ap_html
    for dp, _, fns in os.walk(os.path.join(adir, "src")):
        for fn in fns:
            if not fn.endswith((".mjs", ".js")):
                continue
            low = fn.lower()
            if low.startswith("ui") or low.endswith("ui.mjs") or low in ("app.mjs", "main.mjs"):
                view_src += read(os.path.join(dp, fn))
    per_action = {}
    for act in REQUIRED_APPROVAL_ACTIONS:
        machine_has = (f"case '{act}'" in ap_machine or f'case "{act}"' in ap_machine
                       or f"{act}(" in ap_machine or f"{act}:" in ap_machine)
        # 控件证据 A：把 HTML 里所有 id/name 值抽出来做**子串**匹配
        #（前缀匹配会漏掉 a-route / route-btn 这类带前后缀的命名）
        id_vals = re.findall(r'id="([^"]+)"', ap_html_l) + re.findall(r'name="([^"]+)"', ap_html_l)
        id_hit = any(act in v for v in id_vals)
        # 控件证据 B：按钮/标签的可见文案（中文别名，或英文动作词作为独立词）
        texts = re.findall(r"<button[^>]*>(.*?)</button>", ap_html_l, re.S)
        texts += re.findall(r"<label[^>]*>(.*?)</label>", ap_html_l, re.S)
        text_blob = " ".join(re.sub(r"<[^>]+>", " ", t) for t in texts).lower()
        text_hit = any(a.lower() in text_blob for a in ALIAS.get(act, [])) or bool(
            re.search(r"\b" + re.escape(act) + r"\b", text_blob))
        # 证据 B：调用 —— 动作在**视图层**被真正调用（含被别的控件自动带出，如 submit 后自动 route）
        call_hit = (f".{act}(" in view_src or f"case '{act}'" in view_src
                    or f'case "{act}"' in view_src or f"'{act}'" in view_src
                    or f'"{act}"' in view_src)
        per_action[act] = {"machine_defines": machine_has,
                           "control_or_label": id_hit or text_hit,
                           "invoked_from_view": call_hit,
                           "status": ("pass" if (id_hit or text_hit or call_hit) else "fail")}
    failed_actions = [a for a, v in per_action.items() if v["status"] == "fail"]
    res["checks"]["S1_approval_actions_reachable"] = {
        "required_actions": REQUIRED_APPROVAL_ACTIONS,
        "per_action": per_action,
        "failed_actions": failed_actions,
        "status": "pass" if not failed_actions else "fail",
        "meaning": "动作在 UI 上没有控件 => 用户在界面上走不到该状态（fixture 用 initial_state 直接注入，永远测不到）",
    }

    # 2) form 恢复动作：错误态下是否存在一条 UI 出口
    #    注意（R1 教训）：只匹配 id 字符串会假绿 —— h3 的 #recover 存在但藏在
    #    `hidden = state !== 'error'` 后面。因此这里只断言"控件存在"，
    #    并把控制其可见性的表达式原样摘出来交人判，不给 pass/fail。
    form_html = read(os.path.join(adir, "form.html")) or read(os.path.join(adir, "index.html"))
    recover_tokens = ("recover", "retry", "重试", "重新提交", "继续编辑")
    has_recover = any(t in form_html for t in recover_tokens)
    gating = []
    for ln in form_html.split("\n"):
        if ("recover" in ln or "retry" in ln) and (".hidden" in ln or ".disabled" in ln):
            gating.append(ln.strip()[:160])
    res["checks"]["S6_form_recover"] = {
        "view_has_recover_control": has_recover,
        "status": "present" if has_recover else "absent",
        "gating_expression": gating,
        "meaning": ("控件存在不等于可用：需人判 gating_expression 的极性，"
                    "确认它在错误态可见（R1: h3 曾被观察员读反极性误报 high）"),
    }

    fails = [k for k, v in res["checks"].items() if v["status"] in ("fail", "absent")]
    res["failed"] = fails
    for k in fails:
        note(f"{hid}: reachability {k} FAIL -- {res['checks'][k]['meaning']}")
    return res


def check_hardcode(hid, fx):
    """expected 有、input 没有的字符串值 = 哨兵；产物源码里出现即 suspect。"""
    sentinels = set()
    for fid, f in fx.items():
        exp, inp = f["expected"], f["input"]
        inp_strings = set()

        def collect(v):
            if isinstance(v, dict):
                for x in v.values():
                    collect(x)
            elif isinstance(v, list):
                for x in v:
                    collect(x)
            elif isinstance(v, str):
                inp_strings.add(v)
        collect(inp)
        for k, v in exp.items():
            if k in META_KEYS:
                continue
            if isinstance(v, str) and len(v) >= 4 and v not in inp_strings:
                sentinels.add(v)
    hits = []
    adir = os.path.join(ROOT, hid, "artifact")
    for dp, _, fns in os.walk(adir):
        if "/.data" in dp:
            continue
        for fn in fns:
            # 跳过驱动输出/隐藏文件：.run-fixtures-result.json 按契约回显 expected，
            # 扫它必然假阳（pilot V-2 同类误报）。
            if fn.startswith("."):
                continue
            if not fn.endswith((".mjs", ".js", ".html", ".json")):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for s in sentinels:
                if s in txt:
                    hits.append({"file": os.path.relpath(p, adir), "literal": s})
    r = {"sentinels": sorted(sentinels), "hits": hits, "clean": not hits}
    if hits:
        note(f"{hid}: hardcode suspects (expected-only literals in artifact): {sorted({h['literal'] for h in hits})}")
    return r


def mutation_probe(hid):
    """行为级反硬编码：改 input（不改 expected），看 actual 是否跟着变。
    F-5: 422 -> 200 应变成功；F-6: timeout -> 200 应变成功且不再抛 fallback 兜底；
    A-6: 解除自审批 -> 应变 approved。只读 actual，不依赖 expected。"""
    import shutil
    import tempfile
    adir = os.path.join(ROOT, hid, "artifact")
    drv = os.path.join(adir, "run-fixtures.mjs")
    if not os.path.isfile(drv):
        return {"status": "inconclusive", "reason": "no driver"}
    tmp = tempfile.mkdtemp(prefix=f"r1mut-{hid}-")
    # 关键：在产物的**副本**里跑变异，避免污染原件。
    # R1 踩过：探针 cwd 指向 artifact/，驱动把 .run-fixtures-result.json 覆盖成
    # 只有 3 个变异体的结果，导致后续汇总把真实 12/12 读成 fail（仪器改样本）。
    art_copy = os.path.join(tmp, "_artifact")
    try:
        shutil.copytree(adir, art_copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    except Exception as e:
        return {"status": "error", "reason": f"copy artifact failed: {e}"}
    try:
        for cls, fid in (("form", "F-5"), ("form", "F-6"), ("approval", "A-6")):
            src = os.path.join(FIXROOT, cls, fid)
            dst = os.path.join(tmp, cls, fid)
            shutil.copytree(src, dst)
            inp_path = os.path.join(dst, "input.json")
            inp = json.load(open(inp_path))
            if fid == "F-5":
                for a in inp["actions"]:
                    if a.get("response_code") == 422:
                        a["response_code"] = 200
                        a.pop("error", None)
            elif fid == "F-6":
                # 探针目的：F-6 的 fallback=stable_path 是"错误分支的领域常量"还是"无脑输出"。
                # 把超时改成成功，正确实现的 fallback 应消失。
                for a in inp["actions"]:
                    if a.get("error") == "timeout":
                        a["response_code"] = 200
                        a.pop("error", None)
                        a["to"] = "success"
            else:
                # A-6 原意 = 自审批被拒。突变必须同时解除"自审批"（applicant==approver）
                # 并换成语义角色 approver；否则 role 改了但 request.approver 仍是 user-006，
                # 实现照旧拒绝 —— 那是探针无效，不是实现硬编码。
                inp["approver"] = "approver-001"
                inp["actions"][0]["role"] = "approver"
                inp["actions"][0].pop("outcome", None)
            with open(inp_path, "w", encoding="utf-8") as fh:
                json.dump(inp, fh, ensure_ascii=False, indent=2)
        proc = subprocess.run([NODE, "run-fixtures.mjs", tmp], cwd=art_copy,
                              capture_output=True, text=True, timeout=600)
        payload = None
        for ln in reversed([l for l in (proc.stdout or "").split("\n") if l.strip()]):
            try:
                payload = json.loads(ln)
                break
            except Exception:
                continue
        if not isinstance(payload, dict) or "fixtures" not in payload:
            return {"status": "inconclusive", "reason": "driver emitted no JSON on mutant fixture set",
                    "exit": proc.returncode, "stderr": (proc.stderr or "")[-200:]}
        got = {f["fixture_id"]: (f.get("actual") or {}) for f in payload["fixtures"]}
        res = {"status": "ran", "mutants": {}}
        # F-5: 原 expected = error/false；突变后正确实现应 success/true
        f5 = got.get("F-5")
        if f5 is None:
            res["status"] = "inconclusive"
            res["reason"] = "driver skipped mutant F-5"
        else:
            res["mutants"]["F-5"] = {"final_state": f5.get("final_state"), "persisted": f5.get("persisted"),
                                     "followed_input": f5.get("final_state") == "success" and f5.get("persisted") is True}
        f6 = got.get("F-6")
        if f6 is None:
            res["status"] = "inconclusive"
            res["reason"] = "driver skipped mutant F-6"
        else:
            res["mutants"]["F-6"] = {
                "final_state": f6.get("final_state"), "persisted": f6.get("persisted"),
                "fallback": f6.get("fallback"),
                "followed_input": (f6.get("final_state") == "success"
                                   and f6.get("persisted") is True
                                   and not f6.get("fallback")),
            }
        a6 = got.get("A-6")
        if a6 is None:
            res["status"] = "inconclusive"
            res["reason"] = "driver skipped mutant A-6"
        else:
            res["mutants"]["A-6"] = {"final_state": a6.get("final_state"), "persisted": a6.get("persisted"),
                                     "followed_input": a6.get("final_state") == "approved" and a6.get("persisted") is True}
        followed = [k for k, v in res["mutants"].items() if v.get("followed_input")]
        res["mutants_followed"] = followed
        n = len(res["mutants"])
        if res["status"] == "ran" and not followed:
            fail(f"{hid}: mutation probe -- all mutants ignored input change (hardcoded outputs suspected)")
        elif res["status"] == "ran" and len(followed) < n:
            note(f"{hid}: mutation probe partial -- followed {followed} of {sorted(res['mutants'])}")
        return res
    except Exception as e:
        return {"status": "error", "reason": str(e)[:200]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_leak(hid):
    adir = os.path.join(ROOT, hid, "artifact")
    hits, scanned, suppressed = [], 0, []
    for dp, _, fns in os.walk(adir):
        if "/.data" in dp:
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                lines = open(p, encoding="utf-8", errors="ignore").read().lower().split("\n")
            except Exception:
                continue
            scanned += 1
            for i, txt in enumerate(lines, 1):
                for pat in LEAK_PATTERNS:
                    if re.search(pat, txt):
                        hits.append({"file": os.path.relpath(p, adir), "line": i, "pattern": pat})
                if re.search(r"\bbaseline\b", txt) and CSS_PROPS.search(txt):
                    suppressed.append({"file": os.path.relpath(p, adir), "line": i})
    if scanned == 0:
        note(f"{hid}: leak scan not_checkable (0 files)")
        return {"status": "not_checked", "scanned": 0}
    if hits:
        fail(f"{hid}: artifact leaks comparison tokens {sorted({h['pattern'] for h in hits})}")
    return {"status": "clean" if not hits else "leaked", "scanned": scanned,
            "hits": hits, "suppressed_css": len(suppressed)}


def check_budget(hid, ev, adir):
    span = dir_mtime_span(adir) if os.path.isdir(adir) else (None, None)
    out_bytes = 0
    for dp, _, fns in os.walk(adir) if os.path.isdir(adir) else []:
        for fn in fns:
            try:
                out_bytes += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    r = {"wallclock_min": ev.get("wallclock_min"), "audited_steps": ev.get("audited_steps"),
         "unaudited_steps": ev.get("unaudited_steps"), "unaudited_ratio": ev.get("unaudited_ratio"),
         "cmd_verified_steps": ev.get("cmd_verified_steps"),
         "unverifiable_steps": ev.get("unverifiable_steps"),
         "unverifiable_ratio": ev.get("unverifiable_ratio"),
         "output_bytes": out_bytes, "dir_mtime_span_s": None,
         "within": {}}
    if span[0] and span[1]:
        r["dir_mtime_span_s"] = round(span[1] - span[0], 1)
    wc = ev.get("wallclock_min")
    r["within"]["wallclock"] = wc is not None and wc <= BUDGET["wallclock_min"]
    r["within"]["audited_calls"] = (ev.get("audited_steps") or 0) <= BUDGET["audited_calls"]
    # 口径：先按"能被独立证据核实的步骤"算（file= 可解析 + 驱动执行与 driver-runs 对上），
    # 剩下的才是不可核步骤。旧的 unaudited_ratio 保留在报告里做对照，不用于判负。
    # 硬门：产物写入必须全部被 file= 记录（比比例更可直接证伪）
    r["within"]["artifact_writes_logged"] = ev.get("artifact_write_fully_logged") is True
    # 比例退为观测指标：>20% 记 note，不判负（其风险已被上面的覆盖断言接管）
    r["within"]["unverifiable_ratio"] = (ev.get("unverifiable_ratio") or 0) <= BUDGET["unaudited_ratio"]
    if r["within"]["wallclock"] is False:
        fail(f"{hid}: wallclock {wc} min > {BUDGET['wallclock_min']}")
    if r["within"]["audited_calls"] is False:
        fail(f"{hid}: audited steps {ev.get('audited_steps')} > {BUDGET['audited_calls']}")
    if r["within"]["unverifiable_ratio"] is False:
        note(f"{hid}: unverifiable ratio {ev.get('unverifiable_ratio')} > {BUDGET['unaudited_ratio']} "
             f"(非判负：其风险由 artifact_writes_logged 覆盖断言接管)")
    if r["within"]["artifact_writes_logged"] is False:
        fail(f"{hid}: {len(ev.get('unlogged_artifact_files') or [])} artifact files were never logged with file= "
             f"-> 存在未记录的变更: {(ev.get('unlogged_artifact_files') or [])[:6]}")
    r["tokens"] = None
    r["tokens_note"] = "DEV-3: tokens not measurable; output_bytes is the reported substitute (no threshold)"
    return r


def check_driver_runs(hid):
    """BLK-4 修复：从 append-only driver-runs.jsonl 独立复核返工。

    events.jsonl 里的 `rework` 是 operator 自记（可漏可多）；driver-runs.jsonl 是
    host 侧可查的驱动执行历史（每次退出码 + 失败断言），两者交叉验证。
    任一不存在 -> 该口径标 not_measured，不静默给 0。
    """
    p = os.path.join(ROOT, hid, "driver-runs.jsonl")
    res = {"path": f"{hid}/driver-runs.jsonl"}
    if not os.path.isfile(p):
        res.update({"status": "missing", "failed_runs": None, "total_runs": None})
        note(f"{hid}: driver-runs.jsonl missing -> 独立返工口径 not_measured")
        return res
    rows, bad = [], []
    for i, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            bad.append({"line": i, "error": str(e)[:80]})
    seqs = [r.get("seq") for r in rows]
    seq_ok = bool(seqs) and seqs[0] == 1 and all(b - a == 1 for a, b in zip(seqs, seqs[1:]))
    failed = sum(1 for r in rows if r.get("exit") != 0 or r.get("all_match") is not True)
    res.update({
        "status": "ok", "total_runs": len(rows), "failed_runs": failed,
        "seq_ok": seq_ok, "malformed": bad[:5],
        "runs": [{"seq": r.get("seq"), "exit": r.get("exit"),
                  "all_match": r.get("all_match"), "mismatch_count": r.get("mismatch_count")}
                 for r in rows],
        "meaning": "failed_runs = host 侧可查的'驱动失败次数'，独立于 operator 自记 rework",
    })
    if bad:
        fail(f"{hid}: driver-runs.jsonl has {len(bad)} malformed lines")
    if not seq_ok:
        note(f"{hid}: driver-runs.jsonl seq not strictly increasing (append-only 存疑)")
    return res


def check_requirement_identity():
    """同 case 不变量：R2 的裸需求必须与 R1 逐字节相同。"""
    import hashlib
    r1 = os.path.join(os.path.dirname(ROOT), "R1", "raw-requirement.md")
    r2 = os.path.join(ROOT, "raw-requirement.md")
    if not os.path.isfile(r1):
        return {"status": "not_checked", "reason": "R1 requirement missing"}
    h1 = hashlib.sha256(open(r1, "rb").read()).hexdigest()
    h2 = hashlib.sha256(open(r2, "rb").read()).hexdigest()
    res = {"r1_sha256": h1, "r2_sha256": h2, "identical": h1 == h2}
    if h1 != h2:
        fail("raw-requirement.md differs between R1 and R2 -> 同 case 约束被破坏")
    return res


def check_run_meta(hid):
    p = os.path.join(ROOT, hid, "run_meta.json")
    if not os.path.isfile(p):
        fail(f"{hid}: run_meta.json missing")
        return {}
    m = json.load(open(p))
    for k in ("role", "lane_hidden_id", "config_hash", "budget_used", "operator_id"):
        if k not in m:
            fail(f"{hid}: run_meta missing {k}")
    for bad in ("lane_condition", "mode", "lane"):
        if bad in m:
            fail(f"{hid}: run_meta leaks {bad}")
    if m.get("lane_hidden_id") not in (None, hid):
        fail(f"{hid}: run_meta lane_hidden_id mismatch")
    return m


def main():
    unseal = "--unseal" in sys.argv
    fx = load_fixtures()
    if len(fx) != 12:
        fail(f"fixture set is {len(fx)}, expected 12")
    lanemap = json.load(open(os.path.join(ROOT, "_sealed/lanemap.json")))
    hids = sorted(lanemap["map"])
    rep = {"run": "R3-contract-layer", "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "fixtures": EXPECTED_IDS, "budget_rules": BUDGET,
           "case_invariance": check_requirement_identity(), "per_hid": {}}
    for hid in hids:
        ev = check_events(hid)
        drv = check_driver(hid, fx)
        rep["per_hid"][hid] = {
            "events": ev,
            "driver": {k: v for k, v in drv.items() if k != "per_fixture"},
            "per_fixture_match": {fid: v["match"] for fid, v in (drv.get("per_fixture") or {}).items()},
            "hardcode": check_hardcode(hid, fx),
            "reachability": reachability_probe(hid),
            "driver_runs": check_driver_runs(hid),
            "mutation_probe": mutation_probe(hid),
            "leak": check_leak(hid),
            "budget": check_budget(hid, ev, os.path.join(ROOT, hid, "artifact")),
            "run_meta": check_run_meta(hid),
        }
    rep["verdict"] = "PASS" if not hard else "FAIL"
    rep["hard_failures"] = hard
    rep["soft_notes"] = soft
    if unseal:
        rep["unsealed_map"] = lanemap["map"]
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
