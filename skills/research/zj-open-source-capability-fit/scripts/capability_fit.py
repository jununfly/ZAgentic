#!/usr/bin/env python3
"""zj-open-source-capability-fit — 开源能力拟合决策模型的操作化仪器。

把本仓库《开源能力拟合决策模型》从方法论文档操作化成带机械闸门的决策工具。

权威模型 SSOT: docs/agreements/open-source-capability-fit-decision-model.md
（本仓库 SSOT）。

本脚本只做确定性计算与闸门校验，不做主观判断；最终分类由 Human/Agent 拍板，
但脚本必须给出**可复核的推荐分类 + 依据**，满足模型「完成标准」：
第三方 Agent 仅凭决策记录即可复核分类依据，识别证据 vs 假设。

子命令:
  init    写出一份空白输入模板(JSON)
  assess  加载输入 -> 跑闸门 -> 计算 -> 打印推荐分类(+可选 --record 产出决策记录)
  validate 仅跑闸门，打印每项闸门结果

设计纪律: 仅依赖 stdlib，零新依赖。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# ----------------------------------------------------------------------------
# 常量 (可经 CLI 覆盖，保持跨候选一致即可)
# ----------------------------------------------------------------------------

# 有效拟合度三因子乘积里，每个因子落在 [0,1]
FIT_OK = 0.9          # 需求"算被满足"的阈值
FIT_FAIL = 0.5        # 关键需求有效拟合度低于此 = 关键缺口 -> D

# 总所有权成本 E 的阈值 (单位自定，跨候选须一致)
E_LOW = 20.0          # 低于此视为"可忽略"
E_MID = 80.0          # 低于此视为"可控"
E_HIGH = 200.0        # 高于此视为"超出可接受范围" -> 倾向 D

# 可控 B 边界: 适配层可承担的薄层 (allowed) vs 主体能力 (forbidden)
ALLOWED_ADAPT = {
    "identity-map": "身份映射",
    "query-adapt": "查询适配",
    "state-transform": "状态转换",
    "coord-semantics-claim-lease": "claim/lease 等小型协调语义",
    "provenance-adapt": "来源和可追溯信息适配",
}
FORBIDDEN_ADAPT = {
    "storage-sync-infra": "存储和同步基础设施",
    "full-retrieval-memory": "完整检索或记忆流水线",
    "acl-perms": "ACL 和权限系统",
    "full-workflow-task-platform": "完整工作流或任务平台",
}

# 单元状态
STATUS_NATIVE = "native"          # 原生支持
STATUS_ADAPTED = "adapted"        # 适配后支持
STATUS_UNKNOWN = "unknown"        # 未知 (需 PoC)
STATUS_UNSUPPORTED = "unsupported"  # 不支持

VALID_STATUS = {STATUS_NATIVE, STATUS_ADAPTED, STATUS_UNKNOWN, STATUS_UNSUPPORTED}
VALID_PRIORITY = {"must", "want", "nice"}
VALID_B_MODE = {"adapter", "plugin", "sidecar", "upstream-contrib", "fork"}
MATRIX_FIELDS = {
    "coverage",
    "semantic_match",
    "composability",
    "status",
    "evidence",
    "notes",
}
FIT_FIELDS = ("coverage", "semantic_match", "composability")


# ----------------------------------------------------------------------------
# 数据模型
# ----------------------------------------------------------------------------

@dataclass
class GateResult:
    name: str
    ok: bool
    message: str


@dataclass
class CandidateResult:
    cid: str
    name: str
    version: str
    must_coverage: float          # 关键需求满足比例 [0,1]
    avg_fit: float                # 全部需求有效拟合度均值(算术平均, 非加权)
    total_e: float                # 总所有权成本
    critical_gap: bool
    forbidden_touched: bool
    recommended: str              # A / B1 / B2 / B3 / C / D / BLOCKED
    reasons: list[str] = field(default_factory=list)
    gates: list[GateResult] = field(default_factory=list)


# ----------------------------------------------------------------------------
# 计算核心
# ----------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def effective_fit(cell: dict) -> float:
    """有效拟合度 = 覆盖 × 语义匹配 × 可组合性 (canonical 两判定量之一)."""
    cov = _clamp01(cell.get("coverage", 0.0))
    sem = _clamp01(cell.get("semantic_match", 0.0))
    comp = _clamp01(cell.get("composability", 0.0))
    return cov * sem * comp


def cell_satisfied(cell: dict) -> bool:
    """状态为 native/adapted 且有效拟合度 >= FIT_OK 才算满足."""
    if cell.get("status") not in (STATUS_NATIVE, STATUS_ADAPTED):
        return False
    return effective_fit(cell) >= FIT_OK


def is_must(req: dict) -> bool:
    return req.get("priority") == "must" or bool(req.get("critical", False))


def run_gates(data: dict, cid: str) -> list[GateResult]:
    """机械闸门: 不依赖自觉，任一不过则拒绝给出自信分类."""
    gates: list[GateResult] = []
    reqs = data.get("requirements", [])
    cand = next((c for c in data.get("candidates", []) if c.get("id") == cid), {})
    matrix = data.get("matrix", {}).get(cid, {})
    adaptation = data.get("adaptation", {}).get(cid, {})

    # G1 矩阵完整性: 每个 (R × O) 单元存在，字段齐全且枚举/拟合因子合法。
    missing = [r["id"] for r in reqs if r["id"] not in matrix]
    malformed = []
    for requirement in reqs:
        rid = requirement["id"]
        if rid not in matrix:
            continue
        cell = matrix[rid]
        problems = []
        if not isinstance(cell, dict):
            problems.append("单元不是 object")
        else:
            absent = sorted(MATRIX_FIELDS - set(cell))
            if absent:
                problems.append(f"缺字段 {absent}")
            if cell.get("status") not in VALID_STATUS:
                problems.append(f"非法 status={cell.get('status')!r}")
            bad_fits = [
                field
                for field in FIT_FIELDS
                if isinstance(cell.get(field), bool)
                or not isinstance(cell.get(field), (int, float))
                or not 0.0 <= float(cell[field]) <= 1.0
            ]
            if bad_fits:
                problems.append(f"拟合因子须在 [0,1]: {bad_fits}")
        if problems:
            malformed.append(f"{rid}({'; '.join(problems)})")
    gates.append(GateResult(
        "G1-matrix-complete",
        ok=not missing and not malformed,
        message=(
            "OK"
            if not missing and not malformed
            else "; ".join(
                part for part in (
                    f"缺单元: {missing}" if missing else "",
                    f"非法单元: {malformed}" if malformed else "",
                )
                if part
            )
        ),
    ))

    # G2 每个需求有 priority 与 critical 字段
    bad_reqs = [r["id"] for r in reqs
                if r.get("priority") not in VALID_PRIORITY or "critical" not in r]
    gates.append(GateResult(
        "G2-req-fields",
        ok=not bad_reqs,
        message=("OK" if not bad_reqs else f"需求字段缺失: {bad_reqs}"),
    ))

    # G3 候选版本固定 (canonical: 固定每个候选的版本)
    gates.append(GateResult(
        "G3-version-pinned",
        ok=bool(cand.get("version")),
        message=("OK" if cand.get("version") else f"候选 {cid} 未固定版本"),
    ))

    # G4 被标记为满足的单元必须有非空证据 (canonical: 结论须来自一手资料)
    no_ev = [
        r["id"]
        for r in reqs
        if r["id"] in matrix
        and isinstance(matrix[r["id"]], dict)
        and matrix[r["id"]].get("status") in (STATUS_NATIVE, STATUS_ADAPTED)
        and (
            not isinstance(matrix[r["id"]].get("evidence"), str)
            or not matrix[r["id"]]["evidence"].strip()
        )
    ]
    gates.append(GateResult(
        "G4-evidence-present",
        ok=not no_ev,
        message=("OK" if not no_ev else f"满足单元缺证据: {no_ev}"),
    ))

    # G5 关键未知项须有 PoC 计划 (canonical: 未知项须消除或有可接受验证计划)
    unknown_must = [r["id"] for r in reqs
                    if is_must(r) and r["id"] in matrix
                    and isinstance(matrix[r["id"]], dict)
                    and matrix[r["id"]].get("status") == STATUS_UNKNOWN]
    raw_poc = adaptation.get("poc_plan") or data.get("poc_plan") or ""
    poc = raw_poc.strip() if isinstance(raw_poc, str) else ""
    gates.append(GateResult(
        "G5-unknown-poc-plan",
        ok=not unknown_must or bool(poc),
        message=("OK" if (not unknown_must or poc) else f"关键未知项无 PoC 计划: {unknown_must}"),
    ))

    # G6 适配模式枚举：缺省 mode 仍表示待细分的通用 B；显式值必须属于契约。
    mode = adaptation.get("mode")
    mode_ok = mode in (None, "") or (isinstance(mode, str) and mode in VALID_B_MODE)
    gates.append(GateResult(
        "G6-adaptation-mode",
        ok=mode_ok,
        message=(
            "OK"
            if mode_ok
            else f"非法 adaptation.mode={mode!r}; 允许值: {sorted(VALID_B_MODE)}"
        ),
    ))

    return gates


def classify_candidate(data: dict, cid: str) -> CandidateResult:
    reqs = data.get("requirements", [])
    matrix = data.get("matrix", {}).get(cid, {})
    cost = data.get("cost", {}).get(cid, {})
    adaptation = data.get("adaptation", {}).get(cid, {})
    gates = run_gates(data, cid)

    res = CandidateResult(
        cid=cid,
        name=next((c.get("name", cid) for c in data.get("candidates", []) if c.get("id") == cid), cid),
        version=next((c.get("version", "?") for c in data.get("candidates", []) if c.get("id") == cid), "?"),
        must_coverage=0.0, avg_fit=0.0, total_e=0.0,
        critical_gap=False, forbidden_touched=False,
        recommended="BLOCKED", reasons=[], gates=gates,
    )

    # 硬闸门（除 G5 外均为输入合法性）不过 -> 拒绝自信分类。
    # G5 (未知项无 PoC 计划) 是就绪度提示，不阻塞分类，仅作理由附注
    failed = [g for g in gates if not g.ok and g.name != "G5-unknown-poc-plan"]
    if failed:
        res.reasons.append("闸门未过，拒绝给出自信分类: " + "; ".join(g.message for g in failed))
        return res
    g5 = next((g for g in gates if g.name == "G5-unknown-poc-plan" and not g.ok), None)
    if g5:
        res.reasons.append("就绪度提示: " + g5.message + " (要退出 D 进入实施须补 PoC 计划)")

    # 计算拟合度
    fits = [effective_fit(matrix[r["id"]]) for r in reqs if r["id"] in matrix]
    res.avg_fit = sum(fits) / len(fits) if fits else 0.0
    must_reqs = [r for r in reqs if is_must(r)]
    must_satisfied = [r for r in must_reqs if cell_satisfied(matrix[r["id"]])]
    res.must_coverage = (len(must_satisfied) / len(must_reqs)) if must_reqs else 1.0

    # 成本 E
    res.total_e = float(sum(cost.get(k, 0.0) for k in (
        "initial_dev", "integration", "maintenance", "upstream_adapt", "ops", "security_gov")))

    # 关键缺口检测 (canonical: 关键能力缺失不能由非关键高覆盖抵消)
    for r in must_reqs:
        cell = matrix[r["id"]]
        if cell.get("status") in (STATUS_UNSUPPORTED, STATUS_UNKNOWN):
            res.critical_gap = True
            res.reasons.append(f"关键需求 {r['id']} 状态={cell.get('status')} -> 继续搜索(D)")
        elif effective_fit(cell) < FIT_FAIL:
            res.critical_gap = True
            res.reasons.append(f"关键需求 {r['id']} 有效拟合度={effective_fit(cell):.2f}<{FIT_FAIL} -> 继续搜索(D)")

    if res.critical_gap:
        res.recommended = "D"
        return res

    # 适配层范围校验 (canonical: 可控 B = 可移除薄层)
    scope = adaptation.get("scope", []) or []
    forbidden_hit = [s for s in scope if s in FORBIDDEN_ADAPT]
    allowed_hit = [s for s in scope if s in ALLOWED_ADAPT]
    res.forbidden_touched = bool(forbidden_hit)
    if forbidden_hit:
        res.reasons.append("适配层触碰主体能力(禁止类目): " + ", ".join(
            f"{s}({FORBIDDEN_ADAPT[s]})" for s in forbidden_hit) + " -> 至少降为 C")

    # 关键需求部分满足 (0.5<=fit<0.9 且 adapted) = 真实缺口
    must_gap = any(
        is_must(r) and matrix[r["id"]].get("status") in (STATUS_NATIVE, STATUS_ADAPTED)
        and effective_fit(matrix[r["id"]]) < FIT_OK
        for r in reqs)

    # 分类决策
    if forbidden_hit:
        if adaptation.get("responsibility_uncontrolled") or res.total_e > E_HIGH:
            res.recommended = "D"
            res.reasons.append(f"主体能力建设且(责任不可控 或 E={res.total_e:.0f}>{E_HIGH}) -> D")
        else:
            res.recommended = "C"
            res.reasons.append(f"主体能力建设但责任可控 -> C")
        return res

    if must_gap:
        if res.total_e <= E_MID:
            res.recommended = "B" if scope else "C"
            res.reasons.append(f"关键需求存在部分缺口但 E={res.total_e:.0f}<=E_MID -> {res.recommended}")
        else:
            res.recommended = "C"
            res.reasons.append(f"关键需求缺口且 E={res.total_e:.0f}>E_MID -> C")
        return res

    # 无关键缺口、无禁止类目
    adapted_cells = [r["id"] for r in reqs
                    if r["id"] in matrix and matrix[r["id"]].get("status") == STATUS_ADAPTED]
    if not adapted_cells and not scope and res.total_e <= E_LOW:
        res.recommended = "A"
        res.reasons.append(f"关键能力完整、无适配层、E={res.total_e:.0f}<=E_LOW -> A(直接采用)")
    elif res.total_e <= E_MID:
        mode = adaptation.get("mode")
        if mode == "upstream-contrib":
            res.recommended = "B2"
            res.reasons.append("上游贡献补齐能力 -> B2")
        elif mode in ("adapter", "plugin", "sidecar"):
            res.recommended = "B1"
            res.reasons.append("外部 Adapter/插件/sidecar 扩展、不维护 fork -> B1")
        elif mode == "fork":
            res.recommended = "B3"
            res.reasons.append("维护长期 fork -> B3")
        else:
            res.recommended = "B"
            res.reasons.append(f"缺口小且可控、E={res.total_e:.0f}<=E_MID -> B (需声明 mode 细分 B1/B2/B3)")
    else:
        res.recommended = "C"
        res.reasons.append(f"成本 E={res.total_e:.0f}>E_MID -> C (自有架构为主体)")

    return res


# ----------------------------------------------------------------------------
# 输入模板
# ----------------------------------------------------------------------------

def blank_template() -> dict:
    return {
        "goal": "用一句话描述目标需求集合 R 要满足什么",
        "requirements": [
            {"id": "R1", "statement": "关键能力示例", "priority": "must", "critical": True,
             "acceptance": "可独立验收的判据"},
            {"id": "R2", "statement": "次要能力示例", "priority": "want", "critical": False,
             "acceptance": "..."},
        ],
        "candidates": [
            {"id": "O1", "name": "候选开源项目", "url": "https://github.com/...",
             "version": "v1.2.0", "license": "MIT"},
        ],
        "matrix": {
            "O1": {
                "R1": {"coverage": 1.0, "semantic_match": 1.0, "composability": 1.0,
                       "status": "native", "evidence": "源码路径/文档章节/可复现实验", "notes": ""},
                "R2": {"coverage": 0.5, "semantic_match": 1.0, "composability": 1.0,
                       "status": "adapted", "evidence": "...", "notes": "需适配层"},
            }
        },
        "cost": {
            "O1": {"initial_dev": 0, "integration": 0, "maintenance": 0,
                   "upstream_adapt": 0, "ops": 0, "security_gov": 0}
        },
        "adaptation": {
            "O1": {"scope": ["query-adapt"], "mode": "adapter",
                   "responsibility_uncontrolled": False, "poc_plan": ""}
        },
        "poc_plan": "",
    }


# ----------------------------------------------------------------------------
# 决策记录产出
# ----------------------------------------------------------------------------

def render_decision_record(data: dict, results: list[CandidateResult]) -> str:
    lines: list[str] = []
    lines.append("# 开源能力拟合决策记录")
    lines.append("")
    lines.append(f"> 由 `zj-open-source-capability-fit` 依据 "
                 f"[开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。")
    lines.append("")
    lines.append(f"## 目标需求 R")
    lines.append("")
    lines.append(data.get("goal", ""))
    lines.append("")
    for r in data.get("requirements", []):
        tag = "关键" if is_must(r) else r.get("priority", "")
        lines.append(f"- **{r['id']}** [{tag}] {r.get('statement','')} — 验收: {r.get('acceptance','')}")
    lines.append("")

    for res in results:
        lines.append(f"## 候选 {res.cid} · {res.name} ({res.version})")
        lines.append("")
        lines.append(f"- **推荐分类**: `{res.recommended}`")
        lines.append(f"- 关键需求覆盖率: {res.must_coverage:.0%} · 平均有效拟合度: {res.avg_fit:.2f} · 总所有权成本 E: {res.total_e:.0f}")
        lines.append("")
        lines.append("### R × O 证据矩阵")
        lines.append("")
        lines.append("| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in data.get("requirements", []):
            cell = data.get("matrix", {}).get(res.cid, {}).get(r["id"], {})
            ef = effective_fit(cell)
            lines.append(f"| {r['id']} | {cell.get('status','-')} | {cell.get('coverage','-')} "
                         f"| {cell.get('semantic_match','-')} | {cell.get('composability','-')} "
                         f"| {ef:.2f} | {cell.get('evidence','')} |")
        lines.append("")
        lines.append("### 依据")
        for reason in res.reasons:
            lines.append(f"- {reason}")
        gates_fail = [g for g in res.gates if not g.ok]
        if gates_fail:
            lines.append("")
            lines.append("### ⚠ 闸门未过 (拒绝自信分类)")
            for g in gates_fail:
                lines.append(f"- {g.name}: {g.message}")
        lines.append("")

    lines.append("## 最终拍板 (Human/Agent 填)")
    lines.append("")
    lines.append("- 选定组合 C 与能力缺口 G: ___")
    lines.append("- 自有责任 E 及成本估计: ___")
    lines.append("- PoC 结论: ___")
    lines.append("- 最终分类 (A/B1/B2/B3/C/D): ___")
    lines.append("- 采用理由: ___")
    lines.append("- 主要风险: ___")
    lines.append("- 退出路径: ___")
    lines.append("- 重新评估触发条件: ___")
    lines.append("")
    lines.append("**完成标准自检**: 第三方 Agent 仅凭本记录能否复核分类依据，并区分证据 vs 假设？")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_init(args: argparse.Namespace) -> int:
    out = args.out
    with open(out, "w", encoding="utf-8") as f:
        json.dump(blank_template(), f, ensure_ascii=False, indent=2)
    print(f"已写出空白模板: {out}")
    return 0


def cmd_assess(args: argparse.Namespace) -> int:
    data = _load(args.input)
    results = [classify_candidate(data, c["id"]) for c in data.get("candidates", [])]

    if args.json:
        payload = {
            "results": [
                {"cid": r.cid, "name": r.name, "version": r.version,
                 "recommended": r.recommended, "must_coverage": r.must_coverage,
                 "avg_fit": r.avg_fit, "total_e": r.total_e,
                 "critical_gap": r.critical_gap, "forbidden_touched": r.forbidden_touched,
                 "reasons": r.reasons,
                 "gates": [{"name": g.name, "ok": g.ok, "message": g.message} for g in r.gates]}
                for r in results]
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"目标: {data.get('goal','')}")
        print("=" * 60)
        for r in results:
            print(f"[{r.cid}] {r.name} ({r.version}) -> 推荐 {r.recommended}")
            print(f"    关键覆盖 {r.must_coverage:.0%} | 平均拟合 {r.avg_fit:.2f} | E {r.total_e:.0f}"
                  f" | 关键缺口 {r.critical_gap} | 触碰主体能力 {r.forbidden_touched}")
            for reason in r.reasons:
                print(f"    - {reason}")
            failed = [g for g in r.gates if not g.ok]
            if failed:
                print("    ⚠ 闸门未过:")
                for g in failed:
                    print(f"      - {g.name}: {g.message}")
            print("-" * 60)

    if args.record:
        with open(args.record, "w", encoding="utf-8") as f:
            f.write(render_decision_record(data, results))
        print(f"决策记录已写出: {args.record}")

    # 退出码: 任一硬闸门（除 G5 外）未过 -> 1 (提醒不要盲信);
    # G5 是就绪度提示、不阻塞分类, 不影响退出码 (classify_candidate 已排除 G5)
    hard_failed = any(
        any(g.name != "G5-unknown-poc-plan" and not g.ok for g in r.gates)
        for r in results
    )
    return 1 if hard_failed else 0


def cmd_validate(args: argparse.Namespace) -> int:
    data = _load(args.input)
    ok_all = True
    for c in data.get("candidates", []):
        cid = c["id"]
        print(f"[{cid}] {c.get('name','')}")
        for g in run_gates(data, cid):
            mark = "✓" if g.ok else "✗"
            print(f"  {mark} {g.name}: {g.message}")
            ok_all = ok_all and g.ok
        print("")
    return 0 if ok_all else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="开源能力拟合决策仪器 (本仓库决策模型操作化)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="写出空白输入模板")
    pi.add_argument("--out", default="capability_fit_input.json")
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("assess", help="评估并给出推荐分类")
    pa.add_argument("--input", required=True)
    pa.add_argument("--record", default=None, help="产出决策记录 Markdown 路径")
    pa.add_argument("--json", action="store_true", help="以 JSON 输出")
    pa.set_defaults(func=cmd_assess)

    pv = sub.add_parser("validate", help="仅跑闸门")
    pv.add_argument("--input", required=True)
    pv.set_defaults(func=cmd_validate)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
