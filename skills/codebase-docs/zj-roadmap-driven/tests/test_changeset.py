from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *[str(arg) for arg in args]],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({result.returncode})\n"
            f"args: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class ChangeSetCliTest(unittest.TestCase):
    def test_preview_scope_rejects_every_out_of_scope_topology_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            roadmap = tmpdir / "roadmap.json"
            run_cli("init", roadmap, "--title", "Roadmap", cwd=tmpdir)
            inside = json.loads(run_cli("add", roadmap, "1", "Inside", cwd=tmpdir).stdout)
            inside_leaf = json.loads(run_cli(
                "add", roadmap, inside["id"], "Inside leaf", cwd=tmpdir,
            ).stdout)
            outside = json.loads(run_cli("add", roadmap, "1", "Outside", cwd=tmpdir).stdout)
            outside_leaf = json.loads(run_cli(
                "add", roadmap, outside["id"], "Outside leaf", cwd=tmpdir,
            ).stdout)
            edge = json.loads(run_cli(
                "edge", "add", roadmap, inside_leaf["uid"], outside_leaf["uid"],
                "--type", "blocks", cwd=tmpdir,
            ).stdout)

            legacy_move = json.dumps([{
                "kind": "placement.move", "id": "p3",
                "parent_uid": inside["uid"], "outline_rank": 0,
            }])
            failed = run_cli(
                "changeset", "preview", roadmap, "--scope", inside["uid"],
                "--changes", legacy_move, cwd=tmpdir, check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertIn("E_SCOPE", failed.stderr)

            trace = json.loads(run_cli(
                "trace", "add", roadmap, "--kind", "finding", "--body", "evidence",
                "--under", inside["uid"], "--obligation-key", "scope-trace",
                cwd=tmpdir,
            ).stdout)
            in_scope_trace = json.dumps([{
                "kind": "trace.disposition", "trace_uid": trace["uid"],
                "work_uid": inside_leaf["uid"], "disposition": "covered",
            }])
            allowed = run_cli(
                "changeset", "preview", roadmap, "--scope", inside["uid"],
                "--changes", in_scope_trace, cwd=tmpdir,
            )
            self.assertEqual(json.loads(allowed.stdout)["scope"], inside["uid"])

            migrated = tmpdir / "placements.json"
            run_cli("migrate-placements", roadmap, "--output", migrated, cwd=tmpdir)

            changes_by_kind = {
                "work.create": {
                    "kind": "work.create", "parent_uid": outside["uid"], "label": "new",
                },
                "work.patch": {
                    "kind": "work.patch", "work_uid": outside_leaf["uid"],
                    "patch": {"label": "renamed"},
                },
                "work.coalesce": {
                    "kind": "work.coalesce", "target_uid": inside["uid"],
                    "source_uids": [outside_leaf["uid"]],
                },
                "work.supersede": {
                    "kind": "work.supersede", "source_uid": inside["uid"],
                    "new": {"parent_uid": outside["uid"], "label": "replacement"},
                },
                "placement.put": {
                    "kind": "placement.put", "work_uid": outside_leaf["uid"],
                    "parent_uid": inside["uid"], "outline_rank": 0,
                },
                "placement.reference": {
                    "kind": "placement.reference", "work_uid": outside_leaf["uid"],
                    "parent_uid": inside["uid"], "outline_rank": 0,
                },
                "placement.move": {
                    "kind": "placement.move", "id": "p3",
                    "parent_uid": inside["uid"], "outline_rank": 0,
                },
                "edge.put": {
                    "kind": "edge.put", "from_uid": inside["uid"],
                    "to_uid": outside["uid"], "type": "blocks",
                },
                "edge.remove": {"kind": "edge.remove", "edge_id": edge["id"]},
                "edge.replace": {
                    "kind": "edge.replace", "edge_id": edge["id"],
                    "replacement": {
                        "from_uid": inside["uid"], "to_uid": outside["uid"],
                        "type": "blocks",
                    },
                },
                "decision.append": {
                    "kind": "decision.append", "node_uid": outside_leaf["uid"],
                    "question": "q", "answer": "a",
                },
            }
            for kind, change in changes_by_kind.items():
                with self.subTest(kind=kind):
                    failed = run_cli(
                        "changeset", "preview", migrated, "--scope", inside["uid"],
                        "--changes", json.dumps([change]), cwd=tmpdir, check=False,
                    )
                    self.assertEqual(failed.returncode, 1)
                    self.assertIn("E_SCOPE", failed.stderr)

    def test_scope_is_part_of_approval_and_cannot_be_dropped_at_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            roadmap = tmpdir / "roadmap.json"
            run_cli("init", roadmap, "--title", "Roadmap", cwd=tmpdir)
            inside = json.loads(run_cli("add", roadmap, "1", "Inside", cwd=tmpdir).stdout)
            work = json.loads(run_cli(
                "add", roadmap, inside["id"], "Work", cwd=tmpdir,
            ).stdout)
            changes = json.dumps([{
                "kind": "work.patch", "work_uid": work["uid"],
                "patch": {"label": "Scoped rename"},
            }])
            preview = json.loads(run_cli(
                "changeset", "preview", roadmap, "--scope", inside["uid"],
                "--changes", changes, cwd=tmpdir,
            ).stdout)

            dropped = run_cli(
                "changeset", "apply", roadmap, "--changes", changes,
                "--approved-digest", preview["digest"], "--idempotency-key", "scope-1",
                cwd=tmpdir, check=False,
            )
            self.assertEqual(dropped.returncode, 1)
            self.assertIn("E_APPROVAL_MISMATCH", dropped.stderr)

            run_cli(
                "changeset", "apply", roadmap, "--scope", inside["uid"],
                "--changes", changes, "--approved-digest", preview["digest"],
                "--idempotency-key", "scope-1", cwd=tmpdir,
            )
            stored = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)
            self.assertEqual(stored["label"], "Scoped rename")

    def test_preview_and_apply_support_closed_topology_change_kinds(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(run_cli("add", roadmap, "1", "Original work", cwd=tmpdir).stdout)
                context = json.loads(run_cli("add", roadmap, "1", "Second context", cwd=tmpdir).stdout)
                changes = json.dumps([
                    {
                        "kind": "work.patch",
                        "work_uid": work["uid"],
                        "patch": {"label": "Renamed work"},
                    },
                    {
                        "kind": "placement.reference",
                        "work_uid": work["uid"],
                        "parent_uid": context["uid"],
                        "outline_rank": 0,
                    },
                    {
                        "kind": "edge.put",
                        "from_uid": context["uid"],
                        "to_uid": work["uid"],
                        "type": "blocks",
                    },
                    {
                        "kind": "decision.append",
                        "node_uid": work["uid"],
                        "question": "Why was this work reshaped?",
                        "answer": "The dependency boundary changed.",
                    },
                ])

                proposal = json.loads(run_cli(
                    "changeset", "preview", roadmap, "--changes", changes, cwd=tmpdir,
                ).stdout)

                self.assertEqual(proposal["schema"], "zj-changeset/v1")
                self.assertEqual(
                    proposal["change_kinds"],
                    ["work.patch", "placement.reference", "edge.put", "decision.append"],
                )
                receipt = json.loads(run_cli(
                    "changeset", "apply", roadmap, "--changes", changes,
                    "--approved-digest", proposal["digest"],
                    "--idempotency-key", "generic-1", cwd=tmpdir,
                ).stdout)
                stored = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)
                placements = json.loads(run_cli("placement", "list", roadmap, cwd=tmpdir).stdout)["placements"]
                edges = json.loads(run_cli("edge", "list", roadmap, cwd=tmpdir).stdout)["edges"]

                self.assertEqual(receipt["status"], "committed")
                self.assertEqual(stored["label"], "Renamed work")
                self.assertEqual(stored["decisions"][-1]["answer"], "The dependency boundary changed.")
                self.assertTrue(any(
                    placement["kind"] == "reference"
                    and placement["work_uid"] == work["uid"]
                    and placement["parent_uid"] == context["uid"]
                    for placement in placements
                ))
                self.assertTrue(any(
                    edge["type"] == "blocks"
                    and edge["from"] == context["id"]
                    and edge["to"] == work["id"]
                    for edge in edges
                ))

    def test_edge_replace_and_cycle_rejection_are_atomic(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                first = json.loads(run_cli("add", roadmap, "1", "First", cwd=tmpdir).stdout)
                second = json.loads(run_cli("add", roadmap, "1", "Second", cwd=tmpdir).stdout)
                third = json.loads(run_cli("add", roadmap, "1", "Third", cwd=tmpdir).stdout)
                original_edge = json.loads(run_cli(
                    "edge", "add", roadmap, first["uid"], second["uid"], "--type", "blocks", cwd=tmpdir,
                ).stdout)
                replace = json.dumps([{
                    "kind": "edge.replace",
                    "edge_id": original_edge["id"],
                    "replacement": {
                        "from_uid": first["uid"],
                        "to_uid": third["uid"],
                        "type": "blocks",
                    },
                }])
                preview = json.loads(run_cli(
                    "changeset", "preview", roadmap, "--changes", replace, cwd=tmpdir,
                ).stdout)
                run_cli(
                    "changeset", "apply", roadmap, "--changes", replace,
                    "--approved-digest", preview["digest"], "--idempotency-key", "replace-1", cwd=tmpdir,
                )
                edges = json.loads(run_cli("edge", "list", roadmap, cwd=tmpdir).stdout)["edges"]
                self.assertEqual(len(edges), 1)
                self.assertEqual(edges[0]["to"], third["id"])

                cycle = json.dumps([{
                    "kind": "edge.put",
                    "from_uid": third["uid"],
                    "to_uid": first["uid"],
                    "type": "blocks",
                }])
                cycle_preview = json.loads(run_cli(
                    "changeset", "preview", roadmap, "--changes", cycle, cwd=tmpdir,
                ).stdout)
                failed = run_cli(
                    "changeset", "apply", roadmap, "--changes", cycle,
                    "--approved-digest", cycle_preview["digest"], "--idempotency-key", "cycle-1",
                    cwd=tmpdir, check=False,
                )
                self.assertEqual(failed.returncode, 1)
                self.assertIn("E_CYCLE", failed.stderr)
                self.assertEqual(
                    json.loads(run_cli("edge", "list", roadmap, cwd=tmpdir).stdout)["edges"],
                    edges,
                )

    def test_coalesce_and_supersede_keep_one_active_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            roadmap = tmpdir / "roadmap.json"
            run_cli("init", roadmap, "--title", "Roadmap", cwd=tmpdir)
            target = json.loads(run_cli("add", roadmap, "1", "Canonical", cwd=tmpdir).stdout)
            source = json.loads(run_cli("add", roadmap, "1", "Duplicate", cwd=tmpdir).stdout)
            coalesce = json.dumps([{
                "kind": "work.coalesce",
                "target_uid": target["uid"],
                "source_uids": [source["uid"]],
            }])
            preview = json.loads(run_cli(
                "changeset", "preview", roadmap, "--changes", coalesce, cwd=tmpdir,
            ).stdout)
            run_cli(
                "changeset", "apply", roadmap, "--changes", coalesce,
                "--approved-digest", preview["digest"], "--idempotency-key", "coalesce-1", cwd=tmpdir,
            )
            source_after = json.loads(run_cli("get", roadmap, source["uid"], cwd=tmpdir).stdout)
            self.assertTrue(source_after["archived"])

            supersede = json.dumps([{
                "kind": "work.supersede",
                "source_uid": target["uid"],
                "new": {"label": "Replacement", "parent_uid": target["uid"]},
            }])
            preview = json.loads(run_cli(
                "changeset", "preview", roadmap, "--changes", supersede, cwd=tmpdir,
            ).stdout)
            receipt = json.loads(run_cli(
                "changeset", "apply", roadmap, "--changes", supersede,
                "--approved-digest", preview["digest"], "--idempotency-key", "supersede-1", cwd=tmpdir,
            ).stdout)
            self.assertEqual(receipt["status"], "committed")
            target_after = json.loads(run_cli("get", roadmap, target["uid"], cwd=tmpdir).stdout)
            self.assertTrue(target_after["archived"])


if __name__ == "__main__":
    unittest.main()
