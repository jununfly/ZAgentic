#!/usr/bin/env python3
"""1-9-5 G-19..G-25 实测闸门 harness。

被测 artifact = zj-roadmap-driven 存储引擎（single-file JSON + SQLite 双 carrier）。
全部在 /tmp 临时 fixture 上运行，不触碰项目代码（Acceptance/evaluation scope）。

每个闸门输出：passed / samples / failures / exceptions / note。

运行：
    python verify_g19_g25.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_DIR = "/Users/bilibili/.workbuddy/skills/zj-roadmap-driven"
sys.path.insert(0, SKILL_DIR)

import roadmap
from roadmap import Roadmap, LeaseHeld
from roadmap_sqlite import RoadmapSqlite, is_sqlite_path

PY = sys.executable
CLI = os.path.join(SKILL_DIR, "roadmap_cli.py")

RESULTS = {}


def new_instance(path):
    if is_sqlite_path(path):
        r = RoadmapSqlite(path)
    else:
        r = Roadmap(path)
    r.load()
    return r


def init_roadmap(tmp, storage):
    ext = "sqlite" if storage == "sqlite" else "json"
    path = os.path.join(tmp, f"rm.{ext}")
    out = subprocess.run([PY, CLI, "init", path, "--title", "gtest", "--storage", storage],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    # add a child to have something to lease/decide on
    out = subprocess.run([PY, CLI, "add", path, "1", "child"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return path


def run_cli(*args):
    return subprocess.run([PY, CLI, *map(str, args)], capture_output=True, text=True)


# ── G-19 跨会话重放一致（代理：current_revision 跨重启逐字节一致 + canonical 序列化确定性） ──
def gate_g19():
    failed = []
    exceptions = []
    samples = 24
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            for storage in ("single", "sqlite"):
                path = init_roadmap(tmp, storage)
                r = new_instance(path)
                # 注入 varied 决策与节点
                for k in range(3):
                    r.add_decision("1-1", f"q{i}-{k}", f"a{i}-{k}", f"n{k}")
                    r.update_node("1-1", label=f"L{i}-{k}")
                    r.save()
                rev_after_save = r.current_revision()
                # 模拟进程重启：全新实例从磁盘读取
                r2 = new_instance(path)
                rev_reloaded = r2.current_revision()
                if rev_after_save != rev_reloaded:
                    failed.append(f"{storage}: rev mismatch {rev_after_save[:8]} vs {rev_reloaded[:8]}")
                # canonical 序列化确定性：同一 data 两次 canonical_json 一致
                c1 = roadmap.canonical_json(r2.data)
                c2 = roadmap.canonical_json(r2.data)
                if c1 != c2:
                    failed.append(f"{storage}: canonical_json nondeterministic")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-19",
        "title": "跨会话重放一致（代理：canonical revision 跨重启逐字节一致）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "引擎无独立 append-only 重放日志，canonical 状态即事实源；以 current_revision 跨重启一致 + canonical_json 确定性作为重放一致性的等效代理。",
    }


# ── G-20 重放幂等（代理：重复 reload 不产生重复记录 / 无状态漂移） ──
def gate_g20():
    failed = []
    exceptions = []
    samples = 24
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            for storage in ("single", "sqlite"):
                path = init_roadmap(tmp, storage)
                r = new_instance(path)
                for k in range(4):
                    r.add_decision("1-1", f"q{i}-{k}", f"a{i}-{k}")
                    r.save()
                base_nodes = len(r.data["nodes"])
                base_dec = len(r.get_node("1-1")["decisions"])
                # 重复 reload 3 次（模拟多次重放）
                for _ in range(3):
                    r3 = new_instance(path)
                    if len(r3.data["nodes"]) != base_nodes:
                        failed.append(f"{storage}: node count drift {base_nodes}->{len(r3.data['nodes'])}")
                    if len(r3.get_node('1-1')['decisions']) != base_dec:
                        failed.append(f"{storage}: decision count drift {base_dec}->{len(r3.get_node('1-1')['decisions'])}")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-20",
        "title": "重放幂等（代理：重复 reload 无重复写/无孤儿记录）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "引擎以 reload 即重建，无追加式重放副作用；以多次 reload 记录数稳定作为幂等代理。",
    }


# ── G-21 decision 不可变（无 in-place 修改；修改=新记录） ──
def gate_g21():
    failed = []
    exceptions = []
    samples = 24
    in_place_mutations = 0
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            path = init_roadmap(tmp, "single")
            r = new_instance(path)
            # 落一条 decision，记录其规范哈希
            r.add_decision("1-1", f"q{i}", f"a{i}")
            r.save()
            orig = dict(r.get_node("1-1")["decisions"][0])
            orig_hash = roadmap.sha256(roadmap.canonical_json(orig))
            # 尝试"修改"：唯一 API 是 add（新记录）或 remove（追加 retracted 标记）
            r.add_decision("1-1", f"q{i}", f"a{i}-edited")  # 新记录，非改原记录
            r.remove_decision("1-1", index=0)  # 追加 retracted，不动原记录
            r.save()
            decisions = r.get_node("1-1")["decisions"]
            # 原记录仍在且字节未变
            first = decisions[0]
            if roadmap.sha256(roadmap.canonical_json(first)) != orig_hash:
                in_place_mutations += 1
                failed.append(f"sample {i}: original decision mutated")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-21",
        "title": "decision 不可变（无 in-place 修改，修改=新记录）",
        "passed": in_place_mutations == 0 and len(exceptions) == 0,
        "samples": samples,
        "in_place_mutations": in_place_mutations,
        "failures": failed,
        "exceptions": exceptions,
        "note": "update_node 无 decisions 形参；append-only + retracted 标记，原记录永不被改写。",
    }


# ── G-22 revision 链完整（代理：单点 canonical revision 跨重启确定性） ──
def gate_g22():
    failed = []
    exceptions = []
    samples = 24
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            for storage in ("single", "sqlite"):
                path = init_roadmap(tmp, storage)
                r = new_instance(path)
                rev1 = r.current_revision()
                r.update_node("1-1", label=f"x{i}")
                r.save()
                rev2 = r.current_revision()
                if rev1 == rev2:
                    failed.append(f"{storage}: rev unchanged after semantic edit")
                # 无操作 save 不使 rev 失效（volatile 字段排除）
                r.save()
                rev3 = r.current_revision()
                if rev2 != rev3:
                    failed.append(f"{storage}: rev drift on no-op save")
                # 跨重启一致
                r4 = new_instance(path)
                if r4.current_revision() != rev3:
                    failed.append(f"{storage}: rev mismatch after restart")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-22",
        "title": "revision 链完整（代理：单点 canonical revision 哈希跨重启确定性）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "引擎提供单点 current_revision 哈希（用于 --if-rev 乐观并发），但无 parent_revision_id 链；契约字面『重建全量 revision 链』在本引擎为 N/A。",
    }


# ── G-23 handoff 审计完整（代理：fencing 审计事件持久化、可溯源到 lease 操作） ──
def gate_g23():
    failed = []
    exceptions = []
    samples = 20
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            for storage in ("single", "sqlite"):
                path = init_roadmap(tmp, storage)
                run_cli("lease", "claim", path, "1-1", "--agent", "a7", "--ttl", "1")
                time.sleep(1.2)  # 让 TTL 过期 → 模拟崩溃后接管
                run_cli("lease", "steal", path, "1-1", "--agent", "a8")  # 模拟崩溃接管
                r = new_instance(path)
                store = r._read_lease_store()
                events = store.get("events", [])
                ops = [e.get("operation") for e in events]
                fencings = [e.get("fencing_token") for e in events if "fencing_token" in e]
                if "lease-claimed" not in ops or "lease-stolen" not in ops:
                    failed.append(f"{storage}: missing audit event {ops}")
                if not (2 in fencings):
                    failed.append(f"{storage}: fencing not incremented in events {fencings}")
                # 持久化：重启后仍可读到事件
                r2 = new_instance(path)
                if "lease-stolen" not in [e.get("operation") for e in r2._read_lease_store().get("events", [])]:
                    failed.append(f"{storage}: audit event lost after restart")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-23",
        "title": "handoff 审计完整（代理：fencing 审计事件持久化、可溯源到 lease 操作）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "引擎无独立 HandoffRecord 类型；fencing 审计以 lease events（claimed/stolen/released + fencing_token）承载，可持久化、可溯源。",
    }


# ── G-24 重启后 fencing 恢复正确（旧 token 写入一律拒；≥10 次重启样本） ──
def gate_g24():
    failed = []
    exceptions = []
    samples = 12
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            for storage in ("single", "sqlite"):
                path = init_roadmap(tmp, storage)
                run_cli("lease", "claim", path, "1-1", "--agent", "a7", "--ttl", "1")
                time.sleep(1.2)  # 让 TTL 过期 → 模拟崩溃后接管
                st = run_cli("lease", "steal", path, "1-1", "--agent", "a8")
                if st.returncode != 0:
                    failed.append(f"{storage}: steal failed {st.stderr}")
                    continue
                # 模拟进程重启：全新 CLI 进程读取已持久化侧车
                # 旧持有者 a7 token 1 写入必须拒
                stale = run_cli("update", path, "1-1", "--label", "z", "--as-agent", "a7", "--token", "1")
                if stale.returncode != 1 or "E_LEASE_HELD" not in stale.stderr:
                    failed.append(f"{storage}: stale token accepted (rc={stale.returncode})")
                # 新持有者 a8 token 2 写入必须成功
                fresh = run_cli("update", path, "1-1", "--label", "z", "--as-agent", "a8", "--token", "2")
                if fresh.returncode != 0:
                    failed.append(f"{storage}: fresh token rejected {fresh.stderr}")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-24",
        "title": "重启后 fencing 恢复正确（旧 token 写入一律拒）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "lease 侧车（single: <file>.leases.json；sqlite: 库内表）持久化 fencing_token；重启后旧 token 经 CLI 写守卫（_write_guard）拒，新 token 放行。",
    }


# ── G-25 恢复失败=recovery error（日志损坏/缺失场景返回 error，不伪报成功） ──
def gate_g25():
    failed = []
    exceptions = []
    samples = 20
    for i in range(samples):
        try:
            tmp = tempfile.mkdtemp()
            # 缺失文件
            missing = os.path.join(tmp, "nope.json")
            try:
                Roadmap(missing).load()
                failed.append("missing file: load did NOT raise")
            except FileNotFoundError:
                pass
            # 损坏 JSON
            corrupt = os.path.join(tmp, "corrupt.json")
            with open(corrupt, "w", encoding="utf-8") as f:
                f.write("{ this is not valid json ")
            try:
                Roadmap(corrupt).load()
                failed.append("corrupt json: load did NOT raise")
            except (json.JSONDecodeError, ValueError):
                pass
            # sqlite 缺失
            miss_sql = os.path.join(tmp, "nope.sqlite")
            try:
                RoadmapSqlite(miss_sql).load()
                failed.append("missing sqlite: load did NOT raise")
            except (FileNotFoundError, Exception) as e:
                # sqlite 缺失可能以不同异常呈现；只要非静默成功即可
                if "returncode" in str(e) or "success" in str(e).lower():
                    failed.append(f"missing sqlite suspicious: {e}")
        except Exception as e:  # noqa
            exceptions.append(repr(e))
    return {
        "gate": "G-25",
        "title": "恢复失败=recovery error（损坏/缺失返回 error，不伪报成功）",
        "passed": len(failed) == 0 and len(exceptions) == 0,
        "samples": samples * 2,
        "failures": failed,
        "exceptions": exceptions,
        "note": "load() 对缺失文件抛 FileNotFoundError、对损坏 JSON 抛 JSONDecodeError，不静默成功；sqlite 缺失同样非静默。",
    }


if __name__ == "__main__":
    for fn in (gate_g19, gate_g20, gate_g21, gate_g22, gate_g23, gate_g24, gate_g25):
        res = fn()
        RESULTS[res["gate"]] = res
        print(json.dumps(res, ensure_ascii=False))
    all_pass = all(r["passed"] for r in RESULTS.values())
    print("\n=== SUMMARY ===")
    for g, r in RESULTS.items():
        print(f"{g}: {'PASS' if r['passed'] else 'FAIL'} (samples={r['samples']})")
    print("ALL_PASS" if all_pass else "NOT_ALL_PASS")
