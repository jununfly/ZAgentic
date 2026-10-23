#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R-RCP-1 — UI Agent Skills verification receipt 契约与判定

职责（契约见源仓库 ui-agent-skills-verification-receipt.md）：
  定义 verification receipt、聚合状态、stale/revalidation_required 与无法归因 quarantine，
  且三者状态可审计。

设计原则：
- 纯 stdlib，可离线运行；不依赖浏览器/adapter/网络。
- fail-closed：
    * 缺证据 / 空 cell / 算术不自洽 → 不得 PASS；
    * 无法归因 → QUARANTINED，不得降格成 FAIL（"不知道"不等于"已验证失败"）；
    * 过期不因 hash 未变而豁免。
- 收据 append-only：同一 receipt_id 内容变化即判 `RCP-V-07`；重出必须新 run_id。
- 判定与生成分离：`validate` / `check_freshness` / `validate_quarantine` 都是纯函数，
  不写盘、不重跑，供 1-9 paired run 与 1-10 rollout 复核直接调用。

契约文档：源仓库 ui-agent-skills-verification-receipt.md

CLI：
  verification_receipt.py build --lane <baseline|degraded> [--observations DIR]
                                [--plans DIR] [--commit SHA] [--reviewer NAME]
                                [--ttl-days N] [--worktree-dirty]
  verification_receipt.py validate <receipt.json> [--previous PREV.json]
  verification_receipt.py freshness <receipt.json> [--plans DIR] [--now ISO]
  verification_receipt.py selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hard_gates as hg  # noqa: E402
import dual_lane_runner as runner  # noqa: E402

# --------------------------------------------------------------------------- #
# 契约常量（单一事实源；文档与代码共用，测试防漂移）
# --------------------------------------------------------------------------- #

SCHEMA = "ui-agent-skills/verification-receipt/v1"
RECEIPT_VERSION = "1.0"
DEFAULT_TTL_DAYS = 14
LANES = ("baseline", "degraded")

# 14 段固定字段（dual-lane-runner.md  的字段清单）
REQUIRED_SECTIONS = (
    "claim", "checks", "risks", "fixtures", "env", "oracles", "thresholds",
    "command", "commit", "artifacts", "observed", "status", "reviewer", "expiry",
)
IDENTITY_FIELDS = ("schema", "receipt_id", "run_id", "lane", "issued_at")

CELL_STATUSES = (
    "PASS", "WARNING", "QUARANTINED", "HUMAN_REVIEW_REQUIRED", "FAIL",
    "NOT_EXECUTED", "DEGRADED_SKIP",
)
# 与 hard_gates.STATUS_PRECEDENCE 同序
PRECEDENCE = ("FAIL", "HUMAN_REVIEW_REQUIRED", "QUARANTINED", "WARNING", "PASS")
# 不进通过率分母（也不能变成 PASS）
EXCLUDED_FROM_DENOMINATOR = ("QUARANTINED", "NOT_EXECUTED", "DEGRADED_SKIP")
ATTRIBUTABLE_STATUSES = ("PASS", "WARNING", "FAIL", "HUMAN_REVIEW_REQUIRED")

# 维度 -> oracle（verification-matrix ；runner.VERIFICATION_CONFIG["oracles"] 是其全集）
ORACLE_BY_DIMENSION = {
    "dom_aria": ["static-assert"],
    "focus": ["interaction-sim"],
    "contrast": ["pixel-calc"],
    "overflow": ["pixel-calc"],
    "responsive": ["pixel-calc"],
    "motion": ["pixel-calc"],
    "state": ["schema-assert"],
    "round_trip": ["semantic-hash"],
    "migration": ["schema-assert"],
    "offline_recovery": ["recovery-assert"],
}

# 维度 -> 该维度消费的阈值键（config_hash 变化时据此收敛影响面）
THRESHOLD_KEYS_BY_DIMENSION = {
    "dom_aria": (),
    "focus": (),
    "contrast": ("contrast_ratio", "contrast_ratio_large", "non_text_contrast_ratio"),
    "overflow": ("overflow_px",),
    "responsive": ("overflow_px", "target_size_px"),
    "motion": ("motion_reduced_max_ms", "motion_autoplay_warn_ms"),
    "state": (),
}

QUARANTINE_REQUIRED_FIELDS = ("fixture", "dimension", "viewport", "evidence", "release_condition")

# 宽口径失效（无法收敛到部分 cell，或代价等同全量）
BROAD_FRESHNESS_CODES = ("RCP-F-01", "RCP-F-04", "RCP-F-05", "RCP-F-06", "RCP-F-07")


# --------------------------------------------------------------------------- #
# 基元
# --------------------------------------------------------------------------- #

