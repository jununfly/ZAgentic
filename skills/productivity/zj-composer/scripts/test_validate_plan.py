#!/usr/bin/env python3
"""CLI-seam tests for Composer Plan validation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("validate_plan.py")
REPO_ROOT = SCRIPT.parents[4]
SNAPSHOT_SCHEMA = "zj-composer/catalog-snapshot/v1"
DISCOVERY_SCHEMA = "zj-composer/catalog-discovery/v1"
TEMPLATE_SCHEMA = "zj-composer/template-versions/v1"


def empty_snapshot(path: Path, root: Path) -> None:
    manifest: list[dict[str, object]] = []
    encoded = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_id": f"catalog-v1-{digest}",
        "generated_at": "2026-10-19T00:00:00Z",
        "source": {
            "skills_root": str(root.resolve()),
            "layout": "installed-flat",
            "content_digest": digest,
            "files": manifest,
            "discovery_schema": DISCOVERY_SCHEMA,
        },
        "catalog": {"skills": []},
        "metadata_warnings": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def minimal_plan(snapshot_id: str) -> str:
    return f"""# Composer Plan

## Identity

- **plan_id:** `flat-validator-fixture`
- **title:** Flat validator fixture
- **status:** `planned`
- **template_version:** `1`
- **generated_at:** 2026-10-19T00:00:00Z
- **composer_version:** `zj-composer/v1`
- **human_review:** `pending`

## Intent

- **goal:** Validate a flat installed Composer package.
- **scope:** CLI validator seam only.
- **constraints:** Use an isolated fixture.
- **desired_output:** Stable JSON validation result.
- **exclusions:** No implementation execution.
- **permission_boundary:** Human approval is required before side effects; no write, network, publish, credential, or irreversible actions.

## Capability composition

No capability steps are required for this validator fixture.

## Gaps and suggestions

No unresolved gaps.

## Human checkpoints

- **approval_point:** Human review is required before any handoff.
- **decisions_needed:** None for this fixture.
- **rejection_path:** preserve this Plan and record the reason; do not execute.
- **side_effect_authorization:** Human approval is required before side effects.

## Evidence and provenance

- **skill_index_snapshot:** `{snapshot_id}`
- **catalog_revision_or_digest:** `{{digest}}`
- **source_references:** `selected=[]`
- **evidence_requirements:** The fixture and validator JSON are the evidence.
- **generated_assertions:** The registry must be found through the installed layout.
- **unknowns:** No unknowns for this fixture.

## Verification

- **step_checks:** The CLI exits successfully and reports no registry error.
- **scenario_oracle:** Flat user-level installation validates without template_registry_invalid.
- **plan_acceptance:** `pending`

## Failure and rollback

- **failure_exits:** Preserve the JSON diagnostics and stop.
- **safe_stop:** Do not hand off a failed validation.
- **rollback:** Remove only the isolated temporary fixture.
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** None; this is a validator fixture.
- **handoff_preconditions:** Human approval and passing verification.
- **authority_statement:** Composer proposes and documents; it has no execution authority.
"""


class ValidatePlanCliTest(unittest.TestCase):
    def test_flat_user_level_root_finds_composer_registry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zj-composer-flat-validator-") as name:
            root = Path(name) / "workbuddy"
            references = root / "skills" / "zj-composer" / "references"
            references.mkdir(parents=True)
            (references.parent / "SKILL.md").write_text(
                "---\nname: zj-composer\ndescription: fixture\nsource: zagentic\n---\n",
                encoding="utf-8",
            )

            template = references / "plan-template.md"
            template.write_text("flat fixture template\n", encoding="utf-8")
            digest = hashlib.sha256(template.read_bytes()).hexdigest()
            (references / "template-versions.json").write_text(
                json.dumps(
                    {
                        "schema": TEMPLATE_SCHEMA,
                        "versions": {
                            "1": {
                                "path": "references/plan-template.md",
                                "sha256": digest,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            snapshot = root / "snapshot.json"
            empty_snapshot(snapshot, root)
            snapshot_id = json.loads(snapshot.read_text(encoding="utf-8"))["snapshot_id"]
            plan = root / "plan.md"
            plan.write_text(
                minimal_plan(snapshot_id).replace(
                    "`{digest}`", "`" + json.loads(snapshot.read_text(encoding="utf-8"))["source"]["content_digest"] + "`"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(plan),
                    "--root",
                    str(root),
                    "--snapshot",
                    str(snapshot),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(payload["valid"])
            self.assertNotIn(
                "template_registry_invalid",
                payload["summary"]["categories"],
            )

    def test_monorepo_plan_keeps_template_binding(self) -> None:
        plan = REPO_ROOT / "skills-outputs/zj-composer/external-repository-research/plan.md"
        snapshot = (
            REPO_ROOT
            / "skills-outputs/zj-composer/catalog-snapshots"
            / "catalog-v1-df316e12beb071712f283a80fc86a6139bda2bbea38d188fd2d4a94d07e721d0.json"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(plan),
                "--root",
                str(REPO_ROOT),
                "--snapshot",
                str(snapshot),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["valid"])
        self.assertNotIn(
            "template_version_mismatch",
            payload["summary"]["categories"],
        )

    def test_missing_registry_is_a_non_blocking_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zj-composer-missing-registry-") as name:
            root = Path(name) / "workbuddy"
            package = root / "skills" / "zj-composer"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text(
                "---\nname: zj-composer\ndescription: fixture\nsource: zagentic\n---\n",
                encoding="utf-8",
            )
            snapshot = root / "snapshot.json"
            empty_snapshot(snapshot, root)
            snapshot_id = json.loads(snapshot.read_text(encoding="utf-8"))["snapshot_id"]
            snapshot_digest = json.loads(snapshot.read_text(encoding="utf-8"))["source"]["content_digest"]
            plan = root / "plan.md"
            plan.write_text(
                minimal_plan(snapshot_id).replace("`{digest}`", f"`{snapshot_digest}`"),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(plan),
                    "--root",
                    str(root),
                    "--snapshot",
                    str(snapshot),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(payload["valid"])
            diagnostics = payload["diagnostics"]
            self.assertEqual(
                diagnostics,
                [
                    {
                        "category": "template_registry_missing",
                        "message": "template version registry is not bundled; template pin could not be verified",
                        "severity": "warning",
                    }
                ],
            )

    def test_malformed_registry_remains_a_blocking_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zj-composer-malformed-registry-") as name:
            root = Path(name) / "workbuddy"
            references = root / "skills" / "zj-composer" / "references"
            references.mkdir(parents=True)
            (references.parent / "SKILL.md").write_text(
                "---\nname: zj-composer\ndescription: fixture\nsource: zagentic\n---\n",
                encoding="utf-8",
            )
            (references / "template-versions.json").write_text(
                "{not valid json\n",
                encoding="utf-8",
            )
            snapshot = root / "snapshot.json"
            empty_snapshot(snapshot, root)
            snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
            plan = root / "plan.md"
            plan.write_text(
                minimal_plan(snapshot_payload["snapshot_id"]).replace(
                    "`{digest}`", f"`{snapshot_payload['source']['content_digest']}`"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(plan),
                    "--root",
                    str(root),
                    "--snapshot",
                    str(snapshot),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(payload["valid"])
            self.assertEqual(payload["diagnostics"][0]["category"], "template_registry_invalid")
            self.assertEqual(payload["diagnostics"][0]["severity"], "error")


if __name__ == "__main__":
    unittest.main()
