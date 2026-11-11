"""Install-state seam: commands a SKILL.md teaches must run from a foreign cwd.

A skill is a published unit. The source repo is absent wherever it is installed,
and the agent's cwd is the *target project* (roadmap carriers land in its
docs/plans/). Commands that assume cwd == skill dir, or that rely on an env var
nobody declares, look correct in-repo and fail on every installed copy.

The public interface under test is the published command itself: tests read the
command out of the document, then execute it from a foreign cwd. No internal
function is imported and no script path literal is assumed, so moving scripts
into scripts/ later does not invalidate these tests.

NegativeProbe is the required two-way check: a gate that cannot fail on a
defect is a fake green. Broken documents are fed to the pure checker in memory,
so proving the gate is live never touches the working tree.
"""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven"
SKILL_MD = SKILL / "SKILL.md"
CLI_REF = SKILL / "references" / "roadmap-cli.md"
VENDOR_MD = SKILL / "viz" / "VENDOR.md"
VIZ_DEMO = SKILL / "demos" / "roadmap_viz_sample.json"

BASIS = "SKILL_ROOT"
PY = sys.executable

_CLI_COMMAND = re.compile(r"^(?:PYTHONPATH=\S+\s+)?python3?\s")


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """Non-comment lines inside fenced code blocks (continuations included)."""
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if inside and line.strip() and not line.lstrip().startswith("#"):
            lines.append(line.strip())
    return lines


def _dollar_vars(text: str) -> set[str]:
    return set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", "\n".join(_code_lines(text))))


def _foreign_env(tmpdir: str | None = None) -> dict[str, str]:
    """Only what an installed host provides: no skill path variables at all.

    tmpdir pins the child interpreter's scratch space, so a sandbox that denies
    the system temp dir cannot turn a real E2E run into a setup error.
    """
    env = os.environ.copy()
    env.pop(BASIS, None)
    env.pop("SKILL_DIR", None)
    # The IDE injects a sitecustomize shim via PYTHONPATH. It is a host-local
    # tool, not part of an installed skill's runtime; leaving it on the child's
    # path makes the smoke test measure the shim instead of the published
    # command (its temp-dir probe can fail under a restrictive sandbox).
    parts = [
        part for part in env.get("PYTHONPATH", "").split(os.pathsep)
        if part and "workbuddy" not in part.lower()
    ]
    if parts:
        env["PYTHONPATH"] = os.pathsep.join(parts)
    else:
        env.pop("PYTHONPATH", None)
    if tmpdir:
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = tmpdir
    return env


def _document_contract_errors(skill_md: str, cli_ref: str, vendor_md: str) -> list[str]:
    """Pure document checker → ERROR strings. No filesystem access, no cwd.

    Pure on purpose: NegativeProbe feeds it known-broken text to prove each
    finding actually fires, without mutating tracked files.
    """
    errors: list[str] = []
    if BASIS not in skill_md:
        errors.append("E_NO_BASIS: SKILL.md never declares SKILL_ROOT")
    declaration = [
        line for line in skill_md.splitlines() if BASIS in line and "$" + BASIS not in line
    ]
    if not any("SKILL.md" in line or "目录" in line for line in declaration):
        errors.append("E_BASIS_UNDEFINED: SKILL_ROOT is named but never defined in prose")

    undeclared = _dollar_vars(skill_md) - {BASIS}
    if undeclared:
        errors.append(f"E_UNDECLARED_VAR: commands rely on {sorted(undeclared)}")

    commands = [
        line
        for line in _code_lines(cli_ref)
        if "roadmap_cli.py" in line and _CLI_COMMAND.match(line)
    ]
    if not commands:
        errors.append("E_NO_CLI_COMMANDS: CLI reference teaches no runnable command")
    for line in commands:
        if "$" + BASIS not in line:
            errors.append(f"E_BARE_CLI: {line}")
    if "$SKILL_DIR" in cli_ref:
        errors.append("E_LEGACY_VAR: CLI reference still teaches $SKILL_DIR")

    for label, text in (("SKILL.md", skill_md), ("VENDOR.md", vendor_md)):
        # Prose lines count too: an inline `python -m viz.cli` in a vendor note
        # is taught just as loudly as one inside a fenced block.
        for line in text.splitlines():
            if "-m viz.cli" in line and "PYTHONPATH" not in line:
                errors.append(f"E_NO_MODULE_BASIS: {label}: {line.strip()}")
    return errors


