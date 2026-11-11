#!/usr/bin/env python3
"""S3 rollout close-out contracts (issue #234).

Seams under test, confirmed with the Human before the first test was written:

* A. CLI end-to-end via subprocess: stdout JSON, stderr error code, exit code,
  and carrier/Markdown state observed through public read commands.
* B. ``Roadmap.promote(..., "accept")`` direct API call: the stable rejection
  contract for a direct topology write.

No test reaches into ``apply_promotion``, ``canonical_json``,
``_finish_reviewed_apply`` or any other implementation detail.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from roadmap import Roadmap, ReconciliationRequired  # noqa: E402


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CLI), *[str(a) for a in args]],
        cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({completed.returncode})\nargs: {args}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


class DirectPromotionRejectionTest(unittest.TestCase):
    """Seam B: a direct accept is refused with an executable migration hint."""

    def test_direct_accept_names_both_reviewed_write_commands(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = tmpd / "roadmap.json"
            run_cli("init", path, "--title", "t", cwd=tmpd)
            trace = json.loads(run_cli(
                "trace", "add", path, "--kind", "finding", "--body", "new risk",
                "--obligation-key", "risk:new", "--evidence", "scan:1", cwd=tmpd,
            ).stdout)
            before = path.read_bytes()
            rm = Roadmap(str(path))
            rm.load()

            with self.assertRaises(ReconciliationRequired) as raised:
                rm.promote(trace["uid"], "accept")

            self.assertEqual(raised.exception.code, "E_RECONCILIATION_REQUIRED")
            # Expected literals come from the migration contract, not from a
            # constant exported by the implementation (no tautological assert).
            message = str(raised.exception)
            self.assertIn("reconcile <roadmap> <trace_uid>", message)
            self.assertIn(
                "apply <roadmap> <proposal_id> --approved-digest <digest> "
                "--idempotency-key <key>",
                message,
            )
            self.assertEqual(path.read_bytes(), before)


class CliPromotionMigrationTest(unittest.TestCase):
    """Seam A: a missing approved digest fails with an executable migration hint."""

    def test_missing_digest_names_the_reviewed_accept_command(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = tmpd / "roadmap.json"
            run_cli("init", path, "--title", "t", cwd=tmpd)
            trace = json.loads(run_cli(
                "trace", "add", path, "--kind", "finding", "--body", "new risk",
                "--obligation-key", "risk:new", "--evidence", "scan:1", cwd=tmpd,
            ).stdout)
            before = path.read_bytes()

            rejected = run_cli(
                "promote", path, trace["uid"], "--accept",
                "--idempotency-key", "missing-digest-1",
                check=False, cwd=tmpd,
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("E_USAGE", rejected.stderr)
            # Spec-level literals; never import an implementation constant here.
            self.assertIn("reconcile <roadmap> <trace_uid>", rejected.stderr)
            self.assertIn(
                "promote <roadmap> <trace_uid> --accept --approved-digest <digest> "
                "--idempotency-key <key>",
                rejected.stderr,
            )
            self.assertEqual(path.read_bytes(), before)


TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def normalize_identity(value, uid_apply: str, uid_promote: str):
    """Collapse each path's freshly minted WorkItem uid into one shared token.

    ``new_uid()`` deliberately uses time + randomness, so two independent
    executions cannot be byte-identical. The revision is derived from that
    identity and is collapsed as well; ``base_revision`` is asserted separately
    as the real pre-commit semantic evidence.
    """
    if isinstance(value, str):
        for uid in (uid_apply, uid_promote):
            value = value.replace(uid, "<WORK_UID>")
        return value
    if isinstance(value, list):
        return [normalize_identity(v, uid_apply, uid_promote) for v in value]
    if isinstance(value, dict):
        return {
            key: ("<REVISION>" if key == "revision"
                  else normalize_identity(v, uid_apply, uid_promote))
            for key, v in value.items()
        }
    return value


class ReviewedWriteParityTest(unittest.TestCase):
    """Seam A: explicit reconcile+apply and default accept stay isomorphic.

    Every observation comes from a public CLI command. Nothing reaches into the
    carrier internals, ``canonical_json`` or the apply implementation.
    """

    def test_two_reviewed_write_paths_produce_isomorphic_canonical_state(self):
        for storage, ext in (("single", "json"), ("sqlite", "sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as d:
                tmpd = Path(d)
                seed = tmpd / f"seed.{ext}"
                init_args = ["init", seed, "--title", "parity"]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpd)
                trace = json.loads(run_cli(
                    "trace", "add", seed, "--kind", "finding", "--body", "new risk",
                    "--obligation-key", "risk:new", "--evidence", "scan:1", cwd=tmpd,
                ).stdout)
                uid = trace["uid"]

                observed = {}
                minted = {}
                for label in ("apply", "promote"):
                    path = tmpd / f"{label}.{ext}"
                    shutil.copy(seed, path)
                    proposal = json.loads(run_cli("reconcile", path, uid, cwd=tmpd).stdout)
                    if label == "apply":
                        cmd = ("apply", path, proposal["proposal_id"],
                               "--approved-digest", proposal["proposal_digest"],
                               "--idempotency-key", "parity-key")
                    else:
                        cmd = ("promote", path, uid, "--accept",
                               "--approved-digest", proposal["proposal_digest"],
                               "--idempotency-key", "parity-key")
                    receipt = json.loads(run_cli(*cmd, cwd=tmpd).stdout)
                    work_uids = {
                        change["work_uid"] for change in receipt.get("changes", [])
                        if "work_uid" in change
                    }
                    self.assertEqual(len(work_uids), 1, f"{storage}/{label} work_uids")
                    self.assertEqual(receipt["view_status"], "published",
                                     f"{storage}/{label} view")
                    minted[label] = work_uids.pop()
                    md_path = tmpd / "ROADMAP.md"
                    md_text = md_path.read_text(encoding="utf-8")
                    # The view header names its carrier file; that is fixture
                    # identity, not roadmap semantics.
                    md_text = md_text.replace(path.name, "<CARRIER>")
                    observed[label] = {
                        "proposal": proposal,
                        "receipt": receipt,
                        "trace": json.loads(run_cli("get", path, uid, cwd=tmpd).stdout),
                        "ready": run_cli("ready", path, cwd=tmpd).stdout,
                        "critical_path": run_cli("critical-path", path, cwd=tmpd).stdout,
                        "tree": run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                        "stats": run_cli("stats", path, cwd=tmpd).stdout,
                        "md": TS_RE.sub("TS", md_text),
                    }

                apply, promote = observed["apply"], observed["promote"]
                self.assertEqual(apply["proposal"], promote["proposal"], storage)
                self.assertEqual(
                    apply["receipt"]["base_revision"],
                    promote["receipt"]["base_revision"],
                    storage,
                )
                norm_apply = normalize_identity(apply, minted["apply"], minted["promote"])
                norm_promote = normalize_identity(promote, minted["apply"], minted["promote"])
                for key in ("receipt", "trace", "ready", "critical_path",
                            "tree", "stats", "md"):
                    self.assertEqual(norm_apply[key], norm_promote[key],
                                     f"{storage}/{key}")


class PromoteAcceptFaultTest(unittest.TestCase):
    """Seam A: ``promote --accept`` shares the stale-view fault path with ``apply``.

    The reviewed accept routes through the same ``_finish_reviewed_apply`` as
    ``apply``; a Markdown publication failure must leave a stale view only, and a
    retry (no fault) must repair it.  This closes the evidence gap where only the
    ``apply`` path was covered.
    """

    def test_promote_accept_fault_leaves_stale_view_and_retry_repairs(self):
        for storage, ext in (("single", "json"), ("sqlite", "sqlite")):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as d:
                tmpd = Path(d)
                seed = tmpd / f"roadmap.{ext}"
                md_file = tmpd / "ROADMAP.md"
                md_file.write_text("# Plan\n", encoding="utf-8")
                init_args = ["init", seed, "--title", "Roadmap", "--md-file", md_file]
                if storage == "sqlite":
                    init_args += ["--storage", "sqlite"]
                run_cli(*init_args, cwd=tmpd)
                run_cli("add", seed, "1", "Publish the report",
                        "--obligation-key", "report:publish", cwd=tmpd)
                trace = json.loads(run_cli(
                    "trace", "add", seed, "--kind", "finding",
                    "--body", "The report still needs publication",
                    "--obligation-key", "report:publish", cwd=tmpd,
                ).stdout)
                proposal = json.loads(
                    run_cli("reconcile", seed, trace["uid"], cwd=tmpd).stdout
                )
                before_view = md_file.read_text(encoding="utf-8")

                stale = json.loads(run_cli(
                    "promote", seed, trace["uid"], "--accept",
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "promote-fault-1",
                    "--fault-stage", "after-commit-before-view", cwd=tmpd,
                ).stdout)
                repaired = json.loads(run_cli(
                    "promote", seed, trace["uid"], "--accept",
                    "--approved-digest", proposal["proposal_digest"],
                    "--idempotency-key", "promote-fault-1", cwd=tmpd,
                ).stdout)

                self.assertEqual(stale["status"], "committed")
                self.assertEqual(stale["view_status"], "stale")
                self.assertEqual(before_view, "# Plan\n")
                self.assertEqual(repaired["view_status"], "published")
                self.assertIn(
                    "Publish the report", md_file.read_text(encoding="utf-8")
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