canonical_json = runner.canonical_json
sha256_text = runner.sha256_text


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _deepcopy(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


def oracles_for(dimension):
    return list(ORACLE_BY_DIMENSION.get(dimension, []))


def thresholds_for(dimension, thresholds=None):
    src = dict(hg.GATE_THRESHOLDS if thresholds is None else thresholds)
    return {k: src[k] for k in THRESHOLD_KEYS_BY_DIMENSION.get(dimension, ()) if k in src}


def fixture_entries(manifest):
    """每个 fixture 的稳定字段 sha256（内容/class/landed_at 变化都能逐 id 定位）。"""
    entries = []
    for fx in sorted(manifest.get("fixtures", []), key=lambda f: str(f.get("id"))):
        stable = {k: fx.get(k) for k in runner.STABLE_FIELDS}
        entries.append({
            "id": fx.get("id"),
            "class": fx.get("class"),
            "sha256": sha256_text(canonical_json(stable)),
        })
    return entries


# --------------------------------------------------------------------------- #
# 当前事实源快照（重算 hash，供 freshness 比对）
# --------------------------------------------------------------------------- #

def current_facts(plans_dir=None):
    plans_dir = plans_dir or runner.default_plans_dir()
    facts = {
        "schema": SCHEMA,
        "config_version": runner.VERIFICATION_CONFIG["version"],
        "dimensions": list(runner.DIMENSIONS),
        "viewports": list(hg.REQUIRED_VIEWPORTS),
        "cell_gate": {d: dict(runner.CELL_GATE[d]) for d in runner.DIMENSIONS},
        "thresholds": dict(hg.GATE_THRESHOLDS),
        "oracles": list(runner.VERIFICATION_CONFIG["oracles"]),
        "planned_cells": [f'{c["dimension"]}/{c["class"]}' for c in runner.plan_cells("baseline")],
    }
    try:
        manifest = runner.load_json(
            os.path.join(plans_dir, "ui-agent-skills-fixture-manifest.json"))
        fp = runner.fingerprint(plans_dir, write=False)
        facts.update({
            "manifest_hash": runner.compute_manifest_hash(manifest),
            "env_hash": fp["env_hash"],
            "matrix_key": fp["matrix_key"],
            "config_hash": fp["config_hash"],
            "axes": fp["axes"],
            "fixtures": {
                "entries": fixture_entries(manifest),
                "counts_by_class": _counts_by_class(manifest.get("fixtures", [])),
            },
        })
    except Exception as exc:  # 事实源不可读 -> 由 freshness 判 REVALIDATION_REQUIRED
        facts["error"] = f"{type(exc).__name__}: {exc}"
    return facts


def _counts_by_class(fixtures):
    out = {}
    for fx in fixtures:
        cls = fx.get("class")
        out[cls] = out.get(cls, 0) + 1
    return out


# --------------------------------------------------------------------------- #
# 聚合
# --------------------------------------------------------------------------- #

def _verdict_from_statuses(statuses):
    """逐字镜像 dual_lane_runner._overall_status（单一答案，不另立一套口径）。"""
    return runner._overall_status(list(statuses))


def counts_from_cells(cells):
    counts = {s: 0 for s in CELL_STATUSES}
    unknown = []
    for cell in cells:
        status = cell.get("status")
        if status in counts:
            counts[status] += 1
        else:
            unknown.append(str(status))
    return counts, unknown


def aggregate_cells(cells):
    """cell 集合 -> 计数 + verdict + 通过率（报告字段，永不用于判 PASS）。

    verdict 与 runner 同源；未知 status 一律降级 HUMAN_REVIEW_REQUIRED（fail-closed），
    因为"没见过的状态"不能被算进 PASS 的构成里。
    """
    counts, unknown = counts_from_cells(cells)
    planned = len(cells)
    attributable = sum(counts[s] for s in ATTRIBUTABLE_STATUSES)
    excluded = sum(counts[s] for s in EXCLUDED_FROM_DENOMINATOR)

    verdict = _verdict_from_statuses([c.get("status") for c in cells])
    if unknown and verdict == "PASS":
        verdict = "HUMAN_REVIEW_REQUIRED"

    pass_rate = (counts["PASS"] / attributable) if attributable else 0.0
    return {
        "verdict": verdict,
        "planned_cells": planned,
        "counts": counts,
        "attributable": attributable,
        "excluded": excluded,
        "passed_cells": counts["PASS"],
        "pass_rate": round(pass_rate, 4),
        "unknown_statuses": unknown,
    }


# --------------------------------------------------------------------------- #
# quarantine
# --------------------------------------------------------------------------- #

def validate_quarantine(records, fixture_ids=None, dimensions=None, viewports=None):
    """无法归因判定：必须能映射到 fixture×dimension×viewport 且带证据与解除条件。

    两类都判 QUARANTINED；attribution 分开计数——attributed 可定位待修，
    unattributable 只能补采集重跑，不得转成 FAIL。
    """
    fixture_ids = set(fixture_ids or [])
    dimensions = set(dimensions or runner.DIMENSIONS)
    viewports = set(viewports or hg.REQUIRED_VIEWPORTS)

    out = []
    for idx, rec in enumerate(records or []):
        rec = dict(rec or {})
        codes = []
        missing = []
        fixture = rec.get("fixture")
        dimension = rec.get("dimension")
        viewport = rec.get("viewport")
        if not fixture or (fixture_ids and fixture not in fixture_ids):
            missing.append("fixture")
        if not dimension or (dimensions and dimension not in dimensions):
            missing.append("dimension")
        if not viewport or (viewports and viewport not in viewports):
            missing.append("viewport")
        if missing:
            codes.append("RCP-Q-01")
        evidence = rec.get("evidence")
        release = rec.get("release_condition")
        if not evidence or not release:
            codes.append("RCP-Q-02")
        resolution = str(rec.get("resolution") or "").upper()
        if resolution in ("PASS", "FAIL"):
            codes.append("RCP-Q-03")

        attribution = "unattributable" if codes else "attributed"
        out.append({
            "index": idx,
            "code": rec.get("code"),
            "detail": rec.get("detail"),
            "fixture": fixture,
            "dimension": dimension,
            "viewport": viewport,
            "evidence": list(evidence or []),
            "release_condition": release,
            "raised_by": rec.get("raised_by"),
            "raised_at": rec.get("raised_at"),
            "source": rec.get("source", "adapter"),
            "attribution": attribution,
            "missing_attribution_fields": missing,
            "codes": codes,
            "resolution": rec.get("resolution"),
        })

    codes = sorted({c for r in out for c in r["codes"]})
    return {
        "records": out,
        "verdict": "QUARANTINED" if out else None,
        "counts": {
            "total": len(out),
            "attributed": len([r for r in out if r["attribution"] == "attributed"]),
            "unattributable": len([r for r in out if r["attribution"] == "unattributable"]),
        },
        "codes": codes,
    }


def can_release(record, new_run_id=None, reviewer=None, old_run_id=None):
    """解除 quarantine：必须新 run_id + 复核人签署，否则不得改写原收据。"""
    codes = []
    if not new_run_id or new_run_id == old_run_id:
        codes.append("RCP-Q-04")
    if not isinstance(reviewer, dict) or not reviewer.get("name") or not reviewer.get("signed_at"):
        codes.append("RCP-Q-04")
    return {"released": not codes, "codes": codes}


# --------------------------------------------------------------------------- #
# 收据组装
# --------------------------------------------------------------------------- #

def _signed(reviewer):
    return isinstance(reviewer, dict) and bool(reviewer.get("name")) and bool(reviewer.get("signed_at"))


def _pinned(commit):
    commit = str(commit or "")
    if commit.startswith("UNPINNED"):
        return False
    return len(commit) == 40 and all(c in "0123456789abcdef" for c in commit.lower())


def _body_of(receipt):
    body = {k: v for k, v in receipt.items()
            if k not in ("receipt_id", "issued_at", "freshness", "body_hash")}
    return body


def receipt_body_hash(receipt):
    return sha256_text(canonical_json(_body_of(receipt)))


def _assemble(checks, *, lane, run_id, commit, artifacts, command, reviewer,
              issued_at, ttl_days, fixtures, env, risks, observations):
    agg = aggregate_cells(checks)
    verdict = agg["verdict"]
    reason_codes = []

    # PASS 的额外签发条件（缺一即降级，不静默）
    if verdict == "PASS" and not _signed(reviewer):
        verdict = "HUMAN_REVIEW_REQUIRED"
        reason_codes.append("RCP-A-07")
    if verdict == "PASS" and not _pinned(commit):
        verdict = "HUMAN_REVIEW_REQUIRED"
        reason_codes.append("RCP-A-08")

    quarantine = validate_quarantine(
        observations.get("quarantine_records") or [],
        fixture_ids=[e["id"] for e in fixtures.get("entries", [])],
    )
    reason_codes.extend(quarantine["codes"])
    if quarantine["verdict"] and verdict not in ("FAIL", "HUMAN_REVIEW_REQUIRED"):
        verdict = "QUARANTINED"

    expires_at = _iso(issued_at + timedelta(days=int(ttl_days)))
    receipt = {
        "schema": SCHEMA,
        "receipt_version": RECEIPT_VERSION,
        "run_id": run_id,
        "lane": lane,
        "issued_at": _iso(issued_at),
        "claim": {
            "subject": "EV-v0.1 deterministic verification",
            "scope": {
                "dimensions": sorted({c["dimension"] for c in checks}),
                "classes": sorted({c["class"] for c in checks}),
                "viewports": list(hg.REQUIRED_VIEWPORTS),
            },
            "asserts": "cells 的 status 由 R-HAR-2 硬门禁对 observation bundle 判定",
            "not_asserts": [
                "不证明 fixture 数据本身正确（fixture 由 1-6/1-7 提供）",
                "不证明浏览器真实渲染（采集由浏览器引擎负责）",
                "不覆盖 round_trip/migration/offline_recovery 的实测结论",
            ],
        },
        "checks": checks,
        "risks": list(risks or []),
        "fixtures": fixtures,
        "env": env,
        "oracles": list(runner.VERIFICATION_CONFIG["oracles"]),
        "thresholds": dict(hg.GATE_THRESHOLDS),
        "command": command,
        "commit": commit,
        "artifacts": list(artifacts or []),
        "observed": observations,
        "status": {
            "verdict": verdict,
            "raw_verdict": agg["verdict"],
            "counts": agg["counts"],
            "coverage": {
                "planned_cells": agg["planned_cells"],
                "passed_cells": agg["passed_cells"],
                "attributable": agg["attributable"],
                "excluded": agg["excluded"],
                "pass_rate": agg["pass_rate"],
                "unknown_statuses": agg["unknown_statuses"],
            },
            "reason_codes": sorted(set(reason_codes)),
            "quarantine": quarantine["counts"],
        },
        "reviewer": reviewer or None,
        "expiry": {"ttl_days": int(ttl_days), "expires_at": expires_at},
    }
    body_hash = receipt_body_hash(receipt)
    receipt["body_hash"] = body_hash
    receipt["receipt_id"] = "rcp-" + sha256_text(f"{lane}|{run_id}|{body_hash}")[:16]
    receipt["freshness"] = check_freshness(receipt, facts=observations.get("_facts"),
                                           now=issued_at)
    return receipt


def _check_from_cell(cell, command):
    dim = cell.get("dimension")
    observed = dict(cell.get("observed") or {})
    return {
        "cell": f"{dim}/{cell.get('class')}",
        "dimension": dim,
        "class": cell.get("class"),
        "gate": cell.get("gate"),
        "status": cell.get("status"),
        "oracle": oracles_for(dim),
        "threshold": thresholds_for(dim),
        "command": command,
        "coverage": {
            "planned_fixtures": None if observed.get("planned_fixtures") is None
            else observed.get("planned_fixtures"),
            "fixtures_with_evidence": observed.get("fixtures_seen", 0),
            "missing_fixtures": list(observed.get("missing_fixtures") or []),
        },
        "observed": observed,
    }


def build_receipt(lane_receipt, *, commit="UNPINNED", artifacts=None, command="",
                  reviewer=None, plans_dir=None, issued_at=None, ttl_days=DEFAULT_TTL_DAYS,
                  quarantine_records=None, worktree_dirty=False, risks=None):
    """把 R-HAR-1 的 lane receipt 升格为 R-RCP-1 完整收据（print-only，不写盘）。"""
    facts = current_facts(plans_dir)
    issued_at = issued_at or _now()
    command = command or (
        f'python dual_lane_runner.py run --lane '
        f'{lane_receipt.get("lane")} --observations '
        f'{lane_receipt.get("observations_dir") or "<DIR>"}'
    )
    checks = [_check_from_cell(c, command) for c in lane_receipt.get("cells", [])]

    manifest = runner.load_json(
        os.path.join(plans_dir or runner.default_plans_dir(),
                     "ui-agent-skills-fixture-manifest.json"))
    fixtures = {
        "manifest_hash": facts.get("manifest_hash"),
        "entries": facts.get("fixtures", {}).get("entries", []),
        "counts_by_class": facts.get("fixtures", {}).get("counts_by_class", {}),
    }
    env = {
        "env_hash": lane_receipt.get("env_hash"),
        "matrix_key": lane_receipt.get("matrix_key"),
        "config_version": lane_receipt.get("config_version"),
        "config_hash": lane_receipt.get("config_hash"),
        "manifest_hash": lane_receipt.get("manifest_hash"),
        "axes": facts.get("axes", {}),
    }
    observations = {
        "observations_dir": lane_receipt.get("observations_dir"),
        "fixtures_seen": sum(int(c.get("observed", {}).get("fixtures_seen") or 0) for c in checks),
        "bundles": sum(int(c.get("observed", {}).get("bundles") or 0) for c in checks),
        "missing_fixtures": sorted({f for c in checks
                                    for f in (c["observed"].get("missing_fixtures") or [])}),
        "quarantine_records": list(quarantine_records or []),
        "worktree_dirty": bool(worktree_dirty),
        "_facts": facts,
    }
    # 汇总 gate finding 里"无法归因"的证据，作为 unattributable 记录入账
    for cell in checks:
        for finding in cell["observed"].get("findings", []):
            if finding.get("severity") == "unattributable":
                observations["quarantine_records"].append({
                    "code": finding.get("code"),
                    "detail": finding.get("message"),
                    "fixture": None,
                    "dimension": cell["dimension"],
                    "viewport": None,
                    "evidence": [],
                    "release_condition": "",
                    "source": "gate-finding",
                })

    if worktree_dirty:
        # 工作树脏 -> 不允许 PASS：以 unpinned commit 表达同一约束
        commit = f"UNPINNED:dirty-worktree@{commit}"

    receipt = _assemble(
        checks, lane=lane_receipt.get("lane"), run_id=lane_receipt.get("run_id"),
        commit=commit, artifacts=artifacts, command=command, reviewer=reviewer,
        issued_at=issued_at, ttl_days=ttl_days,
        fixtures=fixtures, env=env, risks=risks, observations=observations,
    )
    receipt["observed"].pop("_facts", None)
    receipt["status"]["quarantine"] = validate_quarantine(
        observations["quarantine_records"],
        fixture_ids=[e["id"] for e in fixtures["entries"]],
    )["counts"]
    return receipt


# --------------------------------------------------------------------------- #
# 校验（结构 + 聚合 + quarantine；不重跑）
# --------------------------------------------------------------------------- #

def _finding(code, message, path=None):
    return {"code": code, "message": message, "path": path}


def validate(receipt, previous=None):
    findings = []

    if not isinstance(receipt, dict):
        return {"ok": False, "codes": ["RCP-V-01"], "findings": [_finding("RCP-V-01", "receipt 不是对象")]}

    for section in IDENTITY_FIELDS + REQUIRED_SECTIONS:
        if section not in receipt:
            findings.append(_finding("RCP-V-01", f"缺必填段 {section}", section))

    if receipt.get("schema") != SCHEMA:
        findings.append(_finding("RCP-V-02", "schema 不是可识别版本", "schema"))

    run_id = receipt.get("run_id")
    receipt_id = str(receipt.get("receipt_id") or "")
    if not run_id or not isinstance(run_id, str) or not receipt_id.startswith("rcp-"):
        findings.append(_finding("RCP-V-03", "run_id/receipt_id 缺失或不合规", "receipt_id"))

    if receipt.get("lane") not in LANES:
        findings.append(_finding("RCP-V-08", "lane 非法", "lane"))

    checks = receipt.get("checks") or []
    if not checks:
        findings.append(_finding("RCP-V-04", "checks 为空：没有任何 cell 被判定", "checks"))
        return {"ok": False, "codes": sorted({f["code"] for f in findings}), "findings": findings}

    claim = receipt.get("claim") or {}
    scope = claim.get("scope") or {}
    if not scope.get("dimensions") or not (receipt.get("command") or "").strip():
        findings.append(_finding("RCP-V-05", "claim 范围或 command 为空（结论不可复核）", "claim"))
    if not str(receipt.get("commit") or "").strip():
        findings.append(_finding("RCP-V-05", "commit 为空（结论不可追溯）", "commit"))

    fixtures = receipt.get("fixtures") or {}
    if not fixtures.get("entries"):
        findings.append(_finding("RCP-V-05", "fixtures.entries 为空", "fixtures"))
    if not (receipt.get("env") or {}).get("env_hash") or not (receipt.get("env") or {}).get("matrix_key"):
        findings.append(_finding("RCP-V-05", "env_hash/matrix_key 缺失", "env"))

    for idx, art in enumerate(receipt.get("artifacts") or []):
        if not isinstance(art, dict) or not art.get("path") or not art.get("sha256"):
            findings.append(_finding("RCP-V-06", "artifact 缺 path 或 sha256", f"artifacts[{idx}]"))

    if previous is not None and receipt.get("receipt_id") == previous.get("receipt_id"):
        if receipt_body_hash(receipt) != receipt_body_hash(previous):
            findings.append(_finding("RCP-V-07", "已签发收据被改写（同 receipt_id 内容变化）", "receipt_id"))

    # ---- 聚合自洽 ----
    agg = aggregate_cells(checks)
    status = receipt.get("status") or {}
    has_quarantine = bool((receipt.get("observed") or {}).get("quarantine_records"))
    reason_codes = set(status.get("reason_codes") or [])
    recorded_counts = status.get("counts") or {}
    if recorded_counts != agg["counts"]:
        findings.append(_finding("RCP-A-04", "counts 与 checks 不一致（分母算术不可审计）", "status.counts"))

    verdict = status.get("verdict")
    if verdict != agg["verdict"] and status.get("raw_verdict") != agg["verdict"]:
        # 允许两种"更严"的合法偏移：缺签/未钉 commit 降级、quarantine 提升
        stricter = (
            (verdict == "HUMAN_REVIEW_REQUIRED" and reason_codes & {"RCP-A-07", "RCP-A-08"})
            or (verdict == "QUARANTINED" and has_quarantine)
        )
        if not stricter:
            findings.append(_finding("RCP-A-03", "verdict 低于 cell 推出的结论", "status.verdict"))

    if verdict == "PASS":
        if agg["passed_cells"] != agg["planned_cells"] or agg["excluded"]:
            findings.append(_finding(
                "RCP-A-01", "PASS 但覆盖率不足（NOT_EXECUTED/DEGRADED_SKIP/非 PASS cell 存在）",
                "status.verdict"))
        if agg["counts"]["HUMAN_REVIEW_REQUIRED"] or agg["counts"]["QUARANTINED"]:
            findings.append(_finding("RCP-A-02", "PASS 但存在证据缺失/quarantine", "status.verdict"))
        if not _signed(receipt.get("reviewer")):
            findings.append(_finding("RCP-A-07", "PASS 缺复核人签署", "reviewer"))
        if not _pinned(receipt.get("commit")) or (receipt.get("observed") or {}).get("worktree_dirty"):
            findings.append(_finding("RCP-A-08", "PASS 但 commit 未钉住或工作树脏", "commit"))

    for idx, cell in enumerate(checks):
        if cell.get("status") == "PASS" and int((cell.get("observed") or {}).get("checked") or 0) <= 0:
            findings.append(_finding(
                "RCP-A-05", "cell 判 PASS 但 checked==0（空转假绿）", f"checks[{idx}]"))
        if verdict == "PASS" and int((cell.get("observed") or {}).get("bundles") or 0) <= 0:
            findings.append(_finding(
                "RCP-A-09", "PASS 但 cell 没有任何 observation bundle（无证据通过）",
                f"checks[{idx}]"))

    coverage = status.get("coverage") or {}
    attributable = agg["attributable"]
    expected_rate = round(agg["passed_cells"] / attributable, 4) if attributable else 0.0
    if coverage.get("attributable") is not None:
        if coverage["attributable"] != attributable or coverage.get("pass_rate") != expected_rate:
            findings.append(_finding(
                "RCP-A-06", "通过率分母包含不进分母的状态（QUARANTINED/NOT_EXECUTED/DEGRADED_SKIP）",
                "status.coverage"))
    elif coverage.get("pass_rate") not in (None, expected_rate):
        findings.append(_finding("RCP-A-06", "通过率分母口径不合规", "status.coverage"))

    # ---- quarantine ----
    # 注意：记录"无法归因"本身是合法内容（收据说的是"我不知道"），不构成收据结构错误；
    # Q-01/Q-02 是记录级审计码，由 validate_quarantine 报出并写入 status.reason_codes。
    records = (receipt.get("observed") or {}).get("quarantine_records") or []
    if records:
        result = validate_quarantine(
            records, fixture_ids=[e.get("id") for e in (fixtures.get("entries") or [])])
        declared = status.get("quarantine") or {}
        if declared and declared != result["counts"]:
            findings.append(_finding("RCP-A-04", "quarantine 计数与记录不一致", "status.quarantine"))
        if {r.get("resolution") for r in records
                if str(r.get("resolution") or "").upper() in ("PASS", "FAIL")}:
            findings.append(_finding("RCP-Q-03", "quarantine 被写成 PASS/FAIL", "observed.quarantine_records"))
        if result["verdict"] and verdict not in ("QUARANTINED", "FAIL", "HUMAN_REVIEW_REQUIRED"):
            findings.append(_finding("RCP-A-03", "有 quarantine 却未反映在 verdict", "status.verdict"))

    codes = sorted({f["code"] for f in findings})
    return {"ok": not codes, "codes": codes, "findings": findings}


# --------------------------------------------------------------------------- #
# 新鲜度（stale / revalidation_required）
# --------------------------------------------------------------------------- #

def check_freshness(receipt, facts=None, plans_dir=None, now=None):
    facts = facts if facts is not None else current_facts(plans_dir)
    now = now or _now()
    codes = {}
    cells = set()

    def flag(code, detail, scope_cells=None):
        codes.setdefault(code, []).append(detail)
        if scope_cells:
            cells.update(scope_cells)

    checks = receipt.get("checks") or []
    all_cells = [c.get("cell") for c in checks]

    if facts.get("error"):
        flag("RCP-F-06", f"事实源不可读：{facts['error']}")
    if facts.get("schema") and receipt.get("schema") != facts["schema"]:
        flag("RCP-F-07", "schema 版本升版")
    if facts.get("env_hash") and (receipt.get("env") or {}).get("env_hash") != facts["env_hash"]:
        flag("RCP-F-01", "env 轴变化（env_hash 失配）")

    # 维度集合 / cell 门禁 / 维度与 class 组成
    scope_dims = set(((receipt.get("claim") or {}).get("scope") or {}).get("dimensions") or [])
    if facts.get("dimensions") and scope_dims != set(facts["dimensions"]):
        flag("RCP-F-04", "维度集合变化")
    planned = set(facts.get("planned_cells") or [])
    if planned and set(all_cells) != planned:
        flag("RCP-F-04", "cell 计划变化（维度或 cell 门禁）")

    # fixture 漂移 -> 该 class 的 cell
    old_entries = {e.get("id"): e for e in ((receipt.get("fixtures") or {}).get("entries") or [])}
    new_entries = {e.get("id"): e for e in (facts.get("fixtures", {}).get("entries") or [])}
    if new_entries:
        changed_ids = []
        for fid in set(old_entries) | set(new_entries):
            old, new = old_entries.get(fid), new_entries.get(fid)
            if old is None or new is None or old.get("sha256") != new.get("sha256"):
                changed_ids.append(fid)
        classes = set()
        for fid in changed_ids:
            entry = new_entries.get(fid) or old_entries.get(fid) or {}
            if entry.get("class"):
                classes.add(entry["class"])
        if changed_ids:
            scoped = [c.get("cell") for c in checks if c.get("class") in classes]
            flag("RCP-F-02", f"fixture 漂移：{sorted(changed_ids)}", scoped)

    # 阈值 / oracle 漂移 -> 该维度 cell
    for cell in checks:
        dim = cell.get("dimension")
        if dim in THRESHOLD_KEYS_BY_DIMENSION:
            current = thresholds_for(dim, facts.get("thresholds"))
        else:
            current = cell.get("threshold") or {}
        if canonical_json(cell.get("threshold") or {}) != canonical_json(current):
            flag("RCP-F-03", f"{cell.get('cell')} 阈值变化", [cell.get("cell")])
        if facts.get("oracles") and sorted(cell.get("oracle") or []) != sorted(oracles_for(dim)):
            flag("RCP-F-03", f"{cell.get('cell')} oracle 变化", [cell.get("cell")])

    # matrix_key 失配但无具体原因 -> 保守全量
    env = receipt.get("env") or {}
    if facts.get("matrix_key") and env.get("matrix_key") != facts["matrix_key"] and not codes:
        flag("RCP-F-04", "matrix_key 失配且无法归因")

    # 过期
    expires_at = _parse_iso(((receipt.get("expiry") or {}).get("expires_at")))
    if expires_at is None or now > expires_at:
        flag("RCP-F-05", "收据已过期")

    broad = [c for c in codes if c in BROAD_FRESHNESS_CODES]
    if not codes:
        status = "FRESH"
    elif broad:
        status = "REVALIDATION_REQUIRED"
    else:
        status = "STALE"

    if status == "FRESH":
        scope = "none"
        scope_cells = []
    elif status == "REVALIDATION_REQUIRED":
        scope = "all"
        scope_cells = sorted(all_cells)
    else:
        scope = "cells"
        scope_cells = sorted(cells)

    return {
        "status": status,
        "checked_at": _iso(now),
        "changed": sorted(codes),
        "detail": {k: v for k, v in sorted(codes.items())},
        "revalidate": {
            "required": status != "FRESH",
            "scope": scope,
            "cells": scope_cells,
            "reason_codes": sorted(codes),
        },
    }


# --------------------------------------------------------------------------- #
# selftest —— 每条 code 都必须真的响过
# --------------------------------------------------------------------------- #

def _base_receipt():
    facts = {
        "schema": SCHEMA,
        "config_version": runner.VERIFICATION_CONFIG["version"],
        "dimensions": list(runner.DIMENSIONS),
        "viewports": list(hg.REQUIRED_VIEWPORTS),
        "thresholds": dict(hg.GATE_THRESHOLDS),
        "oracles": list(runner.VERIFICATION_CONFIG["oracles"]),
        "planned_cells": [f'{c["dimension"]}/{c["class"]}' for c in runner.plan_cells("baseline")],
        "manifest_hash": "m" * 64,
        "env_hash": "e" * 64,
        "matrix_key": "k" * 64,
        "config_hash": "c" * 64,
        "fixtures": {"entries": [], "counts_by_class": {}},
    }
    # 补齐到全量 cell 计划，保证 base 的结构不触发 F-04
    checks = []
    for dim in runner.DIMENSIONS:
        for cls in ("form", "adapter", "contract"):
            if runner.CELL_GATE[dim][cls] == "-":
                continue
            checks.append({
                "cell": f"{dim}/{cls}", "dimension": dim, "class": cls, "gate": "A",
                "status": "PASS", "oracle": oracles_for(dim),
                "threshold": thresholds_for(dim),
                "command": "python x run --lane baseline",
                "coverage": {"planned_fixtures": 1, "fixtures_with_evidence": 1,
                             "missing_fixtures": []},
                "observed": {"fixtures_seen": 1, "bundles": 3, "missing_fixtures": [],
                             "checked": 4, "findings": []},
            })
    facts["planned_cells"] = [c["cell"] for c in checks]
    facts["fixtures"] = {
        "entries": [{"id": "F-1", "class": "form", "sha256": "a" * 64}],
        "counts_by_class": {"form": 1},
    }
    facts["manifest_hash"] = sha256_text(canonical_json(facts["fixtures"]["entries"]))
    receipt = _assemble(
        checks, lane="baseline", run_id="run-selftest",
        commit="a" * 40, artifacts=[{"path": "docs/designs/ui-agent-skills/x.json", "sha256": "b" * 64}],
        command="python x run --lane baseline",
        reviewer={"name": "zj", "signed_at": "2026-10-20T00:00:00+00:00"},
        issued_at=datetime(2026, 10, 20, tzinfo=timezone.utc), ttl_days=DEFAULT_TTL_DAYS,
        fixtures={"manifest_hash": facts["manifest_hash"], "entries": facts["fixtures"]["entries"],
                  "counts_by_class": facts["fixtures"]["counts_by_class"]},
        env={"env_hash": facts["env_hash"], "matrix_key": facts["matrix_key"],
             "config_version": facts["config_version"], "config_hash": facts["config_hash"],
             "manifest_hash": facts["manifest_hash"], "axes": {}},
        risks=[], observations={"_facts": facts},
    )
    return receipt, facts


def selftest():
    cases = []

    def case(name, expected_code, fn):
        try:
            codes = fn()
        except Exception as exc:  # 自检自身失败也要可见
            cases.append({"name": name, "expected_code": expected_code,
                          "got_codes": [f"EXC:{type(exc).__name__}:{exc}"], "ok": False})
            return
        got = sorted(set(codes))
        ok = (expected_code in got) if expected_code else (not got)
        cases.append({"name": name, "expected_code": expected_code, "got_codes": got, "ok": ok})

    base, facts = _base_receipt()
    now = datetime(2026, 10, 21, tzinfo=timezone.utc)

    def v(mutate, previous=None):
        r = _deepcopy(base)
        mutate(r)
        return validate(r, previous=previous)["codes"]

    def f(mutate, facts_override=None):
        r = _deepcopy(base)
        mutate(r)
        return check_freshness(r, facts=facts_override or facts, now=now)["revalidate"]["reason_codes"]

    # 正例
    case("positive/valid", None, lambda: v(lambda r: None))
    case("positive/freshness-fresh", None, lambda: f(lambda r: None))
    case("positive/quarantine-attributed", None, lambda: validate_quarantine(
        [{"code": "ADAPTER-FLAKY", "fixture": "F-1", "dimension": "overflow",
          "viewport": "390x844", "evidence": ["a.png"], "release_condition": "重跑 3 次稳定"}],
        fixture_ids=["F-1"])["codes"])

    # 结构性
    case("V-01/missing-section", "RCP-V-01", lambda: v(lambda r: r.pop("thresholds")))
    case("V-02/bad-schema", "RCP-V-02", lambda: v(lambda r: r.update({"schema": "v0"})))
    case("V-03/bad-receipt-id", "RCP-V-03", lambda: v(lambda r: r.update({"receipt_id": "x"})))
    case("V-04/empty-checks", "RCP-V-04", lambda: v(lambda r: r.update({"checks": []})))
    case("V-05/empty-command", "RCP-V-05", lambda: v(lambda r: r.update({"command": "  "})))
    case("V-06/artifact-no-sha", "RCP-V-06", lambda: v(
        lambda r: r.update({"artifacts": [{"path": "a.json"}]})))
    case("V-07/reissued-mutation", "RCP-V-07", lambda: (
        lambda prev: v(lambda r: r["claim"].update({"asserts": "改过的声明"}), previous=prev)
    )(_deepcopy(base)))
    case("V-08/bad-lane", "RCP-V-08", lambda: v(lambda r: r.update({"lane": "staging"})))

    # 聚合
    def a01(r):
        r["checks"][0]["status"] = "NOT_EXECUTED"
        r["status"]["counts"] = aggregate_cells(r["checks"])["counts"]
        r["status"]["verdict"] = "PASS"
        r["status"]["raw_verdict"] = "PASS"

    case("A-01/pass-with-coverage-gap", "RCP-A-01", lambda: v(a01))

    def a02(r):
        r["checks"][0]["status"] = "HUMAN_REVIEW_REQUIRED"
        agg = aggregate_cells(r["checks"])
        r["status"]["counts"] = agg["counts"]
        r["status"]["verdict"] = "PASS"
        r["status"]["raw_verdict"] = "PASS"

    case("A-02/pass-with-evidence-gap", "RCP-A-02", lambda: v(a02))

    def a03(r):
        r["checks"][0]["status"] = "FAIL"
        agg = aggregate_cells(r["checks"])
        r["status"]["counts"] = agg["counts"]
        r["status"]["verdict"] = "WARNING"
        r["status"]["raw_verdict"] = "WARNING"

    case("A-03/verdict-below-cells", "RCP-A-03", lambda: v(a03))
    case("A-04/counts-mismatch", "RCP-A-04", lambda: v(
        lambda r: r["status"]["counts"].update({"PASS": 999})))
    case("A-05/pass-with-zero-checked", "RCP-A-05", lambda: v(
        lambda r: r["checks"][0]["observed"].update({"checked": 0})))
    def a09(r):
        r["checks"][0]["observed"].update({"bundles": 0})
    case("A-09/pass-without-evidence", "RCP-A-09", lambda: v(a09))
    case("A-06/pass-rate-denominator", "RCP-A-06", lambda: v(
        lambda r: r["status"]["coverage"].update({"attributable": 1, "pass_rate": 0.5})))
    case("A-07/pass-without-reviewer", "RCP-A-07", lambda: v(
        lambda r: r.update({"reviewer": None})))
    case("A-08/pass-with-unpinned-commit", "RCP-A-08", lambda: v(
        lambda r: r.update({"commit": "UNPINNED:worktree"})))

    # 新鲜度
    case("F-01/env-drift", "RCP-F-01", lambda: f(
        lambda r: None, {**facts, "env_hash": "z" * 64, "matrix_key": "z" * 64}))
    case("F-02/fixture-drift-class-scoped", "RCP-F-02", lambda: f(
        lambda r: None, {**facts, "fixtures": {
            "entries": [{"id": "F-1", "class": "form", "sha256": "0" * 64}],
            "counts_by_class": {"form": 1}}}))
    case("F-03/threshold-drift-dimension-scoped", "RCP-F-03", lambda: f(
        lambda r: None, {**facts, "thresholds": {**hg.GATE_THRESHOLDS, "overflow_px": 2}}))
    case("F-04/dimension-set-drift", "RCP-F-04", lambda: f(
        lambda r: None, {**facts, "dimensions": facts["dimensions"] + ["extra"]}))
    def f05():
        res = check_freshness(_deepcopy(base), facts=facts,
                              now=datetime(2027, 1, 1, tzinfo=timezone.utc))
        return res["revalidate"]["reason_codes"]

    case("F-05/expired", "RCP-F-05", f05)
    case("F-06/unreadable-facts", "RCP-F-06", lambda: f(
        lambda r: None, {"error": "FileNotFoundError: manifest"}))
    case("F-07/schema-bump", "RCP-F-07", lambda: f(
        lambda r: None, {**facts, "schema": "ui-agent-skills/verification-receipt/v2"}))

    # quarantine
    def q01():
        return validate_quarantine([{"code": "ADAPTER-FLAKY", "dimension": "overflow",
                                     "viewport": "390x844", "evidence": ["a"],
                                     "release_condition": "r"}], fixture_ids=["F-1"])["codes"]

    case("Q-01/unattributable-no-fixture", "RCP-Q-01", q01)

    def q02():
        return validate_quarantine([{"code": "ADAPTER-FLAKY", "fixture": "F-1",
                                     "dimension": "overflow", "viewport": "390x844"}],
                                   fixture_ids=["F-1"])["codes"]

    case("Q-02/no-evidence-or-release", "RCP-Q-02", q02)
    case("Q-03/quarantine-resolved-as-pass", "RCP-Q-03", lambda: v(
        lambda r: r["observed"].update({"quarantine_records": [
            {"code": "ADAPTER-FLAKY", "fixture": "F-1", "dimension": "overflow",
             "viewport": "390x844", "evidence": ["a"], "release_condition": "r",
             "resolution": "PASS"}]})))
    case("Q-04/release-without-new-run", "RCP-Q-04", lambda: can_release(
        {"fixture": "F-1"}, new_run_id="run-selftest", reviewer={"name": "zj"},
        old_run_id="run-selftest")["codes"])

    # 聚合口径与 runner 同源（正例兜底）
    case("mirror/runner-verdict", None, lambda: (
        [] if all(_verdict_from_statuses(s) == runner._overall_status(s)
                  for s in ([], ["PASS"], ["PASS", "NOT_EXECUTED"], ["FAIL", "PASS"],
                            ["QUARANTINED"], ["HUMAN_REVIEW_REQUIRED", "PASS"],
                            ["WARNING", "PASS"], ["DEGRADED_SKIP"]))
        else ["MIRROR-DRIFT"]))

    # build 路径：真实 runner receipt -> 收据
    def build_ok():
        lane = runner.run_lane("degraded", runner.default_plans_dir())
        receipt = build_receipt(lane, commit="a" * 40, issued_at=datetime(2026, 10, 20, tzinfo=timezone.utc))
        return validate(receipt)["codes"]

    case("build/degraded-receipt-valid", None, build_ok)

    def build_deterministic():
        lane = runner.run_lane("degraded", runner.default_plans_dir())
        at = datetime(2026, 10, 20, tzinfo=timezone.utc)
        a = build_receipt(lane, commit="a" * 40, issued_at=at)
        b = build_receipt(lane, commit="a" * 40, issued_at=at)
        return [] if canonical_json(a) == canonical_json(b) else ["NOT-DETERMINISTIC"]

    case("build/deterministic", None, build_deterministic)

    failed = [c for c in cases if not c["ok"]]
    return {"total": len(cases), "failed": len(failed), "ok": not failed, "cases": cases}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def artifact_entry(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        return {"path": path, "sha256": sha256_text_bytes(data)}
    except OSError:
        return {"path": path, "sha256": "UNREADABLE"}


def sha256_text_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="R-RCP-1 verification receipt")
    ap.add_argument("cmd", choices=["build", "validate", "freshness", "selftest"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--lane", choices=list(LANES), default="baseline")
    ap.add_argument("--plans", default=None)
    ap.add_argument("--observations", default=None)
    ap.add_argument("--commit", default="UNPINNED")
    ap.add_argument("--reviewer", default=None)
    ap.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    ap.add_argument("--worktree-dirty", action="store_true")
    ap.add_argument("--artifact", action="append", default=[])
    ap.add_argument("--previous", default=None)
    ap.add_argument("--now", default=None)
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        res = selftest()
        print(canonical_json(res))
        return 0 if res["ok"] else 1

    if args.cmd == "build":
        # 惰性解析：显式 --plans 优先，缺省时才推导（见 dual_lane_runner.default_plans_dir）
        plans = args.plans or runner.default_plans_dir()
        lane_receipt = runner.run_lane(args.lane, plans, args.observations)
        receipt = build_receipt(
            lane_receipt, commit=args.commit,
            artifacts=[artifact_entry(p) for p in args.artifact],
            reviewer={"name": args.reviewer, "signed_at": _iso(_now())} if args.reviewer else None,
            plans_dir=plans, ttl_days=args.ttl_days,
            worktree_dirty=args.worktree_dirty,
        )
        print(canonical_json(receipt))
        return 0

    if not args.file:
        print("需要 receipt 文件路径", file=sys.stderr)
        return 2
    receipt = load_json(args.file)

    if args.cmd == "validate":
        previous = load_json(args.previous) if args.previous else None
        res = validate(receipt, previous=previous)
        print(canonical_json(res))
        return 0 if res["ok"] else 1

    if args.cmd == "freshness":
        res = check_freshness(receipt, plans_dir=args.plans or runner.default_plans_dir(),
                             now=_parse_iso(args.now) if args.now else None)
        print(canonical_json(res))
        return 0 if res["status"] == "FRESH" else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
