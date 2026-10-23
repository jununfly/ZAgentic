"""Local closed-loop orchestrator for the `zj-ui-*` chain.

This is the faithful reification of `ui-agent-skills-stage-engine.md §6/§8`:
the ten stages (S1..S10) are wired into one deterministic pipeline. For every
step the orchestrator (1) resolves the next action through the frozen resolver
(`ui_resolver.resolve`) and (2) only when the plan is `PLANNED` executes the
stage runner (`ui_stages.STAGES`), threading the committed canonical artifact
from the in-memory `store` into the next stage's request.

A resolver freeze or a non-OK stage result halts the chain immediately with
**zero writes** below the halt point — that is the contract's "冻结即停"
guarantee, and the reason this file exists: without a single orchestrator the
sentence "brief → … → handoff 能跑通" decays into prose.

Nothing here performs an effect: no network, no credentials, no remote write.
The `store` is an in-memory journal the caller owns.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ui_skill_core as core
import ui_stages
import ui_resolver as res
import ui_registry as reg


# --------------------------------------------------------------------------- #
# Per-stage request wiring
# --------------------------------------------------------------------------- #
#
# Each stage runner in `ui_stages` has its own request shape. This table turns a
# uniform chain request + the committed upstream artifact into the exact request
# each runner expects, so the chain never has to know the runners' internals.

def _build_runner_request(stage, chain_request, committed_artifact, committed_result, agent_inputs, root_revision):
    seed = chain_request["seed"]

    if stage == "brief":
        return {
            "candidate": seed,
            "input_revision": root_revision,
            "idempotency_key": "chain:brief",
        }

    if stage == "discover":
        brief = committed_artifact["brief"]
        disc = agent_inputs.get("discover", {})
        return {
            "brief": brief["content"],
            "brief_revision": brief["revision"],
            "evidence": disc.get("evidence", []),
            "question_budget": disc.get("question_budget", 2),
            "questions_asked": disc.get("questions_asked", 0),
            "idempotency_key": "chain:discover",
        }

    if stage == "direction":
        direction = agent_inputs["direction"]
        return {
            "cards": direction["cards"],
            "human_choice": direction.get("human_choice"),
            "brief_revision": committed_artifact["brief"]["revision"],
            "idempotency_key": "chain:direction",
        }

    if stage == "design_system":
        design = committed_artifact["direction"]
        ds = agent_inputs["design_system"]
        return {
            "design": design["content"],
            "tokens": ds.get("tokens", {}),
            "components": ds.get("components", []),
            "design_revision": design["revision"],
            "idempotency_key": "chain:design_system",
        }

    if stage == "flow":
        req = dict(agent_inputs["flow"])
        req.setdefault("input_revision", "chain:flow")
        req["idempotency_key"] = "chain:flow"
        return req

    if stage == "prototype":
        req = dict(agent_inputs["prototype"])
        req.setdefault("input_revision", "chain:prototype")
        req["idempotency_key"] = "chain:prototype"
        return req

    if stage == "visual_review":
        req = dict(agent_inputs["visual_review"])
        req.setdefault("input_revision", "chain:visual_review")
        req["idempotency_key"] = "chain:visual_review"
        return req

    if stage == "break":
        req = dict(agent_inputs["break"])
        req.setdefault("input_revision", "chain:break")
        req["idempotency_key"] = "chain:break"
        return req

    if stage == "verify":
        req = dict(agent_inputs["verify"])
        req.setdefault("input_revision", "chain:verify")
        req["idempotency_key"] = "chain:verify"
        return req

    if stage == "handoff":
        ho = agent_inputs["handoff"]
        # `receipt` is the verify *result* (it carries `status`); consistent with
        # the single-stage FF-HO-01 fixture convention.
        return {
            "candidate": ho["candidate"],
            "receipt": committed_result["verify"],
            "input_revision": ho.get("input_revision", "chain:handoff"),
            "idempotency_key": "chain:handoff",
        }

    raise ValueError(f"unknown stage {stage!r}")


# --------------------------------------------------------------------------- #
# The orchestrator
# --------------------------------------------------------------------------- #


def run_chain(chain_request: dict, registry: list | None = None) -> dict:
    """Drive the ten stages end-to-end. Returns the chain outcome.

    `chain_request` shape:
        {
          "request_id": str,
          "gate_state": "APPROVED" | "PENDING" | ...   # default APPROVED
          "root_revision": str,                         # seed provenance
          "seed": { ...brief candidate... },            # S1 input
          "agent_inputs": {                             # per-stage creative payload
             "discover": {"evidence": [...], ...},
             "direction": {"cards": [...], "human_choice": "id"},
             "design_system": {"tokens": {...}, "components": [...]},
             "flow": {"candidate": {...}, ...},
             "prototype": {"candidate": {...}, ...},
             "visual_review": {"candidate": {...}, ...},
             "break": {"candidate": {...}, ...},
             "verify": {"candidate": {...}, ...},
             "handoff": {"candidate": {...}}
          }
        }
    """
    registry = reg.get_registry() if registry is None else registry
    store: dict = {}
    gate_state = chain_request.get("gate_state", res.GATE_APPROVED)
    root_revision = chain_request.get("root_revision") or "seed-rev"
    agent_inputs = chain_request.get("agent_inputs", {})

    steps = []
    committed_artifact: dict = {}
    committed_result: dict = {}
    chain_status = "OK"
    chain_reason = "全链闭环到 handoff（十阶段全部 PLANNED→OK）"
    stopped_at = None

    for index, stage in enumerate(reg.CHAIN_ORDER):
        # The artifact the stage reads from the previous step, used for resolver
        # determinism (route_fingerprint / plan_hash). Pure input, never mutated.
        prev = reg.CHAIN_ORDER[index - 1] if index > 0 else None
        artifact_snapshot = committed_artifact.get(prev) or {}

        request = _build_runner_request(
            stage, chain_request, committed_artifact, committed_result, agent_inputs, root_revision
        )

        # (1) Resolve before executing. A frozen plan permits zero skill calls.
        plan = res.resolve(request, artifact_snapshot, registry, gate_state, target_stage=stage)
        if plan["status"] != res.PLANNED:
            steps.append({"stage": stage, "plan": plan, "result": None, "writes": 0})
            chain_status = "FROZEN"
            chain_reason = f"{stage} resolver 冻结（{plan['status']}）：{plan['reason']}；下游零写入"
            stopped_at = stage
            break

        # (2) Execute only the resolved owner's runner.
        runner = ui_stages.STAGES[stage]
        result = runner(request, store)
        steps.append({"stage": stage, "plan": plan, "result": result, "writes": result.get("writes", 0)})

        if result["status"] != core.OK:
            chain_status = "STOPPED"
            chain_reason = f"{stage} 返回 {result['status']}：{result.get('reason')}；下游零写入"
            stopped_at = stage
            break

        artifact = result.get("artifact")
        if artifact is not None:
            committed_artifact[stage] = artifact
        committed_result[stage] = result

    return {
        "chain_status": chain_status,
        "stopped_at": stopped_at,
        "chain_reason": chain_reason,
        "gate_state": gate_state,
        "steps": steps,
        "produced_artifacts": [
            a["artifact_kind"] for a in committed_artifact.values() if a is not None
        ],
        "plan_hashes": [s["plan"]["plan_hash"] for s in steps if s["plan"]["plan_hash"]],
        "total_writes": sum(s["writes"] for s in steps),
    }


# --------------------------------------------------------------------------- #
# Optional CLI: run a chain fixture directory for manual inspection
# --------------------------------------------------------------------------- #


def _load(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: python ui_chain.py <chain-fixture-dir>")
        return 2
    directory = pathlib.Path(argv[1])
    chain_request = _load(directory / "input.json")
    outcome = run_chain(chain_request)
    print(json.dumps(outcome, indent=2, ensure_ascii=False, default=str))
    return 0 if outcome["chain_status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
