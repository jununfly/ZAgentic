"""Shared golden-diff / version-drift detection harness for F-A2 (node 1-7-4-4).

Implements the `F-A2-JR-DRIFT` spec (see
``tests/ui-agent-skills/fixtures/adapters/F-A2/json-render/drift-harness.spec.json``):

* **version_drift** — ``pin.version`` / ``pin.source_commit`` (anchor) or top-level
  ``pin_version`` (expected.json) changes → **report only, never hard fail**.
* **semantic_loss** — candidate drops or alters fields inside the semantic regions
  (``projection``, ``semantic_equivalence``, ``validation``) → **hard fail**.
* **unknown_regression** — any unknown-handling flag
  (``unknown_preserved`` / ``unknown_not_dropped`` / ``unknown_not_empty`` /
  ``deviation_flagged`` / ``warning_emitted``) regresses ``true -> false`` → **hard fail**.

The harness is pure-python and dependency-free so it runs in the same unittest
suite as the other ``tests/test_ui_agent_skills_*.py`` modules. A CLI entrypoint
(``python ui_agent_skills_drift_harness.py ...``) emits a JSON report and uses the
exit code ``0`` for ``ok`` / ``drift_only`` and ``1`` for ``fail``.
"""

import copy
import json
import sys

# Regions whose field-level diff defines *semantic loss* (not additive churn).
SEMANTIC_REGIONS = ("projection", "semantic_equivalence", "validation")

# Flags describing canonical->adapter unknown-field handling; any true->false
# regression is a hard-fail signal.
UNKNOWN_FLAGS = (
    "unknown_preserved",
    "unknown_not_dropped",
    "unknown_not_empty",
    "deviation_flagged",
    "warning_emitted",
)


def field_diff(baseline, candidate, path="$"):
    """Recursive field-level diff.

    Returns a list of diff records:
        {"op": "remove"|"add"|"change", "path", "baseline", "candidate"}
    ``remove`` / ``change`` in a semantic region constitute *semantic loss*;
    ``add`` is treated as additive churn (not loss).
    """
    diffs = []
    if isinstance(baseline, dict) and isinstance(candidate, dict):
        for key in baseline:
            child = f"{path}.{key}"
            if key not in candidate:
                diffs.append({"op": "remove", "path": child,
                              "baseline": baseline[key], "candidate": None})
            else:
                diffs.extend(field_diff(baseline[key], candidate[key], child))
        for key in candidate:
            if key not in baseline:
                child = f"{path}.{key}"
                diffs.append({"op": "add", "path": child,
                              "baseline": None, "candidate": candidate[key]})
    elif isinstance(baseline, list) and isinstance(candidate, list):
        if baseline != candidate:
            diffs.append({"op": "change", "path": path,
                          "baseline": baseline, "candidate": candidate})
    else:
        if baseline != candidate:
            diffs.append({"op": "change", "path": path,
                          "baseline": baseline, "candidate": candidate})
    return diffs


def _anchor_versions(pin):
    """Extract (version, source_commit) from an anchor dict, tolerant of layout."""
    if not pin:
        return None, None
    if isinstance(pin.get("pin"), dict):
        p = pin["pin"]
        return p.get("version"), p.get("source_commit")
    return pin.get("version") or pin.get("pin_version"), pin.get("source_commit")


def detect_version_drift(baseline_expected, candidate_expected,
                        pin_baseline=None, pin_candidate=None):
    """Compare version anchors. Report-only signal (never a hard fail)."""
    bv_exp = baseline_expected.get("pin_version")
    cv_exp = candidate_expected.get("pin_version")
    bv_pin, bc = _anchor_versions(pin_baseline)
    cv_pin, cc = _anchor_versions(pin_candidate)

    version_changed = (bv_exp != cv_exp) or (bv_pin != cv_pin)
    commit_changed = (bc != cc) and (bc is not None) and (cc is not None)
    detected = bool(version_changed or commit_changed)

    # Prefer the anchor version when an anchor is supplied (it is the
    # authoritative pin); fall back to the expected.json top-level pin_version.
    baseline_version = bv_pin if pin_baseline is not None else bv_exp
    candidate_version = cv_pin if pin_candidate is not None else cv_exp

    return {
        "detected": detected,
        "baseline_version": baseline_version,
        "candidate_version": candidate_version,
        "baseline_source_commit": bc,
        "candidate_source_commit": cc,
    }


def detect_semantic_loss(baseline, candidate):
    """Field-level diff over the semantic regions.

    Semantic loss = any ``remove`` or ``change`` op in those regions. Pure
    additions are reported but do not count as loss.
    """
    diffs = []
    for region in SEMANTIC_REGIONS:
        if region not in baseline and region not in candidate:
            continue
        diffs.extend(field_diff(baseline.get(region, {}),
                               candidate.get(region, {}),
                               f"$.{region}"))
    loss_diffs = [d for d in diffs if d["op"] in ("remove", "change")]
    return {"detected": len(loss_diffs) > 0, "diffs": diffs,
            "loss_diffs": loss_diffs}


def detect_unknown_regression(baseline, candidate):
    """Unknown-handling flags regressing true->false are a hard-fail signal."""
    regressed = []
    for flag in UNKNOWN_FLAGS:
        b = baseline.get(flag)
        c = candidate.get(flag)
        if b is True and c is not True:
            regressed.append({"flag": flag, "baseline": b, "candidate": c})
    return {"detected": len(regressed) > 0, "regressed": regressed}


def compare(baseline, candidate, pin_baseline=None, pin_candidate=None):
    """Run the full harness and return a report dict.

    Verdict:
        "fail"        - semantic loss OR unknown regression (hard fail)
        "drift_only"  - version drift detected, no loss/regression
        "ok"          - nothing detected
    """
    version_drift = detect_version_drift(baseline, candidate, pin_baseline, pin_candidate)
    semantic_loss = detect_semantic_loss(baseline, candidate)
    unknown_regression = detect_unknown_regression(baseline, candidate)

    if semantic_loss["detected"] or unknown_regression["detected"]:
        verdict = "fail"
    elif version_drift["detected"]:
        verdict = "drift_only"
    else:
        verdict = "ok"

    return {
        "verdict": verdict,
        "version_drift": version_drift,
        "semantic_loss": semantic_loss,
        "unknown_regression": unknown_regression,
    }


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_on_files(baseline_expected_path, candidate_expected_path,
                baseline_anchor_path=None, candidate_anchor_path=None):
    """Convenience: load fixtures + anchors and run ``compare``."""
    baseline = _load(baseline_expected_path)
    candidate = _load(candidate_expected_path)
    pin_b = _load(baseline_anchor_path) if baseline_anchor_path else None
    pin_c = _load(candidate_anchor_path) if candidate_anchor_path else None
    return compare(baseline, candidate, pin_b, pin_c)


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(description="F-A2 golden-diff / drift harness")
    parser.add_argument("baseline_expected")
    parser.add_argument("candidate_expected")
    parser.add_argument("--baseline-anchor", default=None)
    parser.add_argument("--candidate-anchor", default=None)
    args = parser.parse_args(argv[1:])
    report = run_on_files(args.baseline_expected, args.candidate_expected,
                          args.baseline_anchor, args.candidate_anchor)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["verdict"] in ("ok", "drift_only") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
