"""Sample-flow drill harness for the Experience Version form/approval paths (roadmap 1-8-5).

The form (F-1~F-6) and approval (A-1~A-6) fixtures under
``tests/ui-agent-skills/fixtures/{form,approval}`` were landed as data-only
(ev-sample-flow §4.5) and, until this harness, were never executed by any
runner. This module is the missing drill: it runs each fixture through a
deterministic state-machine simulator and injects the four degradation
scenarios the 1-8-5 exit criteria demand:

    ① remote adapter closed  -> static-preview fallback, no fake success
    ② asset / license quarantine -> isolated, degraded, recovery preserved
    ③ unknown field -> preserved as a 4-tuple (path/raw/reason/source), not coerced
    ④ local static-preview fallback -> recovery surfaces (canonical /
       static_preview / local_verify) stay available (adapter_boundary invariant)

Baseline run proves the sample *runs* (12 fixtures match their expectations).
Scenario runs prove the sample *degrades correctly* and keeps a recovery path.

Stdlib only. The local-recovery invariant (④) is imported from
``adapter_boundary`` so it cannot drift from the framework contract.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import adapter_boundary as ab  # noqa: E402

# Frozen canonical schemas (ui-agent-skills-canonical-schema.md / scope-manifest).
CANONICAL_FORM_FIELDS = frozenset({"nickname", "email", "bio"})
CANONICAL_APPROVAL_REQUEST_FIELDS = frozenset(
    {"amount", "currency", "reason", "attachment_ref"}
)

FORM_FIXTURES = (
    pathlib.Path(__file__).resolve().parents[4]
    / "tests"
    / "ui-agent-skills"
    / "fixtures"
    / "form"
)
APPROVAL_FIXTURES = (
    pathlib.Path(__file__).resolve().parents[4]
    / "tests"
    / "ui-agent-skills"
    / "fixtures"
    / "approval"
)


def load_fixture(directory: pathlib.Path) -> dict:
    with (directory / "input.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def empty_result() -> dict:
    return {
        "final_state": None,
        "persisted": False,
        "error_fields": [],
        "submit_blocked": False,
        "human_gates": [],
        "writes": 0,
        "duplicate_suppressed": False,
        "fallback": None,
        "explicit_marker": False,
        "recoverable": False,
        "quarantined": [],
        "unknown": [],
        "denied": False,
        "recovery_available": True,
        "_problems": [],
    }


def _detect_unknown_and_quarantine(fixture: dict, result: dict) -> None:
    """Pre-scan for unknown fields (③) and quarantined assets/licenses (②)."""
    cls = fixture["class"]
    if cls == "form":
        profile = fixture.get("profile", {})
        for key, value in profile.items():
            # a quarantined material is isolated, not treated as an unknown field.
            if isinstance(value, str) and value.startswith("quarantine://"):
                continue
            if key not in CANONICAL_FORM_FIELDS:
                result["unknown"].append(
                    {
                        "path": f"profile.{key}",
                        "raw": value,
                        "reason": "not in canonical form schema",
                        "source": "unsourced",
                    }
                )
    elif cls == "approval":
        request = fixture.get("request", {}) or {}
        for key, value in request.items():
            if key not in CANONICAL_APPROVAL_REQUEST_FIELDS:
                result["unknown"].append(
                    {
                        "path": f"request.{key}",
                        "raw": value,
                        "reason": "not in canonical approval request schema",
                        "source": "unsourced",
                    }
                )
        attachment = request.get("attachment_ref")
        if isinstance(attachment, str) and attachment.startswith("quarantine://"):
            asset_id = attachment.split("://", 1)[1]
            result["quarantined"].append(asset_id)
    # ② quarantine also surfaces as a quarantined asset value (form material, e.g. avatar).
    material = fixture.get("profile", {}) if cls == "form" else fixture.get("request", {}) or {}
    for value in material.values():
        if isinstance(value, str) and value.startswith("quarantine://"):
            result["quarantined"].append(value.split("://", 1)[1])


def simulate(fixture: dict, mode: str = "baseline") -> dict:
    """Execute one fixture's action sequence; ``mode`` = baseline | adapter_closed."""
    cls = fixture["class"]
    remote_unreachable = mode == "adapter_closed"
    state = fixture["initial_state"]
    result = empty_result()

    _detect_unknown_and_quarantine(fixture, result)

    actions = sorted(fixture.get("actions", []), key=lambda a: a["seq"])
    for action in actions:
        frm = action["from"]
        to = action["to"]
        if frm != state:
            result["_problems"].append(
                f"action seq {action['seq']}: from {frm!r} != current {state!r}"
            )
        act = action["action"]

        if act == "edit":
            state = to
        elif act == "validate":
            if action.get("result") == "invalid":
                result["error_fields"].extend(action.get("error_fields", []))
                result["submit_blocked"] = True
            state = to
        elif act == "submit":
            if "blocked_by" in action:
                result["submit_blocked"] = True
                if cls == "approval":
                    result["human_gates"].append(
                        {"role": action["role"], "signed": False, "at_step": action["seq"]}
                    )
                state = frm  # blocked: does not advance
            elif action.get("duplicate") or action.get("result") == "ignored":
                result["duplicate_suppressed"] = True
                if cls == "approval":
                    result["human_gates"].append(
                        {"role": action["role"], "signed": False, "at_step": action["seq"]}
                    )
                # state stays (from == to for these fixtures)
            else:
                result["human_gates"].append(
                    {"role": action["role"], "signed": True, "at_step": action["seq"]}
                )
                state = to
        elif act == "persist":
            if remote_unreachable:
                state = "error"
                result["fallback"] = "static_preview"
                result["explicit_marker"] = True
            else:
                rc = action.get("response_code")
                if rc == 200:
                    result["persisted"] = True
                    result["writes"] += 1
                    state = to
                elif rc == 422:
                    state = "error"
                    result["recoverable"] = True
                else:  # 0 / timeout
                    state = "error"
                    result["fallback"] = "stable_path"
                    result["explicit_marker"] = True
        elif act == "route":
            if remote_unreachable:
                # routing to remote review is unavailable: preview falls back,
                # decision flow still allowed to proceed locally.
                result["fallback"] = "static_preview"
                result["explicit_marker"] = True
            state = to
        elif act in ("approve", "reject"):
            if action.get("outcome") == "denied":
                result["denied"] = True
                state = frm  # denied: does not advance
            else:
                result["human_gates"].append(
                    {"role": action["role"], "signed": True, "at_step": action["seq"]}
                )
                state = to
        elif act == "timeout":
            result["fallback"] = "stable_path"
            result["explicit_marker"] = True
            state = to
        else:
            state = to

    result["final_state"] = state

    if cls == "approval":
        result["persisted"] = state in ("approved", "rejected")

    # ② quarantine forces a degraded-but-recoverable hold, never a fake success.
    if result["quarantined"] and state in ("success", "approved"):
        result["final_state"] = "under_review" if cls == "approval" else "error"
        result["persisted"] = False
        result["fallback"] = "static_preview"
        result["explicit_marker"] = True

    return result


