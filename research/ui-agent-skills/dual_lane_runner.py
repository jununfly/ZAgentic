#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R-HAR-1 — UI Agent Skills 确定性双 lane 验证 runner（1-5-2 交付物）

职责（来自 ui-agent-skills-roadmap.json 节点 1-5-2 退出判据）：
  实现 baseline 与 degraded 双 lane、固定 browser/font/network/clock/seed 并可复跑。

设计原则：
- 纯 stdlib，可在「无网络 / 无凭据 / 无外部设计工具」下运行（golden-fixtures-spec §8 fail-closed）。
- 确定性：固定虚拟时钟、固定 RNG seed、network=replay、固定字体策略、config_hash 冻结断言配置。
- 双 lane：
    * baseline  —— 全维度硬门禁；需要浏览器/adapter 才能执行真实 cell 断言。
    * degraded  —— adapter-off / 离线恢复路径；只走不依赖远端 adapter 的 cell。
- 不伪造通过：未接 adapter/浏览器时，需要它们的 cell 如实标记为
  NOT_EXECUTED / DEGRADED_SKIP，绝不输出假 pass（fail-closed）。
- 可复跑：init / fingerprint 幂等，同输入两次运行得到相同 manifest_hash / env_hash / matrix_key。

注意（已知延迟，非静默接受偏差，见节点 1-5-2 decide）：
- browser_major 不在本仓库 Wave 0 harness 内捕获（无内置浏览器引擎），
  延迟到 1-7-3（Storybook active adapter）。env_hash 当前基于 6 个 concrete 轴
  + browser_major=PENDING@1-7-3 占位；1-7-3 回填真实 major 时按 revalidation 规则触发全量重验。
- 真实 fixture 数据文件（F-1..GF-11）由 1-6/1-7 落地；本 runner 仅就 fixture-manifest
  的元数据记录计算 manifest_hash，数据落地后须重算。

CLI：
  dual_lane_runner.py init [--plans DIR]            # 幂等建立 fixture 目录骨架 + 计算 manifest_hash
  dual_lane_runner.py fingerprint [--plans DIR]     # 捕获 env 轴 + config_hash + env_hash + matrix_key（print-only）
  dual_lane_runner.py plan [--lane baseline|degraded] [--plans DIR]
  dual_lane_runner.py run --lane <baseline|degraded> [--plans DIR] [--observations DIR]
  dual_lane_runner.py selfcheck [--plans DIR]       # 复跑幂等自检
  dual_lane_runner.py demo                           # 确定性控制自检（虚拟时钟 + seed）

