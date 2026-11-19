"""Issue #275 Fix 6: the default output zone anchors to the governed repo
root, not the launch directory.

Legacy behavior (the CWD hidden variable): ``DEFAULT_OUT`` was a relative
path, so ``out or DEFAULT_OUT`` resolved against wherever the CLI happened
to be started. The same skill run launched from two directories wrote two
different output zones, and the SKILL.md-declared checklist path
(``tmp/skills-outputs/zj-docs-ontology/<topic>/``) silently drifted.

Fixed contract:
  - no ``--out``            → ``{repo-root}/tmp/skills-outputs/zj-docs-ontology``
  - relative ``--out``      → ``{repo-root}/<out>``
  - absolute ``--out``      → honored as given
The launch directory is no longer an input to any output-zone resolution.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
MAP = SKILL_ROOT / "tests" / "fixtures" / "existing-map"
TOPIC = "out-zone-anchor"

TOOL_SPEC = importlib.util.spec_from_file_location("dg_out_base", SCRIPT)
assert TOOL_SPEC and TOOL_SPEC.loader
TOOL = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = TOOL
TOOL_SPEC.loader.exec_module(TOOL)


def run_cli(repo: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(repo), *args],
        capture_output=True, text=True, cwd=str(cwd),
    )


class DefaultOutAnchorsToRepoRootTest(unittest.TestCase):
    """End-to-end: emit with no --out from a foreign CWD must land under the
    governed repo root, and inspect must find it from any launch directory.

    Runs against a throwaway clone of the fixture: the output zone legitimately
    lands under the governed repo root, and the shared tracked fixture must
    never be mutated by a test run."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="out-zone-anchor-"))
        self.repo = self._tmp / "existing-map"
        shutil.copytree(MAP, self.repo)
        self.launch_dir = self._tmp / "launch-dir"
        self.launch_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_default_out_lands_under_repo_root_not_cwd(self) -> None:
        proc = run_cli(
            self.repo, self.launch_dir,
            "--proposal", "--topic", TOPIC, "--emit-checklist",
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        zone = self.repo / "tmp/skills-outputs/zj-docs-ontology" / TOPIC
        self.assertTrue((zone / "checklist.json").is_file(),
                        f"checklist must be under the repo root, got zone={zone}")
        self.assertFalse((self.launch_dir / "tmp").exists(),
                         "output must not follow the launch directory (CWD)")

    def test_checklist_findable_from_another_launch_dir(self) -> None:
        # Emit from directory A, then validate from directory B: the declared
        # path must resolve identically — the CWD variable is gone.
        run_cli(self.repo, self.launch_dir,
                "--proposal", "--topic", TOPIC, "--emit-checklist")
        other_dir = self._tmp / "other-launch"
        other_dir.mkdir()
        zone = self.repo / "tmp/skills-outputs/zj-docs-ontology" / TOPIC
        (zone / "architecture-validator.txt").write_text("ok\n", encoding="utf-8")
        proc = run_cli(self.repo, other_dir, "--validate", "--topic", TOPIC)
        self.assertEqual(0, proc.returncode, proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertNotIn(
            "EXEC_STEP5_ARTIFACT_MISSING",
            [d["code"] for d in payload["diagnostics"]],
        )

    def test_relative_out_also_anchors_to_repo_root(self) -> None:
        proc = run_cli(
            self.repo, self.launch_dir,
            "--proposal", "--topic", TOPIC, "--emit-checklist", "--out", "rel-zone",
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertTrue((self.repo / "rel-zone" / TOPIC / "checklist.json").is_file())
        self.assertFalse((self.launch_dir / "rel-zone").exists())


class DefaultOutHasNoCwdBypassTest(unittest.TestCase):
    """Regression pin for the Fix 6 ruling: DEFAULT_OUT is a relative path by
    design, so its ONLY legitimate consumers are resolve_out_base (which
    anchors it) and the argparse help string. Any other direct use would
    silently reintroduce the CWD hidden variable."""

    def test_default_out_is_only_consumed_through_resolve_out_base(self) -> None:
        lines = SCRIPT.read_text(encoding="utf-8").splitlines()

        def span_of(func_name: str) -> tuple[int, int]:
            start = next(i for i, ln in enumerate(lines) if ln.startswith(f"def {func_name}("))
            end = next((i for i in range(start + 1, len(lines))
                        if lines[i].startswith("def ") or lines[i].startswith("class ")), len(lines))
            return start, end

        resolve_span = span_of("resolve_out_base")
        offenders = [
            line for i, line in enumerate(lines)
            if "DEFAULT_OUT" in line
            and "DEFAULT_OUT = " not in line      # the definition itself
            and "help=" not in line               # argparse help string
            and not (resolve_span[0] <= i < resolve_span[1])  # inside the anchoring helper
        ]
        self.assertEqual(
            [], offenders,
            f"DEFAULT_OUT must only flow through resolve_out_base/help; found: {offenders}",
        )


class ResolveOutBaseUnitTest(unittest.TestCase):
    """The helper carries the contract; unit-pinned so the CLI wiring cannot
    regress independently of the helper."""

    def _repo(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="out-zone-unit-"))

    def test_none_gives_repo_anchored_default(self) -> None:
        repo = self._repo()
        base = TOOL.resolve_out_base(repo, None)
        self.assertEqual(repo / "tmp/skills-outputs/zj-docs-ontology", base)

    def test_relative_value_anchors_to_repo(self) -> None:
        repo = self._repo()
        self.assertEqual(repo / "rel-zone", TOOL.resolve_out_base(repo, Path("rel-zone")))

    def test_absolute_value_honored_as_given(self) -> None:
        repo = self._repo()
        absolute = repo / "abs-zone"
        self.assertEqual(absolute, TOOL.resolve_out_base(repo, absolute))


if __name__ == "__main__":
    unittest.main()
