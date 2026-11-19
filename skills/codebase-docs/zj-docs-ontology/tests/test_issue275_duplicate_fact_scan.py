#!/usr/bin/env python3
"""Issue #275 Fix 5: one-home-per-fact gets a mechanical signal.

Acceptance 3 of issue #275: "派生 ontology 视图不得与原文构成并行体系;
one-home-per-fact 应有机械信号（例如检测到 N 份文档重复同一事实且无权威
归属时报警）". Two signal-only surfaces answer it:

  - ``duplicate_fact_scan`` — a report block that coarse-filters the
    map-covered pages for identical normalized headings shared by pages none
    of which declares ``authority: primary`` → ``FACT_NO_SINGLE_HOME``
    (signal, one per cluster). Coarse on purpose: it reports the duplicated
    fact and the pages holding it, never a similarity percentage (the
    doc-slop measurement lesson: raw percentages are not severity).
  - ``PARALLEL_ONTOLOGY_SUSPECTED`` — the #275 repro is "throw new documents
    into an unmapped directory and you have a parallel second docs system
    with zero mechanical trace". Trigger requires BOTH:
      (a) an uncovered ``.md`` under ``docs/`` with git-native activity
          evidence (untracked or modified per ``git status --porcelain``);
          with no git repository the scan has no evidence and skips;
      (b) that page's headings overlap the covered-pages heading pool
          (a full normalized heading match, or ≥ 2 shared distinct words).
    Declaration-missing is signal-only (L7): the scan never adds an ERROR
    and never changes exit semantics — ``has_error`` stays false and the
    CLI exits 0 with findings present.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_issue275_facts"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
SPEC = importlib.util.spec_from_file_location("docs_governance_facts", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def make_repo(name: str, pages: dict[str, str], map_links: list[str]) -> Path:
    """A committed docs system: AGENTS.md points at the map, the map links
    the given pages, every page is committed (so any later file is a
    git-native "new/active" candidate)."""
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    (base / "AGENTS.md").write_text("docs-map: docs/team-map.md\n", encoding="utf-8")
    (base / "docs" / "team-map.md").parent.mkdir(parents=True)
    (base / "docs" / "team-map.md").write_text(
        "# Team map\n\n" + "".join(f"- [{p}]({p})\n" for p in map_links),
        encoding="utf-8",
    )
    for rel, text in pages.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(base, "init", "-q")
    git(base, "add", "-A")
    git(base, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "init")
    return base


def codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


def signals(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"] if item.get("signal")}


PRIMARY = "---\ndoc-kind: prd\nauthority: primary\nauthority-id: {}\n---\n\n"
SUPPORTING = "---\ndoc-kind: prd\nauthority: supporting\n---\n\n"


class DuplicateFactScanTest(unittest.TestCase):
    def tearDown(self) -> None:
        pass

    def test_shared_heading_without_primary_reports_no_single_home(self) -> None:
        repo = make_repo(
            "fact-no-home",
            {
                "docs/prds/a.md": SUPPORTING + "# Checkout flow\n",
                "docs/prds/b.md": SUPPORTING + "# Checkout flow\n",
            },
            ["prds/a.md", "prds/b.md"],
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertIn("FACT_NO_SINGLE_HOME", signals(payload))
        block = payload["duplicate_fact_scan"]
        self.assertEqual(block["covered_scanned"], 2)
        self.assertEqual(len(block["no_single_home"]), 1)
        self.assertEqual(sorted(block["no_single_home"][0]["pages"]), ["docs/prds/a.md", "docs/prds/b.md"])

    def test_a_primary_page_owns_the_fact_and_stays_silent(self) -> None:
        repo = make_repo(
            "fact-owned",
            {
                "docs/prds/a.md": PRIMARY.format("checkout") + "# Checkout flow\n",
                "docs/prds/b.md": SUPPORTING + "# Checkout flow\n",
            },
            ["prds/a.md", "prds/b.md"],
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertNotIn("FACT_NO_SINGLE_HOME", codes(payload))

    def test_a_parallel_ontology_directory_is_suspected(self) -> None:
        """The #275 repro: an unmapped directory accumulates pages that
        restate covered facts — zero map trace, one mechanical signal."""
        repo = make_repo(
            "parallel-onto",
            {
                "docs/prds/payment.md": PRIMARY.format("payment") + "# Payment requirement\n",
            },
            ["prds/payment.md"],
        )
        # committed baseline, then a fresh untracked page outside the map
        (repo / "docs" / "ontology").mkdir()
        (repo / "docs" / "ontology" / "mirror.md").write_text(
            "# Payment requirement\n\nrestated here\n", encoding="utf-8"
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertIn("PARALLEL_ONTOLOGY_SUSPECTED", signals(payload))

    def test_an_unrelated_new_page_stays_silent(self) -> None:
        repo = make_repo(
            "parallel-unrelated",
            {
                "docs/prds/payment.md": PRIMARY.format("payment") + "# Payment requirement\n",
            },
            ["prds/payment.md"],
        )
        (repo / "docs" / "notes").mkdir()
        (repo / "docs" / "notes" / "lunch.md").write_text("# Lunch menu\n", encoding="utf-8")
        payload = TOOL.report(repo, validate_links=True)
        self.assertNotIn("PARALLEL_ONTOLOGY_SUSPECTED", codes(payload))

    def test_process_material_never_counts_as_a_parallel_candidate(self) -> None:
        repo = make_repo(
            "parallel-process",
            {
                "docs/prds/payment.md": PRIMARY.format("payment") + "# Payment requirement\n",
            },
            ["prds/payment.md"],
        )
        (repo / "docs" / "plans").mkdir()
        (repo / "docs" / "plans" / "active.md").write_text(
            "# Payment requirement\n", encoding="utf-8"
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertNotIn("PARALLEL_ONTOLOGY_SUSPECTED", codes(payload))

    def test_the_map_itself_is_never_a_scan_candidate(self) -> None:
        """Found on a real run: the map is not inside its own coverage (a map
        does not link itself), so it surfaced as an uncovered active page —
        and a map's navigation headings overlap the pool by construction.
        The map is the declaration surface, never a suspect."""
        repo = make_repo(
            "map-not-candidate",
            {
                "docs/prds/payment.md": PRIMARY.format("payment") + "# Payment requirement\n",
            },
            ["prds/payment.md"],
        )
        (repo / "docs" / "team-map.md").write_text(
            "# Team map\n\n## Payment requirement\n\n- [Payment](prds/payment.md)\n",
            encoding="utf-8",
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertNotIn("PARALLEL_ONTOLOGY_SUSPECTED", codes(payload))
        self.assertNotIn("FACT_NO_SINGLE_HOME", codes(payload))

    def test_adr_template_headings_are_exempt_from_the_fact_scan(self) -> None:
        """Found on a real run: ADRs share template headings ("写给未来"), so
        every two-ADR repository would report a permanent fact conflict that
        is template reuse, not drift. ADRs are historical authorities whose
        headings are shaped by the template — exempt from the cluster scan."""
        repo = make_repo(
            "adr-template",
            {
                "docs/prds/a.md": PRIMARY.format("a") + "# Checkout flow\n",
                "docs/zj-adr/0001.md": "---\ndoc-kind: adr\nstatus: accepted\n---\n# ADR 0001\n\n## 写给未来\n",
                "docs/zj-adr/0002.md": "---\ndoc-kind: adr\nstatus: accepted\n---\n# ADR 0002\n\n## 写给未来\n",
            },
            ["prds/a.md", "zj-adr/0001.md", "zj-adr/0002.md"],
        )
        payload = TOOL.report(repo, validate_links=True)
        self.assertNotIn("FACT_NO_SINGLE_HOME", codes(payload))


class L7SignalBoundaryTest(unittest.TestCase):
    """L7: the scan is an audit surface, not a gate — signal-only, and a
    consumer may escalate, but the tool itself never turns it into an ERROR."""

    def test_new_codes_are_classified_as_signals(self) -> None:
        self.assertIn("FACT_NO_SINGLE_HOME", TOOL.SIGNAL_CODES)
        self.assertIn("PARALLEL_ONTOLOGY_SUSPECTED", TOOL.SIGNAL_CODES)
        self.assertNotIn("FACT_NO_SINGLE_HOME", TOOL.ERROR_CODES)
        self.assertNotIn("PARALLEL_ONTOLOGY_SUSPECTED", TOOL.ERROR_CODES)

    def test_findings_never_make_the_report_error(self) -> None:
        repo = make_repo(
            "l7-exit",
            {
                "docs/prds/a.md": SUPPORTING + "# Checkout flow\n",
                "docs/prds/b.md": SUPPORTING + "# Checkout flow\n",
            },
            ["prds/a.md", "prds/b.md"],
        )
        (repo / "docs" / "ontology").mkdir()
        (repo / "docs" / "ontology" / "mirror.md").write_text("# Checkout flow\n", encoding="utf-8")
        payload = TOOL.report(repo, validate_links=True)
        self.assertIn("FACT_NO_SINGLE_HOME", signals(payload))
        self.assertIn("PARALLEL_ONTOLOGY_SUSPECTED", signals(payload))
        self.assertFalse(TOOL.has_error(payload))

    def test_cli_exit_stays_zero_with_findings_present(self) -> None:
        repo = make_repo(
            "l7-cli",
            {
                "docs/prds/a.md": SUPPORTING + "# Checkout flow\n",
                "docs/prds/b.md": SUPPORTING + "# Checkout flow\n",
            },
            ["prds/a.md", "prds/b.md"],
        )
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo), "--validate", "--proposal"],
            env=GIT_ENV, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        emitted = {item["code"] for item in payload["diagnostics"]}
        self.assertIn("FACT_NO_SINGLE_HOME", emitted)

    def test_gate_rules_let_a_consumer_escalate_both(self) -> None:
        rules = json.loads(
            (SKILL_ROOT / "references" / "gate-rules.json").read_text(encoding="utf-8")
        )
        self.assertIn("FACT_NO_SINGLE_HOME", rules["escalatable_signals"])
        self.assertIn("PARALLEL_ONTOLOGY_SUSPECTED", rules["escalatable_signals"])


if __name__ == "__main__":
    unittest.main()
