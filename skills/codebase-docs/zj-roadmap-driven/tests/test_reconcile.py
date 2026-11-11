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


class ReconcilePreviewTest(unittest.TestCase):
    def test_batch_reconcile_deduplicates_trace_ids_and_preserves_dispositions(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                for label in ("First owner", "Second owner"):
                    run_cli(
                        "add",
                        roadmap,
                        "1",
                        label,
                        "--obligation-key",
                        "risk:shared",
                        cwd=tmpdir,
                    )

                def add_trace(key: str, body: str, *extra: str) -> dict:
                    return json.loads(
                        run_cli(
                            "trace",
                            "add",
                            roadmap,
                            "--kind",
                            "finding",
                            "--body",
                            body,
                            "--obligation-key",
                            key,
                            *extra,
                            cwd=tmpdir,
                        ).stdout
                    )

                covered = add_trace("report:publish", "The report still needs publication")
                novel = add_trace(
                    "risk:new",
                    "A new compliance risk was found",
                    "--evidence",
                    "source:security-scan-17",
                )
                unresolved = add_trace("risk:shared", "The shared risk needs an owner")
                before = run_cli("stats", roadmap, cwd=tmpdir).stdout

                batch = json.loads(
                    run_cli(
                        "reconcile",
                        roadmap,
                        "--trace",
                        covered["uid"],
                        "--trace",
                        covered["uid"],
                        "--trace",
                        novel["uid"],
                        "--trace",
                        unresolved["uid"],
                        cwd=tmpdir,
                    ).stdout
                )

                self.assertEqual(batch["schema"], "zj-reconciliation-batch/v1")
                self.assertEqual(batch["trace_uids"], sorted({
                    covered["uid"], novel["uid"], unresolved["uid"],
                }))
                self.assertEqual(
                    [proposal["disposition"] for proposal in batch["proposals"]],
                    ["covered", "novel", "unresolved"],
                )
                self.assertEqual(
                    batch["summary"],
                    {"covered": 1, "novel": 1, "unresolved": 1},
                )
                self.assertTrue(batch["batch_digest"].startswith("rb-"))
                self.assertEqual(before, run_cli("stats", roadmap, cwd=tmpdir).stdout)

    def test_batch_apply_coalesces_duplicate_novel_findings_into_one_work_item(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                traces = []
                for body in ("First scan found the risk", "Second scan found the risk"):
                    traces.append(json.loads(run_cli(
                        "trace", "add", roadmap, "--kind", "finding", "--body", body,
                        "--obligation-key", "risk:duplicate",
                        "--evidence", "source:scan",
                        cwd=tmpdir,
                    ).stdout))
                batch = json.loads(run_cli(
                    "reconcile", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
                    cwd=tmpdir,
                ).stdout)

                self.assertEqual(
                    batch["duplicate_groups"],
                    [{
                        "obligation_key": "risk:duplicate",
                        "canonical_trace_uid": min(trace["uid"] for trace in traces),
                        "trace_uids": sorted(trace["uid"] for trace in traces),
                    }],
                )

                receipt = json.loads(run_cli(
                    "apply-batch", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
                    "--approved-digest", batch["batch_digest"],
                    "--idempotency-key", "batch-duplicate-1",
                    cwd=tmpdir,
                ).stdout)
                first_stored = json.loads(run_cli("get", roadmap, traces[0]["uid"], cwd=tmpdir).stdout)
                second_stored = json.loads(run_cli("get", roadmap, traces[1]["uid"], cwd=tmpdir).stdout)
                tree = run_cli("tree", roadmap, "--depth", "3", cwd=tmpdir).stdout
                edges = json.loads(run_cli("edge", "list", roadmap, cwd=tmpdir).stdout)["edges"]

                self.assertEqual(receipt["status"], "committed")
                self.assertEqual(first_stored["reconciliation"]["work_uid"], second_stored["reconciliation"]["work_uid"])
                self.assertEqual(tree.count("First scan found the risk"), 1)
                self.assertEqual(tree.count("Second scan found the risk"), 0)
                derives = [edge for edge in edges if edge["type"] == "derives-from"]
                self.assertEqual(len(derives), 2)
                self.assertEqual({edge["to"] for edge in derives}, {
                    json.loads(run_cli("get", roadmap, first_stored["reconciliation"]["work_uid"], cwd=tmpdir).stdout)["id"]
                })

    def test_completed_work_item_requires_refinement_decision(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(run_cli(
                    "add", roadmap, "1", "Completed obligation",
                    "--obligation-key", "risk:completed", cwd=tmpdir,
                ).stdout)
                run_cli("update", roadmap, work["id"], "--status", "completed", cwd=tmpdir)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "New evidence",
                    "--obligation-key", "risk:completed", cwd=tmpdir,
                ).stdout)

                proposal = json.loads(run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout)

                self.assertEqual(proposal["disposition"], "refine")
                self.assertEqual(proposal["matches"][0]["uid"], work["uid"])
                self.assertEqual(proposal["changes"], [])
                self.assertEqual(proposal["questions"][0]["code"], "E_COMPLETED_WORK_REFINEMENT")

    def test_dismiss_answer_is_previewable_and_apply_persists_human_decision(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "Informational note",
                    "--obligation-key", "risk:informational", "--evidence", "source:review",
                    cwd=tmpdir,
                ).stdout)
                answer = json.dumps({
                    "disposition": "dismiss",
                    "reason": "Informational only; no scheduled work is required.",
                }, ensure_ascii=False)

                proposal = json.loads(run_cli(
                    "reconcile", roadmap, trace["uid"], "--answer", answer, cwd=tmpdir,
                ).stdout)

                self.assertEqual(proposal["disposition"], "dismiss")
                self.assertEqual(proposal["questions"], [])
                self.assertEqual(proposal["changes"][0]["kind"], "decision.append")
                self.assertEqual(proposal["changes"][0]["reason"], "Informational only; no scheduled work is required.")

                receipt = json.loads(run_cli(
                    "apply", roadmap, proposal["proposal_id"],
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "dismiss-1", "--answer", answer, cwd=tmpdir,
                ).stdout)
                stored = json.loads(run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout)

                self.assertEqual(receipt["status"], "committed")
                self.assertEqual(stored["reconciliation"]["disposition"], "dismiss")
                self.assertEqual(stored["reconciliation"]["reason"], "Informational only; no scheduled work is required.")
                self.assertEqual(stored["decisions"][-1]["answer"], "Informational only; no scheduled work is required.")

    def test_completed_refinement_can_reopen_with_explicit_answer(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(run_cli(
                    "add", roadmap, "1", "Completed obligation",
                    "--obligation-key", "risk:reopen", cwd=tmpdir,
                ).stdout)
                run_cli("update", roadmap, work["id"], "--status", "completed", cwd=tmpdir)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "New evidence",
                    "--obligation-key", "risk:reopen", cwd=tmpdir,
                ).stdout)
                answer = json.dumps({
                    "disposition": "refine",
                    "action": "reopen",
                    "reason": "The acceptance evidence changed.",
                })

                proposal = json.loads(run_cli(
                    "reconcile", roadmap, trace["uid"], "--answer", answer, cwd=tmpdir,
                ).stdout)
                self.assertEqual(proposal["disposition"], "refine")
                self.assertEqual(proposal["changes"][0]["kind"], "work.patch")
                self.assertEqual(proposal["changes"][0]["patch"], {"status": "in_progress"})

                run_cli(
                    "apply", roadmap, proposal["proposal_id"],
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "reopen-1", "--answer", answer, cwd=tmpdir,
                )
                stored_work = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)
                stored_trace = json.loads(run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout)

                self.assertEqual(stored_work["status"], "in_progress")
                self.assertEqual(stored_work["decisions"][-1]["answer"], "The acceptance evidence changed.")
                self.assertEqual(stored_trace["reconciliation"]["disposition"], "refine")

    def test_completed_refinement_supports_noop_and_supersede_answers(self):
        for action in ("noop", "supersede"):
            for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
                with self.subTest(action=action, storage=storage), tempfile.TemporaryDirectory() as directory:
                    tmpdir = Path(directory)
                    roadmap = tmpdir / filename
                    init_args = ["init", roadmap, "--title", "Roadmap"]
                    if storage == "sqlite":
                        init_args += ["--storage", "sqlite"]
                    run_cli(*init_args, cwd=tmpdir)
                    work = json.loads(run_cli(
                        "add", roadmap, "1", "Completed obligation",
                        "--obligation-key", "risk:decision", cwd=tmpdir,
                    ).stdout)
                    run_cli("update", roadmap, work["id"], "--status", "completed", cwd=tmpdir)
                    trace = json.loads(run_cli(
                        "trace", "add", roadmap, "--kind", "finding", "--body", "Changed evidence",
                        "--obligation-key", "risk:decision", cwd=tmpdir,
                    ).stdout)
                    answer_data = {
                        "disposition": "refine",
                        "action": action,
                        "reason": f"Explicit {action} decision.",
                    }
                    if action == "supersede":
                        answer_data["label"] = "Replacement obligation"
                    answer = json.dumps(answer_data)
                    proposal = json.loads(run_cli(
                        "reconcile", roadmap, trace["uid"], "--answer", answer, cwd=tmpdir,
                    ).stdout)
                    run_cli(
                        "apply", roadmap, proposal["proposal_id"],
                        "--approved-digest", proposal["proposal_digest"],
                        "--idempotency-key", f"{action}-1", "--answer", answer, cwd=tmpdir,
                    )
                    stored_work = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)
                    stored_trace = json.loads(run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout)
                    edges = json.loads(run_cli("edge", "list", roadmap, cwd=tmpdir).stdout)["edges"]

                    self.assertEqual(stored_work["decisions"][-1]["answer"], f"Explicit {action} decision.")
                    self.assertEqual(stored_trace["reconciliation"]["disposition"], "refine")
                    if action == "noop":
                        self.assertEqual(stored_work["status"], "completed")
                    else:
                        self.assertTrue(stored_work["archived"])
                        replacement = json.loads(run_cli(
                            "get", roadmap, stored_trace["reconciliation"]["work_uid"], cwd=tmpdir,
                        ).stdout)
                        self.assertEqual(replacement["label"], "Replacement obligation")
                        self.assertTrue(any(edge["type"] == "supersedes" for edge in edges))
                        self.assertTrue(any(edge["type"] == "derives-from" for edge in edges))

    def test_reshape_answer_applies_graph_changes_atomically(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(run_cli(
                    "add", roadmap, "1", "Original work", "--obligation-key", "risk:reshape", cwd=tmpdir,
                ).stdout)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "Topology changed",
                    "--obligation-key", "risk:reshape", cwd=tmpdir,
                ).stdout)
                answer = json.dumps({
                    "disposition": "reshape",
                    "work_uid": work["uid"],
                    "reason": "The work belongs in a second outline context.",
                    "changes": [
                        {
                            "kind": "work.patch",
                            "work_uid": work["uid"],
                            "patch": {"label": "Reshaped work"},
                        },
                        {
                            "kind": "placement.reference",
                            "work_uid": work["uid"],
                            "parent_uid": json.loads(run_cli("get", roadmap, "1", cwd=tmpdir).stdout)["uid"],
                            "outline_rank": 0,
                        },
                    ],
                })
                proposal = json.loads(run_cli(
                    "reconcile", roadmap, trace["uid"], "--answer", answer, cwd=tmpdir,
                ).stdout)
                self.assertEqual(proposal["disposition"], "reshape")

                run_cli(
                    "apply", roadmap, proposal["proposal_id"],
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "reshape-1", "--answer", answer, cwd=tmpdir,
                )
                stored = json.loads(run_cli("get", roadmap, work["uid"], cwd=tmpdir).stdout)
                placements = json.loads(run_cli("placement", "list", roadmap, cwd=tmpdir).stdout)["placements"]
                stored_trace = json.loads(run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout)

                self.assertEqual(stored["label"], "Reshaped work")
                self.assertEqual(stored_trace["reconciliation"]["disposition"], "reshape")
                self.assertTrue(any(
                    placement["kind"] == "reference" and placement["work_uid"] == work["uid"]
                    for placement in placements
                ))

    def test_batch_apply_rejects_stale_base_revision(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                traces = []
                for body in ("First finding", "Second finding"):
                    traces.append(json.loads(run_cli(
                        "trace", "add", roadmap, "--kind", "finding", "--body", body,
                        "--obligation-key", "risk:stale-batch", "--evidence", "source:fixture",
                        cwd=tmpdir,
                    ).stdout))
                batch = json.loads(run_cli(
                    "reconcile", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"], cwd=tmpdir,
                ).stdout)
                run_cli("add", roadmap, "1", "Concurrent change", cwd=tmpdir)

                result = run_cli(
                    "apply-batch", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
                    "--approved-digest", batch["batch_digest"],
                    "--idempotency-key", "stale-batch",
                    cwd=tmpdir, check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_CONFLICT", result.stderr)

    def test_batch_apply_rejects_refinement_without_internal_traceback(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(run_cli(
                    "add", roadmap, "1", "Completed obligation",
                    "--obligation-key", "risk:completed-batch", cwd=tmpdir,
                ).stdout)
                run_cli("update", roadmap, work["id"], "--status", "completed", cwd=tmpdir)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "New evidence",
                    "--obligation-key", "risk:completed-batch", cwd=tmpdir,
                ).stdout)
                batch = json.loads(run_cli(
                    "reconcile", roadmap, "--trace", trace["uid"], cwd=tmpdir,
                ).stdout)

                result = run_cli(
                    "apply-batch", roadmap, "--trace", trace["uid"],
                    "--approved-digest", batch["batch_digest"],
                    "--idempotency-key", "refinement-batch-1",
                    cwd=tmpdir, check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_CHANGESET_INVALID", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                stored_trace = json.loads(run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout)
                self.assertNotIn("reconciliation", stored_trace)

    def test_batch_after_commit_retry_returns_receipt_and_repairs_view(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                md_file = tmpdir / "ROADMAP.md"
                md_file.write_text("# Plan\n", encoding="utf-8")
                init_args = [
                    "init", roadmap, "--title", "Roadmap", "--md-file", md_file,
                ]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                traces = []
                for body in ("First finding", "Second finding"):
                    traces.append(json.loads(run_cli(
                        "trace", "add", roadmap, "--kind", "finding", "--body", body,
                        "--obligation-key", "risk:batch-view", "--evidence", "source:fixture",
                        cwd=tmpdir,
                    ).stdout))
                batch = json.loads(run_cli(
                    "reconcile", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"], cwd=tmpdir,
                ).stdout)

                stale = json.loads(run_cli(
                    "apply-batch", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
                    "--approved-digest", batch["batch_digest"],
                    "--idempotency-key", "batch-after-commit-1",
                    "--fault-stage", "after-commit-before-view", cwd=tmpdir,
                ).stdout)
                repaired = json.loads(run_cli(
                    "apply-batch", roadmap,
                    "--trace", traces[0]["uid"], "--trace", traces[1]["uid"],
                    "--approved-digest", batch["batch_digest"],
                    "--idempotency-key", "batch-after-commit-1", cwd=tmpdir,
                ).stdout)

                self.assertEqual(stale["view_status"], "stale")
                self.assertEqual(repaired["view_status"], "published")
                self.assertEqual(repaired["revision"], stale["revision"])
                self.assertIn("First finding", md_file.read_text(encoding="utf-8"))

    def test_covered_proposal_applies_once_and_idempotent_retry_returns_same_receipt(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(
                    run_cli(
                        "add",
                        roadmap,
                        "1",
                        "Publish the report",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                first = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "apply-covered-1",
                        cwd=tmpdir,
                    ).stdout
                )
                second = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "apply-covered-1",
                        cwd=tmpdir,
                    ).stdout
                )
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(first, second)
                self.assertEqual(first["schema"], "zj-changeset-receipt/v1")
                self.assertEqual(first["status"], "committed")
                self.assertEqual(first["proposal_id"], proposal["proposal_id"])
                self.assertEqual(stored_trace["reconciliation"]["disposition"], "covered")
                self.assertEqual(stored_trace["reconciliation"]["work_uid"], work["uid"])

    def test_idempotency_key_cannot_be_reused_for_another_proposal(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                work = json.loads(
                    run_cli(
                        "add", roadmap, "1", "Publish the report",
                        "--obligation-key", "report:publish", cwd=tmpdir,
                    ).stdout
                )
                traces = []
                for body in ("First finding", "Second finding"):
                    traces.append(json.loads(run_cli(
                        "trace", "add", roadmap, "--kind", "finding", "--body", body,
                        "--obligation-key", "report:publish", cwd=tmpdir,
                    ).stdout))
                first = json.loads(run_cli("reconcile", roadmap, traces[0]["uid"], cwd=tmpdir).stdout)
                second = json.loads(run_cli("reconcile", roadmap, traces[1]["uid"], cwd=tmpdir).stdout)
                run_cli(
                    "apply", roadmap, first["proposal_id"],
                    "--approved-digest", first["proposal_digest"],
                    "--idempotency-key", "same-key", cwd=tmpdir,
                )

                result = run_cli(
                    "apply", roadmap, second["proposal_id"],
                    "--approved-digest", second["proposal_digest"],
                    "--idempotency-key", "same-key", cwd=tmpdir, check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_IDEMPOTENCY_CONFLICT", result.stderr)

    def test_apply_rejects_stale_revision_without_mutating_trace(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                run_cli("add", roadmap, "1", "Unrelated work", cwd=tmpdir)

                result = run_cli(
                    "apply",
                    roadmap,
                    proposal["proposal_id"],
                    "--approved-digest",
                    proposal["proposal_digest"],
                    "--idempotency-key",
                    "stale-1",
                    cwd=tmpdir,
                    check=False,
                )
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_CONFLICT", result.stderr)
                self.assertNotIn("reconciliation", stored_trace)

    def test_apply_rejects_approval_digest_mismatch_without_mutating_trace(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                result = run_cli(
                    "apply",
                    roadmap,
                    proposal["proposal_id"],
                    "--approved-digest",
                    "0" * 64,
                    "--idempotency-key",
                    "wrong-digest-1",
                    cwd=tmpdir,
                    check=False,
                )
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_APPROVAL_MISMATCH", result.stderr)
                self.assertNotIn("reconciliation", stored_trace)

    def test_apply_reports_proposal_not_found_with_current_revision(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "Covered finding",
                    "--obligation-key", "risk:covered", "--evidence", "fixture:proposal-not-found",
                    cwd=tmpdir,
                ).stdout)
                proposal = json.loads(run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout)
                unknown_id = f"rp-{proposal['base_revision']}-not-a-real-proposal"

                result = run_cli(
                    "apply", roadmap, unknown_id,
                    "--approved-digest", "0" * 64,
                    "--idempotency-key", "proposal-not-found",
                    cwd=tmpdir, check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_PROPOSAL_NOT_FOUND", result.stderr)

    def test_apply_rejects_unresolved_proposal_as_invalid_changeset(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                for label in ("First owner", "Second owner"):
                    run_cli(
                        "add", roadmap, "1", label,
                        "--obligation-key", "risk:ambiguous", cwd=tmpdir,
                    )
                trace = json.loads(run_cli(
                    "trace", "add", roadmap, "--kind", "finding", "--body", "Ambiguous finding",
                    "--obligation-key", "risk:ambiguous", cwd=tmpdir,
                ).stdout)
                proposal = json.loads(run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout)

                result = run_cli(
                    "apply", roadmap, proposal["proposal_id"],
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "invalid-unresolved",
                    cwd=tmpdir, check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_CHANGESET_INVALID", result.stderr)

    def test_novel_proposal_creates_one_work_item_and_provenance_edge(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "A new compliance risk was found",
                        "--under",
                        "1",
                        "--obligation-key",
                        "risk:compliance",
                        "--evidence",
                        "source:security-scan-17",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                receipt = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "apply-novel-1",
                        cwd=tmpdir,
                    ).stdout
                )
                retry = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "apply-novel-1",
                        cwd=tmpdir,
                    ).stdout
                )
                plan = run_cli("tree", roadmap, "--depth", "10", cwd=tmpdir).stdout
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                edges = json.loads(
                    run_cli("edge", "list", roadmap, cwd=tmpdir).stdout
                )["edges"]

                self.assertEqual(receipt, retry)
                self.assertEqual(receipt["status"], "committed")
                self.assertIn("A new compliance risk was found", plan)
                self.assertEqual(stored_trace["reconciliation"]["disposition"], "novel")
                created_uid = stored_trace["reconciliation"]["work_uid"]
                created_node = json.loads(
                    run_cli("get", roadmap, created_uid, cwd=tmpdir).stdout
                )
                self.assertEqual(
                    len([edge for edge in edges if edge["type"] == "derives-from"]),
                    1,
                )
                self.assertEqual(
                    [edge for edge in edges if edge["type"] == "derives-from"][0]["from"],
                    trace["id"],
                )
                self.assertEqual(
                    [edge for edge in edges if edge["type"] == "derives-from"][0]["to"],
                    created_node["id"],
                )

    def test_fault_before_commit_leaves_old_state_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                before = run_cli("stats", roadmap, cwd=tmpdir).stdout

                result = run_cli(
                    "apply",
                    roadmap,
                    proposal["proposal_id"],
                    "--approved-digest",
                    proposal["proposal_digest"],
                    "--idempotency-key",
                    "fault-before-commit-1",
                    "--fault-stage",
                    "before-commit",
                    cwd=tmpdir,
                    check=False,
                )
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_INJECTED_FAILURE", result.stderr)
                self.assertEqual(before, run_cli("stats", roadmap, cwd=tmpdir).stdout)
                self.assertNotIn("reconciliation", stored_trace)

    def test_fault_after_commit_reports_stale_view_and_retry_repairs_it(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                md_file = tmpdir / "ROADMAP.md"
                md_file.write_text("# Plan\n", encoding="utf-8")
                init_args = [
                    "init",
                    roadmap,
                    "--title",
                    "Roadmap",
                    "--md-file",
                    md_file,
                ]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                before_view = md_file.read_text(encoding="utf-8")

                stale = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "fault-after-commit-1",
                        "--fault-stage",
                        "after-commit-before-view",
                        cwd=tmpdir,
                    ).stdout
                )
                repaired = json.loads(
                    run_cli(
                        "apply",
                        roadmap,
                        proposal["proposal_id"],
                        "--approved-digest",
                        proposal["proposal_digest"],
                        "--idempotency-key",
                        "fault-after-commit-1",
                        cwd=tmpdir,
                    ).stdout
                )

                self.assertEqual(stale["status"], "committed")
                self.assertEqual(stale["view_status"], "stale")
                self.assertEqual(before_view, "# Plan\n")
                self.assertEqual(repaired["view_status"], "published")
                self.assertIn("Publish the report", md_file.read_text(encoding="utf-8"))

    def test_fault_during_carrier_commit_leaves_old_state_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                before = run_cli("stats", roadmap, cwd=tmpdir).stdout

                result = run_cli(
                    "apply",
                    roadmap,
                    proposal["proposal_id"],
                    "--approved-digest",
                    proposal["proposal_digest"],
                    "--idempotency-key",
                    "fault-during-commit-1",
                    "--fault-stage",
                    "during-commit",
                    cwd=tmpdir,
                    check=False,
                )
                stored_trace = json.loads(
                    run_cli("get", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_INJECTED_FAILURE", result.stderr)
                self.assertEqual(before, run_cli("stats", roadmap, cwd=tmpdir).stdout)
                self.assertNotIn("reconciliation", stored_trace)

    def test_exact_duplicate_is_reported_as_covered_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                run_cli(
                    "add",
                    roadmap,
                    "1",
                    "Publish the report",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The report still needs publication",
                        "--obligation-key",
                        "report:publish",
                        cwd=tmpdir,
                    ).stdout
                )

                before = run_cli("stats", roadmap, cwd=tmpdir).stdout
                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )
                after = run_cli("stats", roadmap, cwd=tmpdir).stdout

                self.assertEqual(proposal["schema"], "zj-reconciliation-proposal/v1")
                self.assertEqual(proposal["disposition"], "covered")
                self.assertEqual(proposal["obligation_key"], "report:publish")
                self.assertEqual(len(proposal["matches"]), 1)
                self.assertEqual(proposal["matches"][0]["id"], "1-1")
                self.assertEqual(proposal["matches"][0]["label"], "Publish the report")
                self.assertTrue(proposal["matches"][0]["uid"])
                self.assertEqual(
                    proposal["changes"],
                    [{
                        "kind": "trace.disposition",
                        "disposition": "covered",
                        "trace_uid": proposal["trace_uid"],
                        "work_uid": proposal["matches"][0]["uid"],
                    }],
                )
                self.assertEqual(before, after, "preview must not mutate the roadmap")

    def test_novel_finding_without_evidence_is_rejected_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "A new compliance risk was found",
                        "--obligation-key",
                        "risk:compliance",
                        cwd=tmpdir,
                    ).stdout
                )

                result = run_cli(
                    "reconcile",
                    roadmap,
                    trace["uid"],
                    cwd=tmpdir,
                    check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_NOVELTY_EVIDENCE_MISSING", result.stderr)

    def test_reconcile_requires_an_explicit_obligation_key_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "A free-text-only finding",
                        cwd=tmpdir,
                    ).stdout
                )

                result = run_cli(
                    "reconcile",
                    roadmap,
                    trace["uid"],
                    cwd=tmpdir,
                    check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("E_RECONCILE_KEY_MISSING", result.stderr)

    def test_novel_finding_with_evidence_is_proposed_on_each_carrier(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "A new compliance risk was found",
                        "--obligation-key",
                        "risk:compliance",
                        "--evidence",
                        "source:security-scan-17",
                        cwd=tmpdir,
                    ).stdout
                )

                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(proposal["disposition"], "novel")
                self.assertEqual(proposal["matches"], [])
                self.assertEqual(proposal["evidence"], ["source:security-scan-17"])
                self.assertEqual(proposal["changes"][0]["kind"], "work.create")

    def test_proposal_is_identical_after_single_to_sqlite_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            single = tmpdir / "roadmap.json"
            sqlite = tmpdir / "roadmap.sqlite"
            run_cli("init", single, "--title", "Roadmap", cwd=tmpdir)
            run_cli(
                "add",
                single,
                "1",
                "Publish the report",
                "--obligation-key",
                "report:publish",
                cwd=tmpdir,
            )
            trace = json.loads(
                run_cli(
                    "trace",
                    "add",
                    single,
                    "--kind",
                    "finding",
                    "--body",
                    "The report still needs publication",
                    "--obligation-key",
                    "report:publish",
                    cwd=tmpdir,
                ).stdout
            )
            run_cli(
                "migrate",
                single,
                "--to",
                "sqlite",
                "--output",
                sqlite,
                cwd=tmpdir,
            )

            single_proposal = json.loads(
                run_cli("reconcile", single, trace["uid"], cwd=tmpdir).stdout
            )
            sqlite_proposal = json.loads(
                run_cli("reconcile", sqlite, trace["uid"], cwd=tmpdir).stdout
            )

            self.assertEqual(single_proposal, sqlite_proposal)

    def test_multiple_exact_matches_are_unresolved_without_auto_creation(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                for label in ("First owner", "Second owner"):
                    run_cli(
                        "add",
                        roadmap,
                        "1",
                        label,
                        "--obligation-key",
                        "risk:shared",
                        cwd=tmpdir,
                    )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The shared risk needs a canonical owner",
                        "--obligation-key",
                        "risk:shared",
                        cwd=tmpdir,
                    ).stdout
                )

                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(proposal["disposition"], "unresolved")
                self.assertEqual([match["id"] for match in proposal["matches"]], ["1-1", "1-2"])
                self.assertEqual(proposal["changes"], [])
                self.assertEqual(len(proposal["questions"]), 1)

    def test_archived_exact_match_is_not_an_active_candidate(self):
        for storage, filename in (("single", "roadmap.json"), ("sqlite", "roadmap.sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as directory:
                tmpdir = Path(directory)
                roadmap = tmpdir / filename
                init_args = ["init", roadmap, "--title", "Roadmap"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpdir)
                for label in ("Archived owner", "Current owner"):
                    run_cli(
                        "add",
                        roadmap,
                        "1",
                        label,
                        "--obligation-key",
                        "risk:rotated",
                        cwd=tmpdir,
                    )
                run_cli(
                    "edge",
                    "add",
                    roadmap,
                    "1-2",
                    "1-1",
                    "--type",
                    "supersedes",
                    cwd=tmpdir,
                )
                trace = json.loads(
                    run_cli(
                        "trace",
                        "add",
                        roadmap,
                        "--kind",
                        "finding",
                        "--body",
                        "The rotated risk remains in scope",
                        "--obligation-key",
                        "risk:rotated",
                        cwd=tmpdir,
                    ).stdout
                )

                proposal = json.loads(
                    run_cli("reconcile", roadmap, trace["uid"], cwd=tmpdir).stdout
                )

                self.assertEqual(proposal["disposition"], "covered")
                self.assertEqual([match["id"] for match in proposal["matches"]], ["1-2"])


if __name__ == "__main__":
    unittest.main()