本会话执行方式：以 --print-only（默认）把计算结果输出到 stdout，由专用工具写回
docs/plans/*.json，规避工作区写沙箱；runner 自身仍含 write-back 逻辑，未来环境可直接落盘。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hard_gates as hg  # noqa: E402  R-HAR-2（1-5-3 硬门禁）

# --------------------------------------------------------------------------- #
# 固定确定性常量（1-5-2 退出判据：固定 browser/font/network/clock/seed）
# --------------------------------------------------------------------------- #

# 固定 RNG seed —— 保证截图/布局随机性可复现
SEED = 20261020

# 固定虚拟时钟 epoch —— 无墙钟依赖（clock_source = fixed virtual time）
VIRTUAL_EPOCH_ISO = "2026-01-01T00:00:00+00:00"

# 字体策略（env-fingerprint §1，2026-10-20 定值，SIL OFL 1.1，@fontsource 自托管锁版本）
FONT_AXIS_VALUE = "noto-sans-sc+inter+jetbrains-mono(conditional)"

# 网络模式（env-fingerprint §1，R-MOCK-1/R-RISK-5）
NETWORK_MODE = "replay"

# 浏览器主版本：本仓库 Wave 0 无内置浏览器引擎，延迟到 1-7-3 捕获真实 major
BROWSER_MAJOR = "PENDING@1-7-3"

# Node 运行时约束（env-fingerprint §1，R-ENV-1）：目标 EV 运行时（Next.js 14）
NODE_VERSION = ">=18.17"

# 固定断言配置（env-fingerprint §1 config_hash 来源）
# v0.2（1-5-3）：viewport 集对齐 1-3 capability manifest（S8 FF-BRK 必测 390/768/1440），
# 阈值并入 hard_gates.GATE_THRESHOLDS（单一事实源），config_hash 随之重算。
VERIFICATION_CONFIG = {
    "version": "0.2",
    "viewports": hg.REQUIRED_VIEWPORTS,
    "thresholds": dict(hg.GATE_THRESHOLDS),
    "oracles": [
        "static-assert",     # dom_aria / 结构
        "interaction-sim",   # focus
        "pixel-calc",        # contrast / overflow / responsive / motion
        "semantic-hash",     # round_trip
        "schema-assert",     # migration
        "recovery-assert",   # offline_recovery
    ],
}

# 冻结验证维度（verification-matrix §1）
DIMENSIONS = [
    "dom_aria", "focus", "contrast", "overflow", "responsive", "motion",
    "state", "round_trip", "migration", "offline_recovery",
]

# 冻结 cell 门禁（verification-matrix §2）：dimension -> {form, adapter, contract}
# A=适用并硬门禁, W=适用仅 warning, -=不适用
CELL_GATE = {
    "dom_aria":          {"form": "A", "adapter": "A", "contract": "A"},
    "focus":             {"form": "A", "adapter": "A", "contract": "A"},
    "contrast":          {"form": "A", "adapter": "A", "contract": "-"},
    "overflow":          {"form": "A", "adapter": "A", "contract": "-"},
    "responsive":        {"form": "A", "adapter": "A", "contract": "-"},
    "motion":            {"form": "A", "adapter": "A", "contract": "-"},
    "state":             {"form": "A", "adapter": "A", "contract": "A"},
    "round_trip":        {"form": "-", "adapter": "A", "contract": "A"},
    "migration":         {"form": "-", "adapter": "-", "contract": "A"},
    "offline_recovery":  {"form": "-", "adapter": "-", "contract": "A"},
}

# 门禁是否可执行由「有没有 observation bundle」决定（1-5-3）：不再维护维度级 adapter 依赖表，
# 因为同一维度在不同 class/fixture 下的证据来源不同；缺证据一律 HUMAN_REVIEW_REQUIRED。


# --------------------------------------------------------------------------- #
# 确定性基元
# --------------------------------------------------------------------------- #

class VirtualClock:
    """固定虚拟时钟：无墙钟依赖，单调可控。"""

    def __init__(self, epoch_iso: str = VIRTUAL_EPOCH_ISO):
        self.epoch = datetime.fromisoformat(epoch_iso)
        self._ticks = 0

    def now_iso(self) -> str:
        return (self.epoch.replace(tzinfo=timezone.utc)).isoformat()

    def tick(self, ms: int = 1000) -> str:
        self._ticks += ms
        return self.now_iso()

    def reset(self) -> None:
        self._ticks = 0


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj) -> str:
    """稳定序列化：sort_keys + 固定分隔，保证跨进程/跨时间一致。"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def config_hash() -> str:
    return sha256_text(canonical_json(VERIFICATION_CONFIG))


def make_rng(seed: int = SEED):
    return random.Random(seed)


# --------------------------------------------------------------------------- #
# 路径与加载
# --------------------------------------------------------------------------- #

def default_plans_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # research/ui-agent-skills -> repo/docs/plans
    repo = os.path.dirname(os.path.dirname(here))
    return os.path.join(repo, "docs", "plans")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# --------------------------------------------------------------------------- #
# fixture-manifest：manifest_hash
# --------------------------------------------------------------------------- #

STABLE_FIELDS = ["id", "class", "source", "trigger", "expected", "landed_at", "status"]


def compute_manifest_hash(fixture_doc: dict) -> str:
    rows = []
    for fx in sorted(fixture_doc.get("fixtures", []), key=lambda f: f["id"]):
        rows.append({k: fx.get(k) for k in STABLE_FIELDS})
    return sha256_text(canonical_json(rows))


def init_fixtures(plans_dir: str, write: bool = False) -> dict:
    """幂等建立 fixture 目录骨架 + 计算 manifest_hash。

    真实 fixture 数据由 1-6/1-7 落地；此处仅就 manifest 元数据记录计算 hash。
    """
    manifest_path = os.path.join(plans_dir, "ui-agent-skills-fixture-manifest.json")
    doc = load_json(manifest_path)
    mh = compute_manifest_hash(doc)
    doc["manifest_hash"] = mh

    root = doc.get("storage_root", "tests/ui-agent-skills/fixtures/")
    # 建立 landed_at 目录骨架（幂等）
    created = []
    for fx in doc.get("fixtures", []):
        landed = fx.get("landed_at")
        if landed:
            d = os.path.join(os.path.dirname(plans_dir), "..", landed) \
                if not os.path.isabs(landed) else landed
            try:
                os.makedirs(d, exist_ok=True)
                created.append(d)
            except OSError:
                # 工作区写沙箱可能拒绝；骨架非阻断，数据落地阶段再建
                pass

    if write:
        save_json(manifest_path, doc)
    return {"manifest_hash": mh, "manifest_path": manifest_path,
            "dirs_touched": len(created)}


# --------------------------------------------------------------------------- #
# env-fingerprint：env_hash + matrix_key
# --------------------------------------------------------------------------- #

def build_axes(env_doc: dict, cfg_hash: str) -> dict:
    """回填确定性可固定的轴；保留 PENDING 占位（browser_major 延迟到 1-7-3）。"""
    axes = env_doc.get("axes", {})
    fixed = {
        "browser_major": BROWSER_MAJOR,
        "node_version": NODE_VERSION,
        "font": FONT_AXIS_VALUE,
        "network_mode": NETWORK_MODE,
        "clock_source": f"fixed-virtual-time@{VIRTUAL_EPOCH_ISO}",
        "seed": str(SEED),
        "config_hash": cfg_hash,
    }
    out = {}
    for k, v in fixed.items():
        policy = axes.get(k, {}).get("policy", "")
        source = axes.get(k, {}).get("source", "")
        out[k] = {"value": v, "policy": policy, "source": source}
    return out


def env_hash_from_axes(axes: dict) -> str:
    # 与 env-fingerprint §2 固定顺序一致
    order = ["browser_major", "node_version", "font",
             "network_mode", "clock_source", "seed", "config_hash"]
    joined = "|".join(str(axes[k]["value"]) for k in order)
    return sha256_text(joined)


def matrix_key(manifest_hash: str, env_h: str) -> str:
    dims_part = ",".join(sorted(DIMENSIONS))
    gate_part = canonical_json(
        {d: {c: CELL_GATE[d][c] for c in ("form", "adapter", "contract")}
         for d in DIMENSIONS}
    )
    blob = manifest_hash + env_h + dims_part + gate_part
    return sha256_text(blob)


def fingerprint(plans_dir: str, write: bool = False) -> dict:
    env_path = os.path.join(plans_dir, "ui-agent-skills-env-fingerprint.json")
    env_doc = load_json(env_path)
    cfg_h = config_hash()
    axes = build_axes(env_doc, cfg_h)
    eh = env_hash_from_axes(axes)

    manifest_path = os.path.join(plans_dir, "ui-agent-skills-fixture-manifest.json")
    mh = compute_manifest_hash(load_json(manifest_path))
    mk = matrix_key(mh, eh)

    env_doc["axes"] = axes
    env_doc["env_hash"] = eh
    env_doc["matrix_key"] = mk
    env_doc["config_hash"] = cfg_h
    env_doc["note"] = (
        "机器可读环境指纹（config v" + VERIFICATION_CONFIG["version"] + "）。确定性轴"
        "（network_mode/clock_source/seed/config_hash/font/node_version）由 R-HAR-1 捕获并冻结；"
        "1-5-3 将 viewport 集对齐 capability manifest（390/768/1440）并重算 config_hash/env_hash/"
        "matrix_key。browser_major=" + BROWSER_MAJOR + "（本仓库 Wave 0 无内置浏览器引擎，"
        "延迟到 1-7-3 捕获真实 major，届时按 revalidation 规则触发全量重验）。"
    )

    if write:
        save_json(env_path, env_doc)
    return {"env_hash": eh, "matrix_key": mk, "config_hash": cfg_h,
            "env_path": env_path, "axes": axes}


# --------------------------------------------------------------------------- #
# plan / run：双 lane 调度
# --------------------------------------------------------------------------- #

def plan_cells(lane: str) -> list:
    cells = []
    for dim in DIMENSIONS:
        gate = CELL_GATE[dim]
        for cls in ("form", "adapter", "contract"):
            mark = gate[cls]
            if mark == "-":
                continue
            cells.append({"dimension": dim, "class": cls, "gate": mark, "lane": lane})
    return cells


def run_lane(lane: str, plans_dir: str, observations_dir: str = None) -> dict:
    """执行一条 lane。

    baseline：对存在 observation bundle 的 fixture 逐 viewport 跑 7 类硬门禁；
    缺 bundle 的 fixture 记 HG-EVID-02（HUMAN_REVIEW_REQUIRED），绝不伪造通过。
    degraded：adapter-off 路径，全部 DEGRADED_SKIP（离线恢复归 1-6/1-9）。
    """
    fp = fingerprint(plans_dir, write=False)
    manifest = load_json(os.path.join(plans_dir, "ui-agent-skills-fixture-manifest.json"))
    fixtures = manifest.get("fixtures", [])
    mh = compute_manifest_hash(manifest)
    clock = VirtualClock()
    rng = make_rng()
    obs = hg.load_bundles(observations_dir) if observations_dir else {}
    thresholds = VERIFICATION_CONFIG["thresholds"]

    cells = plan_cells(lane)
    results = []
    for c in cells:
        dim, cls = c["dimension"], c["class"]
        detail = {"gate": dim, "fixtures_seen": 0, "bundles": 0,
                  "missing_fixtures": [], "findings": []}
        reason = ""
        if lane == "degraded":
            status = "DEGRADED_SKIP"      # 离线恢复路径需 1-6 engine；adapter 相关一律跳过
            reason = "degraded lane 不执行视觉/adapter 门禁，离线恢复归 1-6/1-9"
        elif dim not in hg.GATES:
            status = "NOT_EXECUTED"
            reason = "门禁不在 1-5-3 口径（round_trip/migration/offline_recovery 属 1-6/1-9）"
        else:
            class_fixtures = [f for f in fixtures if f.get("class") == cls]
            gate_results = []
            missing = []
            for fx in class_fixtures:
                bundles = obs.get(fx.get("id"), {})
                if not bundles:
                    missing.append(fx.get("id"))
                    continue
                detail["fixtures_seen"] += 1
                detail["bundles"] += len(bundles)
                if dim in hg.CROSS_VIEWPORT_GATES:
                    gate_results.append(hg.run_gate(dim, bundles, thresholds, fx))
                else:
                    for vp in sorted(bundles):
                        gate_results.append(hg.run_gate(dim, bundles[vp], thresholds, fx))
            if not gate_results:
                status = "NOT_EXECUTED"
                reason = "无 observation bundle（%s 类 %d 个 fixture 全缺）" % (cls, len(missing))
            else:
                if missing:
                    gate_results.append(hg.missing_fixtures_result(dim, missing, cls))
                detail["missing_fixtures"] = missing
                detail["findings"] = [f for r in gate_results for f in r["findings"]]
                status = hg.aggregate(gate_results)
                if missing:
                    reason = "部分 fixture 缺 observation（%d/%d），证据不全不判 PASS" % (
                        len(missing), len(class_fixtures))
        results.append({**c, "status": status, "reason": reason, "observed": detail})

    statuses = [r["status"] for r in results]
    executed_n = len([s for s in statuses if s not in ("NOT_EXECUTED", "DEGRADED_SKIP")])
    skipped_n = len(statuses) - executed_n

    receipt = {
        "runner": "R-HAR-1+R-HAR-2",
        "lane": lane,
        "run_id": sha256_text(f"{lane}|{fp['env_hash']}|{clock.now_iso()}|{rng.random()}")[:16],
        "clock_source": clock.now_iso(),
        "seed": SEED,
        "network_mode": NETWORK_MODE,
        "manifest_hash": mh,
        "env_hash": fp["env_hash"],
        "matrix_key": fp["matrix_key"],
        "config_version": VERIFICATION_CONFIG["version"],
        "config_hash": fp["config_hash"],
        "observations_dir": observations_dir,
        "overall": _overall_status(statuses),
        "executed": executed_n,
        "skipped": skipped_n,
        "cells": results,
        "note": ("fail-closed：仅对存在 observation bundle 的 cell 执行硬门禁；缺证据记 "
                 "HUMAN_REVIEW_REQUIRED，绝不以 NOT_EXECUTED 或部分覆盖冒充 PASS。"
                 "本 receipt 仍为结构占位，完整字段由 1-5-4 定稿。"),
    }
    return receipt


def _overall_status(statuses):
    """lane 聚合：FAIL > HUMAN_REVIEW_REQUIRED > QUARANTINED > PARTIAL/WARNING > PASS。"""
    if "FAIL" in statuses:
        return "FAIL"
    if "HUMAN_REVIEW_REQUIRED" in statuses:
        return "HUMAN_REVIEW_REQUIRED"
    if "QUARANTINED" in statuses:
        return "QUARANTINED"
    executed = [s for s in statuses if s not in ("NOT_EXECUTED", "DEGRADED_SKIP")]
    if not executed:
        return "BLOCKED"
    if len(executed) < len(statuses):
        return "PARTIAL"
    if "WARNING" in statuses:
        return "WARNING"
    return "PASS"


# --------------------------------------------------------------------------- #
# selfcheck / demo
# --------------------------------------------------------------------------- #

def selfcheck(plans_dir: str) -> dict:
    a = init_fixtures(plans_dir, write=False)
    b = init_fixtures(plans_dir, write=False)
    fa = fingerprint(plans_dir, write=False)
    fb = fingerprint(plans_dir, write=False)
    ok = (a["manifest_hash"] == b["manifest_hash"]
          and fa["env_hash"] == fb["env_hash"]
          and fa["matrix_key"] == fb["matrix_key"])
    return {"rerun_idempotent": ok,
            "manifest_hash": a["manifest_hash"],
            "env_hash": fa["env_hash"],
            "matrix_key": fa["matrix_key"]}


def demo() -> dict:
    """确定性控制自检：固定时钟 + 固定 seed 产出稳定结果。"""
    c1, c2 = VirtualClock(), VirtualClock()
    r1, r2 = make_rng(), make_rng()
    s1 = [round(r1.random(), 6) for _ in range(5)]
    s2 = [round(r2.random(), 6) for _ in range(5)]
    stable = (s1 == s2) and (c1.now_iso() == c2.now_iso())
    return {"determinism_stable": stable, "seed": SEED,
            "clock": c1.now_iso(), "sample": s1}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R-HAR-1 dual-lane deterministic verifier")
    ap.add_argument("cmd",
                    choices=["init", "fingerprint", "plan", "run", "selfcheck", "demo"])
    ap.add_argument("--plans", default=default_plans_dir(),
                    help="docs/plans 目录（默认自动推导）")
    ap.add_argument("--lane", choices=["baseline", "degraded"], default="baseline")
    ap.add_argument("--write", action="store_true",
                    help="将计算结果写回 docs/plans/*.json（本会话默认 print-only）")
    ap.add_argument("--observations", default=None,
                    help="observation bundle 根目录（<fixture_id>/<viewport>.json）；"
                         "缺省时 baseline 全部 NOT_EXECUTED（fail-closed）")
    args = ap.parse_args(argv)

    if args.cmd == "demo":
        print(canonical_json(demo()))
        return 0

    if args.cmd == "init":
        res = init_fixtures(args.plans, write=args.write)
        print(canonical_json(res))
        return 0

    if args.cmd == "fingerprint":
        res = fingerprint(args.plans, write=args.write)
        print(canonical_json(res))
        return 0

    if args.cmd == "plan":
        print(canonical_json(plan_cells(args.lane)))
        return 0

    if args.cmd == "run":
        print(canonical_json(run_lane(args.lane, args.plans, args.observations)))
        return 0

    if args.cmd == "selfcheck":
        print(canonical_json(selfcheck(args.plans)))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
