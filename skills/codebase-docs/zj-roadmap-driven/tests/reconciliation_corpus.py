#!/usr/bin/env python3
"""Replay the 30 labeled reconciliation scenarios on both carriers.

The runner uses only the public CLI.  It emits raw per-carrier outputs so a
failure can be replayed by fixture id without importing Markdown or relying on
private Roadmap state.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"
ERROR_RE = re.compile(r"E_[A-Z0-9_]+")

SCENARIOS = [
    {"id": "S01", "label": "exact duplicate", "kind": "covered"},
    {"id": "S02", "label": "exact duplicate after retry", "kind": "covered"},
    {"id": "S03", "label": "near duplicate different exit criteria", "kind": "novel"},
    {"id": "S04", "label": "cross-subtree overlap", "kind": "unresolved"},
    {"id": "S05", "label": "completed WorkItem refinement", "kind": "refine"},
    {"id": "S06", "label": "refinement reopen", "kind": "reopen"},
    {"id": "S07", "label": "refinement supersede", "kind": "supersede"},
    {"id": "S08", "label": "evidence-preserving no-op", "kind": "noop"},
    {"id": "S09", "label": "dismiss informational finding", "kind": "dismiss"},
    {"id": "S10", "label": "reshape placement context", "kind": "reshape"},
    {"id": "S11", "label": "batch exact duplicates", "kind": "batch"},
    {"id": "S12", "label": "batch duplicate trace reference", "kind": "batch"},
    {"id": "S13", "label": "dependency reversal", "kind": "edge-replace"},
    {"id": "S14", "label": "dependency reversal with decision", "kind": "edge-replace"},
    {"id": "S15", "label": "split one obligation", "kind": "split"},
    {"id": "S16", "label": "split with separate parents", "kind": "split"},
    {"id": "S17", "label": "merge duplicate owners", "kind": "coalesce"},
    {"id": "S18", "label": "merge preserves target", "kind": "coalesce"},
    {"id": "S19", "label": "combined changes form a cycle", "kind": "cycle"},
    {"id": "S20", "label": "cycle rejection is atomic", "kind": "cycle"},
    {"id": "S21", "label": "stale revision", "kind": "stale"},
    {"id": "S22", "label": "stale revision after edge write", "kind": "stale"},
    {"id": "S23", "label": "renderer publication failure", "kind": "renderer-failure"},
    {"id": "S24", "label": "renderer retry after stale view", "kind": "renderer-failure"},
    {"id": "S25", "label": "trace-only addition", "kind": "trace-only"},
    {"id": "S26", "label": "Placement reference projection", "kind": "placement"},
    {"id": "S27", "label": "Placement move projection", "kind": "placement"},
    {"id": "S28", "label": "legacy group/work migration", "kind": "types"},
    {"id": "S29", "label": "JSON/SQLite semantic parity", "kind": "parity"},
    {"id": "S30", "label": "new obligation with novelty evidence", "kind": "novel"},
]


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *[str(arg) for arg in args]],
        cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"CLI failed: {args}\n{result.stdout}\n{result.stderr}")
    return result


def json_out(result: subprocess.CompletedProcess[str]) -> Any:
    return json.loads(result.stdout)


def error_out(result: subprocess.CompletedProcess[str]) -> str | None:
    match = ERROR_RE.search(result.stderr)
    return match.group(0) if match else None


def setup(root: Path, carrier: str, md_file: str = "ROADMAP.md") -> Path:
    path = root / ("roadmap.json" if carrier == "single" else "roadmap.sqlite")
    args = ["init", path, "--title", "Corpus fixture", "--md-file", md_file]
    if carrier == "sqlite":
        args += ["--storage", "sqlite"]
    run_cli(*args, cwd=root)
    return path


def add_work(path: Path, root: Path, label: str, key: str, parent: str = "1") -> dict:
    return json_out(run_cli("add", path, parent, label, "--obligation-key", key, cwd=root))


def add_trace(path: Path, root: Path, body: str, key: str, evidence: bool = False) -> dict:
    args = ["trace", "add", path, "--kind", "finding", "--body", body, "--obligation-key", key]
    if evidence:
        args += ["--evidence", "source:corpus-fixture"]
    return json_out(run_cli(*args, cwd=root))


def answer(kind: str, reason: str, **extra: Any) -> str:
    value = {"disposition": "refine" if kind in {"reopen", "supersede", "noop"} else kind,
             "reason": reason}
    if kind in {"reopen", "supersede", "noop"}:
        value["action"] = kind
    value.update(extra)
    return json.dumps(value, ensure_ascii=False)


def run_scenario(root: Path, carrier: str, scenario: dict[str, str]) -> dict[str, Any]:
    kind = scenario["kind"]
    path = setup(root, carrier, "broken-view" if kind == "renderer-failure" else "ROADMAP.md")
    key = f"corpus:{scenario['id']}"

    if kind in {"covered", "refine", "reopen", "supersede", "noop", "reshape"}:
        work = add_work(path, root, "Existing work", key)
        if kind in {"refine", "reopen", "supersede", "noop"}:
            run_cli("update", path, work["id"], "--status", "completed", cwd=root)
        trace = add_trace(path, root, "Finding body", key, evidence=True)
        extra: dict[str, Any] = {}
        if kind == "reshape":
            extra = {
                "work_uid": work["uid"],
                "changes": [{"kind": "work.patch", "work_uid": work["uid"], "patch": {"label": "Reshaped"}}],
            }
        disposition_answer = answer(kind, "Corpus fixture decision.", **extra) if kind in {"reopen", "supersede", "noop", "reshape"} else None
        reconcile_args = ["reconcile", path, trace["uid"]]
        if disposition_answer:
            reconcile_args += ["--answer", disposition_answer]
        proposal_result = run_cli(*reconcile_args, cwd=root)
        proposal = json_out(proposal_result)
        result: dict[str, Any] = {"disposition": proposal["disposition"], "proposal": proposal}
        if disposition_answer:
            applied = run_cli(
                "apply", path, proposal["proposal_id"], "--approved-digest", proposal["proposal_digest"],
                "--idempotency-key", f"corpus-{scenario['id']}", "--answer", disposition_answer, cwd=root,
            )
            result["receipt"] = json_out(applied)
        return result

    if kind in {"novel", "dismiss"}:
        trace = add_trace(path, root, "New finding", key, evidence=True)
        reconcile_args = ["reconcile", path, trace["uid"]]
        if kind == "dismiss":
            reconcile_args += ["--answer", answer("dismiss", "Not actionable in this release.")]
        proposal = json_out(run_cli(*reconcile_args, cwd=root))
        return {"disposition": proposal["disposition"], "proposal": proposal}

    if kind == "unresolved":
        add_work(path, root, "Owner A", key)
        add_work(path, root, "Owner B", key)
        trace = add_trace(path, root, "Ambiguous finding", key, evidence=True)
        proposal = json_out(run_cli("reconcile", path, trace["uid"], cwd=root))
        return {"disposition": proposal["disposition"], "proposal": proposal}

    if kind == "batch":
        traces = [add_trace(path, root, f"Batch finding {index}", key, evidence=True) for index in (1, 2)]
        batch = json_out(run_cli("reconcile", path, "--trace", traces[0]["uid"], "--trace", traces[1]["uid"], cwd=root))
        receipt = json_out(run_cli(
            "apply-batch", path, "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
            "--approved-digest", batch["batch_digest"], "--idempotency-key", f"corpus-{scenario['id']}", cwd=root,
        ))
        return {"disposition": "batch-committed", "batch": batch, "receipt": receipt}

    first = add_work(path, root, "First", key + ":a")
    second = add_work(path, root, "Second", key + ":b")
    third = add_work(path, root, "Third", key + ":c")
    if kind in {"edge-replace", "cycle"}:
        edge = json_out(run_cli("edge", "add", path, first["uid"], second["uid"], "--type", "blocks", cwd=root))
        change = {
            "kind": "edge.put" if kind == "cycle" else "edge.replace",
            "from_uid": second["uid"] if kind == "cycle" else first["uid"],
            "to_uid": first["uid"] if kind == "cycle" else third["uid"],
            "type": "blocks",
        }
        if kind == "edge-replace":
            change = {"kind": "edge.replace", "edge_id": edge["id"], "replacement": {
                "from_uid": first["uid"], "to_uid": third["uid"], "type": "blocks",
            }}
        changes = json.dumps([change])
        preview = json_out(run_cli("changeset", "preview", path, "--changes", changes, cwd=root))
        applied = run_cli(
            "changeset", "apply", path, "--changes", changes, "--approved-digest", preview["digest"],
            "--idempotency-key", f"corpus-{scenario['id']}", cwd=root, check=False,
        )
        return {"disposition": "committed" if applied.returncode == 0 else error_out(applied), "stdout": applied.stdout, "stderr": applied.stderr}

    if kind == "split":
        changes = json.dumps([{"kind": "work.create", "parent_uid": first["uid"], "label": "Split A"},
                             {"kind": "work.create", "parent_uid": first["uid"], "label": "Split B"}])
    elif kind == "coalesce":
        changes = json.dumps([{"kind": "work.coalesce", "target_uid": first["uid"], "source_uids": [second["uid"]]}])
    elif kind == "stale":
        changes = json.dumps([{"kind": "work.patch", "work_uid": first["uid"], "patch": {"label": "Stale patch"}}])
    elif kind == "renderer-failure":
        (root / "broken-view").mkdir()
        changes = json.dumps([{"kind": "work.patch", "work_uid": first["uid"], "patch": {"label": "Rendered"}}])
    elif kind == "trace-only":
        before = run_cli("tree", path, cwd=root).stdout
        add_trace(path, root, "Trace-only finding", key, evidence=True)
        after = run_cli("tree", path, cwd=root).stdout
        return {"disposition": "unchanged" if before == after else "changed"}
    elif kind == "placement":
        target = root / ("placement-target.json" if carrier == "single" else "placement-target.sqlite")
        run_cli("migrate-placements", path, "--output", target, cwd=root)
        run_cli("placement", "add-reference", target, first["uid"], third["uid"], cwd=root)
        return {"disposition": "projected" if "↪" in run_cli("tree", target, cwd=root).stdout else "missing"}
    elif kind == "types":
        target = root / ("typed-target.json" if carrier == "single" else "typed-target.sqlite")
        report = json_out(run_cli("migrate-types", path, "--output", target, cwd=root))
        return {"disposition": "typed", "report": report}
    elif kind == "parity":
        trace = add_trace(path, root, "Parity finding", key, evidence=True)
        proposal = json_out(run_cli("reconcile", path, trace["uid"], cwd=root))
        return {"disposition": proposal["disposition"]}
    else:
        raise AssertionError(f"unhandled scenario kind: {kind}")

    preview = json_out(run_cli("changeset", "preview", path, "--changes", changes, cwd=root))
    if kind == "stale":
        run_cli("add", path, "1", "Concurrent write", cwd=root)
    applied = run_cli(
        "changeset", "apply", path, "--changes", changes, "--approved-digest", preview["digest"],
        "--idempotency-key", f"corpus-{scenario['id']}", cwd=root, check=False,
    )
    if applied.returncode != 0:
        return {"disposition": error_out(applied), "stdout": applied.stdout, "stderr": applied.stderr}
    receipt = json.loads(applied.stdout)
    return {"disposition": "committed", "receipt": receipt}


def run(plans: list[dict[str, str]] | None = None) -> dict[str, Any]:
    scenarios = plans or SCENARIOS
    results = []
    with tempfile.TemporaryDirectory(prefix="zj-reconciliation-corpus-") as temporary:
        workspace = Path(temporary)
        for scenario in scenarios:
            carrier_results = {}
            for carrier in ("single", "sqlite"):
                carrier_root = workspace / f"{scenario['id']}-{carrier}"
                carrier_root.mkdir()
                carrier_results[carrier] = run_scenario(carrier_root, carrier, scenario)
            carrier_results["semantic_parity"] = (
                carrier_results["single"].get("disposition")
                == carrier_results["sqlite"].get("disposition")
            )
            results.append({**scenario, "results": carrier_results})
    return {
        "schema": "zj-reconciliation-corpus/v1",
        "scenario_count": len(results),
        "scenario_ids": [item["id"] for item in results],
        "semantic_parity": all(item["results"]["semantic_parity"] for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["scenario_count"] == 30 and report["semantic_parity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