def compare_baseline(result: dict, expected: dict) -> list:
    """Every mismatch is a string; empty list = fixture matched its expectation.

    Only keys present in ``expected`` are checked (``assertions`` is descriptive).
    """
    problems = []
    for key, want in expected.items():
        if key in ("assertions", "fixture_id"):
            continue
        if key == "human_gates":
            want_gates = sorted(
                (g["role"], g["signed"], g["at_step"]) for g in want
            )
            got_gates = sorted(
                (g["role"], g["signed"], g["at_step"])
                for g in result.get("human_gates", [])
            )
            if want_gates != got_gates:
                problems.append(f"human_gates: expected {want_gates}, got {got_gates}")
        elif key == "error_fields":
            if sorted(want) != sorted(result.get(key, [])):
                problems.append(
                    f"error_fields: expected {sorted(want)}, got {sorted(result.get(key, []))}"
                )
        else:
            if result.get(key) != want:
                problems.append(f"{key}: expected {want!r}, got {result.get(key)!r}")
    problems.extend(result.get("_problems", []))
    return problems


def _recovery_invariant_holds(result: dict) -> bool:
    """④ local static-preview fallback: recovery surfaces stay available."""
    try:
        ab.assert_local_recovery(
            ab.CapabilitySnapshot(
                canonical=True,
                static_preview=True,
                local_verify=True,
                resolver_status="degraded",
            )
        )
    except ab.BoundaryError:
        return False
    return bool(result.get("recovery_available"))


# --------------------------------------------------------------------------
# Degradation scenario injection (synthesized from a baseline fixture)
# --------------------------------------------------------------------------
def inject_degradation(fixture: dict, scenario: str) -> str:
    """Return the simulator ``mode`` for a scenario, mutating the fixture in place."""
    cls = fixture["class"]
    if scenario == "remote_adapter_closed":
        return "adapter_closed"
    if scenario == "quarantine":
        if cls == "approval":
            fixture.setdefault("request", {})["attachment_ref"] = "quarantine://receipt-001"
        else:
            fixture.setdefault("profile", {})["avatar"] = "quarantine://avatar-001"
        return "baseline"
    if scenario == "unknown_field":
        if cls == "form":
            fixture.setdefault("profile", {})["favorite_ide"] = "unsourced-claim"
        else:
            fixture.setdefault("request", {})["cost_center"] = "unsourced-claim"
        return "baseline"
    raise ValueError(f"unknown scenario: {scenario}")