def _live_errors() -> list[str]:
    return _document_contract_errors(_read(SKILL_MD), _read(CLI_REF), _read(VENDOR_MD))


def _has(errors: list[str], prefix: str) -> bool:
    return any(error.startswith(prefix) for error in errors)


class PublishedPathBasis(unittest.TestCase):
    """The published documents must declare how the agent resolves the root."""

    def test_skill_declares_one_path_basis_and_no_undeclared_vars(self):
        errors = _live_errors()
        self.assertFalse(_has(errors, "E_NO_BASIS"), errors)
        self.assertFalse(_has(errors, "E_BASIS_UNDEFINED"), errors)
        self.assertFalse(_has(errors, "E_UNDECLARED_VAR"), errors)

    def test_declared_basis_is_defined_in_terms_of_the_skill_directory(self):
        errors = _live_errors()
        self.assertFalse(_has(errors, "E_BASIS_UNDEFINED"), errors)

    def test_cli_reference_never_teaches_bare_script_names(self):
        errors = _live_errors()
        self.assertFalse(_has(errors, "E_NO_CLI_COMMANDS"), errors)
        self.assertFalse(_has(errors, "E_BARE_CLI"), errors)
        self.assertFalse(_has(errors, "E_LEGACY_VAR"), errors)

    def test_viz_commands_declare_a_module_search_basis(self):
        errors = _live_errors()
        self.assertFalse(_has(errors, "E_NO_MODULE_BASIS"), errors)


class InstalledCopyExecution(unittest.TestCase):
    """Execute the published commands from the target project's cwd."""

    def setUp(self):
        # Some sandboxes intermittently deny the system temp dir. Fall back to
        # the project's gitignored tmp/ zone (ADR 0010) instead of skipping:
        # a skipped install-state test is a fake green, not a pass.
        bases = [None]
        project_tmp = REPO / "tmp"
        try:
            project_tmp.mkdir(parents=True, exist_ok=True)
            bases.append(str(project_tmp))
        except OSError:
            pass
        last_error = None
        for base in bases:
            try:
                self.tmp = tempfile.TemporaryDirectory(
                    prefix="zj-install-smoke-", dir=base
                )
                break
            except OSError as exc:
                last_error = exc
        else:
            self.fail(f"no usable temporary directory: {last_error}")
        self.project = pathlib.Path(self.tmp.name) / "project"
        (self.project / "docs" / "plans").mkdir(parents=True)
        # A real target project has its own .git. Without it the CLI walks up,
        # finds this repository, and every smoke run shares one lease lock in
        # the repo's tmp/ zone — the lock, not the command under test, fails.
        for marker in (".git", "tmp"):
            try:
                (self.project / marker).mkdir(exist_ok=True)
            except OSError:
                pass

    def _env(self) -> dict[str, str]:
        return _foreign_env(str(self.project / "tmp"))

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except OSError:
            shutil.rmtree(self.tmp.name, ignore_errors=True)

    def _quick_start(self, needle: str) -> str:
        commands = [
            line
            for line in _code_lines(_read(SKILL_MD))
            if needle in line and "python" in line
        ]
        self.assertEqual(1, len(commands), f"expected one published {needle!r} command")
        return commands[0].replace("$" + BASIS, str(SKILL))

    def test_quick_start_init_runs_with_only_the_declared_basis(self):
        command = self._quick_start(" init ")
        self.assertTrue(
            command.startswith("python3 "),
            "published command must name an interpreter available on a bare CI host",
        )
        argv = shlex.split(command)
        # Which interpreter runs is host-supplied; the seam under test is that
        # the script path resolves from a foreign cwd with the declared basis.
        argv[0] = PY
        result = subprocess.run(
            argv,
            cwd=self.project,
            env=self._env(),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"published init command failed from a foreign cwd:\n{result.stdout}\n{result.stderr}",
        )
        self.assertTrue(
            (self.project / "docs" / "plans" / "roadmap.json").is_file(),
            "init reported success but no carrier landed in the target project",
        )

    def test_viz_module_runs_with_only_the_declared_basis(self):
        out = self.project / "view.html"
        env = self._env()
        env["PYTHONPATH"] = str(SKILL)
        result = subprocess.run(
            [PY, "-m", "viz.cli", str(VIZ_DEMO), "--out", str(out)],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"viz package failed with only the documented basis:\n{result.stdout}\n{result.stderr}",
        )
        self.assertTrue(out.is_file() and out.stat().st_size > 0, "no HTML view produced")


class NegativeProbe(unittest.TestCase):
    """Two-way gate verification: each defect class must make the checker red.

    Without these, a checker that always returns [] would pass every green run.
    Broken variants are built in memory; no tracked file is ever modified.
    """

    def setUp(self):
        self.skill = _read(SKILL_MD)
        self.cli = _read(CLI_REF)
        self.vendor = _read(VENDOR_MD)

    def _errors(self, *, skill: str | None = None, cli: str | None = None,
                vendor: str | None = None) -> list[str]:
        return _document_contract_errors(
            self.skill if skill is None else skill,
            self.cli if cli is None else cli,
            self.vendor if vendor is None else vendor,
        )

    def test_clean_documents_produce_no_errors(self):
        self.assertEqual([], self._errors())

    def test_undeclared_skill_dir_is_rejected(self):
        broken = self.skill.replace(BASIS, "SKILL_DIR")
        errors = self._errors(skill=broken)
        self.assertTrue(
            _has(errors, "E_NO_BASIS") and _has(errors, "E_UNDECLARED_VAR"),
            f"legacy undeclared variable slipped through: {errors}",
        )

    def test_missing_basis_definition_is_rejected(self):
        broken = self.skill.replace(
            "SKILL_ROOT 指**本 SKILL.md 所在目录的绝对路径**",
            "SKILL_ROOT is an internal detail",
        )
        errors = self._errors(skill=broken)
        self.assertTrue(
            _has(errors, "E_BASIS_UNDEFINED"),
            f"an undefined path basis slipped through: {errors}",
        )

    def test_bare_cli_command_is_rejected(self):
        # Derive the broken variant from whatever prefix the document publishes
        # today, so moving scripts into scripts/ cannot silently disarm the probe.
        broken = re.sub(
            r'python3 "\$SKILL_ROOT(?:/[^" ]*)?/roadmap_cli\.py"',
            "python roadmap_cli.py",
            self.cli,
        )
        self.assertNotEqual(
            self.cli, broken, "probe could not build a broken CLI variant"
        )
        errors = self._errors(cli=broken)
        self.assertTrue(
            _has(errors, "E_BARE_CLI"),
            f"a cwd-dependent CLI command slipped through: {errors}",
        )

    def test_legacy_variable_in_cli_reference_is_rejected(self):
        broken = self.cli.replace(
            "The Agent resolves `$SKILL_ROOT`", "The Agent resolves `$SKILL_DIR`"
        )
        errors = self._errors(cli=broken)
        self.assertTrue(
            _has(errors, "E_LEGACY_VAR"),
            f"the legacy variable slipped through: {errors}",
        )

    def test_viz_without_module_basis_is_rejected(self):
        broken = self.skill.replace(
            'PYTHONPATH="$SKILL_ROOT" python3 -m viz.cli', "python -m viz.cli"
        )
        errors = self._errors(skill=broken)
        self.assertTrue(
            _has(errors, "E_NO_MODULE_BASIS"),
            f"a viz command without a search basis slipped through: {errors}",
        )


if __name__ == "__main__":
    unittest.main()