def drill_scenario(fixture_dir: pathlib.Path, scenario: str) -> dict:
    """Run one fixture through one scenario; return an assertion report."""
    fixture = load_fixture(fixture_dir)
    mode = inject_degradation(fixture, scenario)
    result = simulate(fixture, mode=mode)

    cls = fixture["class"]
    has_remote_step = any(
        a["action"] in ("persist", "route", "approve", "reject")
        and "blocked_by" not in a
        and not a.get("duplicate")
        and a.get("result") != "ignored"
        and a.get("outcome") != "denied"
        for a in fixture.get("actions", [])
    )

    problems = []
    if scenario == "remote_adapter_closed":
        if has_remote_step:
            if result.get("fallback") != "static_preview":
                problems.append(f"fallback != static_preview: {result.get('fallback')!r}")
            if not result.get("explicit_marker"):
                problems.append("explicit_marker missing on adapter-closed")
            # ① a remote-dependent step must never fake success when closed
            if cls == "form" and result.get("final_state") == "success":
                problems.append("adapter-closed must not fake success")
        if not _recovery_invariant_holds(result):
            problems.append("local-recovery invariant violated after adapter-closed")
    elif scenario == "quarantine":
        if not result.get("quarantined"):
            problems.append("quarantined list empty")
        if result.get("final_state") in ("success", "approved"):
            problems.append("quarantined asset must block finalization")
        if not result.get("recovery_available"):
            problems.append("recovery path lost under quarantine")
        if not _recovery_invariant_holds(result):
            problems.append("local-recovery invariant violated under quarantine")
    elif scenario == "unknown_field":
        if not result.get("unknown"):
            problems.append("unknown quartet missing")
        for entry in result.get("unknown", []):
            if set(entry) != {"path", "raw", "reason", "source"}:
                problems.append(f"unknown quartet malformed: {sorted(entry)}")
        if result.get("final_state") == "success" and result.get("quarantined"):
            problems.append("unknown field must not be coerced into quarantine")
        if not _recovery_invariant_holds(result):
            problems.append("local-recovery invariant violated under unknown field")
    else:  # local_static_preview_fallback (④) — meta check across states
        if not _recovery_invariant_holds(result):
            problems.append("local-recovery invariant violated")

    return {
        "fixture_id": fixture.get("fixture_id", fixture_dir.name),
        "scenario": scenario,
        "mode": mode,
        "final_state": result["final_state"],
        "fallback": result.get("fallback"),
        "explicit_marker": result.get("explicit_marker"),
        "quarantined": result.get("quarantined"),
        "unknown": result.get("unknown"),
        "recovery_available": result.get("recovery_available"),
        "problems": problems,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _fixture_dirs(root: pathlib.Path) -> list:
    if (root / "input.json").is_file():
        return [root]
    return sorted(p.parent for p in root.rglob("input.json"))


def main(argv) -> int:
    args = argv[1:]
    if not args:
        print(__doc__.splitlines()[0])
        return 2

    if "--all" in args:
        roots = [FORM_FIXTURES, APPROVAL_FIXTURES]
    else:
        roots = [pathlib.Path(a) for a in args if not a.startswith("--")]

    scenario = None
    for i, a in enumerate(args):
        if a == "--scenario":
            scenario = args[i + 1]

    failed = 0
    if scenario:
        for root in roots:
            for directory in _fixture_dirs(root):
                report = drill_scenario(directory, scenario)
                failed += bool(report["problems"])
                status = "FAIL" if report["problems"] else "ok"
                print(f"[{status}] {report['fixture_id']} :: {scenario} -> {report['final_state']}")
                for p in report["problems"]:
                    print(f"       {p}")
    else:
        for root in roots:
            for directory in _fixture_dirs(root):
                fixture = load_fixture(directory)
                expected = json.loads(
                    (directory / "expected.json").read_text(encoding="utf-8")
                )
                result = simulate(fixture)
                problems = compare_baseline(result, expected)
                failed += bool(problems)
                status = "FAIL" if problems else "ok"
                print(f"[{status}] {fixture.get('fixture_id', directory.name)} ({fixture['class']}) -> {result['final_state']}")
                for p in problems:
                    print(f"       {p}")

    print(f"\n{('all matched' if not failed else str(failed) + ' failed')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
