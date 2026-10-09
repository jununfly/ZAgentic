#!/usr/bin/env python3
"""Run local, deterministic regression checks for Composer Plan artifacts.

The runner exercises the validator at the Markdown boundary.  Every negative
case is written to a temporary copy of a known-good fixture, so the checked-in
Plans are never mutated.  It does not invoke a Plan capability, open a
network connection, run Git, or perform a handoff.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import io
import json
import os
import re
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_fixture import evaluate_fixture  # noqa: E402
from discover_catalog import discover_catalog  # noqa: E402
from generate_snapshot import build_snapshot  # noqa: E402
from validate_plan import (  # noqa: E402
    canonical_manifest_digest,
    field_value,
    parse_sections,
    validate_plan,
    validate_template_pin,
)


RESULT_SCHEMA = "zj-composer/regression-result/v1"
SNAPSHOT_DIGEST_RE = re.compile(r"(\*\*catalog_revision_or_digest:\*\*\s*`)([^`]+)(`)")


class RegressionError(RuntimeError):
    """A controlled regression case could not be constructed or checked."""


class EffectLedger:
    """Separate declared writes, blocked attempts, and effects that escaped."""

    def __init__(self) -> None:
        self.temporary_writes = 0
        self.result_writes = 0
        self.network_calls = 0
        self.git_publications = 0
        self.credential_reads = 0
        self.irreversible_actions = 0
        self.unapproved_side_effects = 0
        self.blocked_attempts = {
            "filesystem_writes": 0,
            "credential_reads": 0,
            "network_calls": 0,
            "git_publications": 0,
            "irreversible_actions": 0,
        }

    def write_temporary(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.temporary_writes += 1

    def block(self, category: str, message: str) -> None:
        # A rejected probe is evidence that the guard worked, not an escaped
        # side effect.  Keep attempts separate from effects so the final safety
        # verdict cannot report both ``safe`` and a non-zero effect count.
        self.blocked_attempts[category] += 1
        raise RegressionError(message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "declared": {
                "temporary_fixture_copies": self.temporary_writes,
                "regression_result": self.result_writes,
            },
            "network_calls": self.network_calls,
            "git_publications": self.git_publications,
            "credential_reads": self.credential_reads,
            "irreversible_actions": self.irreversible_actions,
            "unapproved_side_effects": self.unapproved_side_effects,
            "blocked_attempts": dict(self.blocked_attempts),
            "safe": all(
                value == 0
                for value in (
                    self.network_calls,
                    self.git_publications,
                    self.credential_reads,
                    self.irreversible_actions,
                    self.unapproved_side_effects,
                )
            ),
        }


@contextmanager
def side_effect_guards(
    ledger: EffectLedger,
    *,
    allowed_write_roots: Iterable[Path] = (),
    allowed_write_files: Iterable[Path] = (),
) -> Iterator[None]:
    """Fail closed around filesystem, credential, network, process, and delete effects."""

    roots = tuple(path.resolve() for path in allowed_write_roots)
    files = {path.resolve() for path in allowed_write_files}

    def normalized(value: Any) -> Optional[Path]:
        if isinstance(value, int):
            return None
        try:
            return Path(value).resolve()
        except (TypeError, OSError):
            return None

    def allowed(path: Optional[Path]) -> bool:
        if path is None:
            return True
        if path in files:
            return True
        return any(path == root or root in path.parents for root in roots)

    def credential_path(path: Optional[Path]) -> bool:
        if path is None:
            return False
        value = path.as_posix().casefold()
        names = ("/.ssh/", "/.aws/", "/.config/gh/", "/.netrc", "/.git-credentials", "/.npmrc", "/.pypirc")
        return any(name in value for name in names)

    def credential_key(value: Any) -> bool:
        return bool(re.search(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|PRIVATE_KEY|ACCESS_KEY)", str(value), re.IGNORECASE))

    def check_open(path_value: Any, mode: str) -> None:
        path = normalized(path_value)
        if credential_path(path):
            ledger.block("credential_reads", f"credential read is forbidden: {path}")
        if any(flag in mode for flag in ("w", "a", "x", "+")) and not allowed(path):
            ledger.block("filesystem_writes", f"filesystem write is outside the allowlist: {path}")

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection
    original_builtin_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open
    original_getenv = os.getenv
    environ_type = type(os.environ)
    original_environ_getitem = environ_type.__getitem__
    original_mutations = {
        name: getattr(os, name)
        for name in (
            "mkdir",
            "makedirs",
            "remove",
            "unlink",
            "rmdir",
            "rename",
            "replace",
            "link",
            "symlink",
            "chmod",
            "chown",
            "truncate",
            "utime",
            "mknod",
        )
        if hasattr(os, name)
    }
    original_rmtree = shutil.rmtree
    destructive_depth = [0]
    original_subprocess: dict[str, Any] = {
        name: getattr(subprocess, name)
        for name in ("run", "Popen", "call", "check_call", "check_output")
    }
    original_system = os.system
    original_popen = os.popen

    def blocked_network(*_args: Any, **_kwargs: Any) -> None:
        ledger.block("network_calls", "network access is forbidden during Composer regressions")

    def blocked_process(*args: Any, **_kwargs: Any) -> None:
        command = args[0] if args else ""
        rendered = " ".join(str(item) for item in command) if isinstance(command, (list, tuple)) else str(command)
        category = "git_publications" if re.search(r"(?:^|\s)(?:git\s+push|gh\s+pr\s+create)(?:\s|$)", rendered, re.IGNORECASE) else "filesystem_writes"
        ledger.block(category, f"subprocess is forbidden during Composer regressions: {rendered}")

    def guarded_builtin_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        check_open(file, mode)
        return original_builtin_open(file, mode, *args, **kwargs)

    def guarded_io_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        check_open(file, mode)
        return original_io_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        normalized_path = normalized(path)
        if credential_path(normalized_path):
            ledger.block("credential_reads", f"credential read is forbidden: {normalized_path}")
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if flags & write_flags and not allowed(normalized_path):
            ledger.block("filesystem_writes", f"filesystem write is outside the allowlist: {normalized_path}")
        return original_os_open(path, flags, *args, **kwargs)

    def guarded_getenv(key: str, default: Any = None) -> Any:
        if credential_key(key):
            ledger.block("credential_reads", f"credential environment read is forbidden: {key}")
        return original_getenv(key, default)

    def guarded_environ_getitem(environment: Any, key: str) -> Any:
        if credential_key(key):
            ledger.block("credential_reads", f"credential environment read is forbidden: {key}")
        return original_environ_getitem(environment, key)

    def mutation_wrapper(name: str, function: Any) -> Any:
        def guarded(path: Any, *args: Any, **kwargs: Any) -> Any:
            destructive = name in {"remove", "unlink", "rmdir"}
            targets = [normalized(path)]
            if name in {"rename", "replace"} and args:
                targets.append(normalized(args[0]))
            elif name in {"link", "symlink"} and args:
                # The source may be read-only repository content; only the new
                # directory entry is a filesystem mutation.
                targets = [normalized(args[0])]
            for target in targets:
                if destructive and destructive_depth[0] == 0 and not allowed(target):
                    ledger.block("irreversible_actions", f"irreversible action is outside the allowlist: {target}")
                if not destructive and not allowed(target):
                    ledger.block("filesystem_writes", f"filesystem mutation is outside the allowlist: {target}")
            return function(path, *args, **kwargs)

        return guarded

    def guarded_rmtree(path: Any, *args: Any, **kwargs: Any) -> Any:
        target = normalized(path)
        if not allowed(target):
            ledger.block("irreversible_actions", f"recursive delete is outside the allowlist: {target}")
        destructive_depth[0] += 1
        try:
            return original_rmtree(path, *args, **kwargs)
        finally:
            destructive_depth[0] -= 1

    socket.socket.connect = blocked_network  # type: ignore[assignment]
    socket.socket.connect_ex = blocked_network  # type: ignore[assignment]
    socket.create_connection = blocked_network  # type: ignore[assignment]
    builtins.open = guarded_builtin_open  # type: ignore[assignment]
    io.open = guarded_io_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    os.getenv = guarded_getenv  # type: ignore[assignment]
    environ_type.__getitem__ = guarded_environ_getitem  # type: ignore[assignment]
    for name, function in original_mutations.items():
        setattr(os, name, mutation_wrapper(name, function))
    shutil.rmtree = guarded_rmtree  # type: ignore[assignment]
    for name in original_subprocess:
        setattr(subprocess, name, blocked_process)
    os.system = blocked_process  # type: ignore[assignment]
    os.popen = blocked_process  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[assignment]
        socket.socket.connect_ex = original_connect_ex  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        builtins.open = original_builtin_open  # type: ignore[assignment]
        io.open = original_io_open  # type: ignore[assignment]
        os.open = original_os_open  # type: ignore[assignment]
        os.getenv = original_getenv  # type: ignore[assignment]
        environ_type.__getitem__ = original_environ_getitem  # type: ignore[assignment]
        for name, function in original_mutations.items():
            setattr(os, name, function)
        shutil.rmtree = original_rmtree  # type: ignore[assignment]
        for name, function in original_subprocess.items():
            setattr(subprocess, name, function)
        os.system = original_system  # type: ignore[assignment]
        os.popen = original_popen  # type: ignore[assignment]


def run_guard_probes(root: Path, temp_root: Path, ledger: EffectLedger) -> dict[str, Any]:
    """Attack every guard and require a controlled rejection before real work runs."""

    before = dict(ledger.blocked_attempts)
    probes = {
        "filesystem_writes": lambda: (temp_root.parent / "zj-composer-unauthorized-probe.txt").write_text(
            "must never land", encoding="utf-8"
        ),
        "credential_reads": lambda: (Path.home() / ".ssh" / "id_rsa").read_text(encoding="utf-8"),
        "network_calls": lambda: socket.create_connection(("127.0.0.1", 9), timeout=0.01),
        "git_publications": lambda: subprocess.run(["git", "push"], check=True),
        "irreversible_actions": lambda: os.unlink(root / "README.md"),
    }
    observed: dict[str, bool] = {}
    errors: dict[str, str] = {}
    for category, probe in probes.items():
        try:
            probe()
        except RegressionError as exc:
            observed[category] = ledger.blocked_attempts[category] == before[category] + 1
            errors[category] = str(exc)
        except Exception as exc:
            observed[category] = False
            errors[category] = f"unexpected rejection: {exc}"
        else:
            observed[category] = False
            errors[category] = "probe was not rejected"
    return {
        "expected": sorted(probes),
        "observed": observed,
        "messages": errors,
        "passed": all(observed.values()),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_files(fixture_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(fixture_dir).as_posix(): sha256(path)
        for path in sorted(fixture_dir.rglob("*"))
        if path.is_file()
    }


def preserve_newline(original: str, lines: list[str]) -> str:
    value = "\n".join(lines)
    return value + ("\n" if original.endswith("\n") else "")


def replace_field(
    text: str,
    section_name: str,
    field_name: str,
    replacement: str,
    *,
    step_number: Optional[int] = None,
) -> str:
    """Replace one Markdown field while staying inside the named section/step."""

    lines = text.splitlines()
    in_section = False
    active_step: Optional[int] = None
    prefix = f"- **{field_name}:**"
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            in_section = heading.group(1).strip() == section_name
            active_step = None
            continue
        if not in_section:
            continue
        step = re.match(r"^###\s+Step\s+(\d+)\s+[-—]", line, re.IGNORECASE)
        if step:
            active_step = int(step.group(1))
            continue
        if not line.lstrip().startswith(prefix):
            continue
        if step_number is not None and active_step != step_number:
            continue
        lines[index] = f"- **{field_name}:** {replacement}"
        return preserve_newline(text, lines)
    qualifier = f" in Step {step_number}" if step_number is not None else ""
    raise RegressionError(f"field {section_name}.{field_name}{qualifier} not found")


def append_field(
    text: str,
    section_name: str,
    field_name: str,
    suffix: str,
    *,
    step_number: Optional[int] = None,
) -> str:
    lines = text.splitlines()
    in_section = False
    active_step: Optional[int] = None
    prefix = f"- **{field_name}:**"
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            in_section = heading.group(1).strip() == section_name
            active_step = None
            continue
        if not in_section:
            continue
        step = re.match(r"^###\s+Step\s+(\d+)\s+[-—]", line, re.IGNORECASE)
        if step:
            active_step = int(step.group(1))
            continue
        if not line.lstrip().startswith(prefix):
            continue
        if step_number is not None and active_step != step_number:
            continue
        lines[index] = f"{line}{suffix}"
        return preserve_newline(text, lines)
    qualifier = f" in Step {step_number}" if step_number is not None else ""
    raise RegressionError(f"field {section_name}.{field_name}{qualifier} not found")


def mutate_gap(text: str) -> str:
    if "required skill：" in text:
        return text.replace("required skill：", "required skill:", 1)
    # The research fixture has no unresolved gap by design.  Turn its explicit
    # no-gap statement into the malformed ASCII form so both positive fixtures
    # exercise the same validator category.
    marker = "No unresolved capability gaps."
    if marker in text:
        return text.replace(marker, "required skill: missing capability", 1)
    raise RegressionError("fixture does not contain a gap marker or explicit no-gap statement")


def mutate_snapshot_digest(text: str) -> str:
    match = SNAPSHOT_DIGEST_RE.search(text)
    if not match:
        raise RegressionError("catalog_revision_or_digest field not found")
    return text[: match.start(2)] + ("0" * len(match.group(2))) + text[match.end(2) :]


def mutate_rejection(text: str) -> str:
    value = replace_field(text, "Identity", "status", "`rejected`")
    value = replace_field(value, "Identity", "human_review", "`rejected`")
    return replace_field(
        value,
        "Human checkpoints",
        "rejection_path",
        "Rejected because the Human declined the proposed capability boundary; preserve this Plan and do not execute.",
    )


def replace_provenance_segment(text: str, category: str, replacement: str) -> str:
    pattern = re.compile(rf"({re.escape(category)}\s*=\s*\[)[^]]*(\])", re.IGNORECASE)
    if not pattern.search(text):
        raise RegressionError(f"{category} provenance segment not found")
    return pattern.sub(rf"\1{replacement}\2", text, count=1)


def mutate_missing_suggested_provenance(text: str) -> str:
    marker = "## Gaps and suggestions\n"
    suggestion = (
        "\nsuggested capability：fixture-external-helper; source unverified; "
        "fit unknown; boundary: not installed\n"
    )
    if marker not in text:
        raise RegressionError("Gaps and suggestions section not found")
    return text.replace(marker, marker + suggestion, 1)


def mutate_missing_gap_provenance(text: str) -> str:
    value = replace_provenance_segment(text, "gap", "none declared")
    if "required skill：" not in value:
        marker = "No unresolved capability gaps."
        if marker not in value:
            raise RegressionError("no gap insertion point found")
        value = value.replace(marker, "required skill：fixture capability unavailable", 1)
    return value


def case_definitions() -> list[dict[str, Any]]:
    return [
        {
            "id": "malformed-unicode-gap",
            "description": "Reject an ASCII colon where the exact full-width gap marker is required.",
            "expected_category": "malformed_gap",
            "mutate": mutate_gap,
        },
        {
            "id": "missing-prerequisite",
            "description": "Reject a prerequisite declaration that explicitly remains unresolved.",
            "expected_category": "unresolved_prerequisite",
            "mutate": lambda text: replace_field(
                text,
                "Capability composition",
                "prerequisites",
                "missing prerequisite evidence",
                step_number=1,
            ),
        },
        {
            "id": "stale-snapshot-digest",
            "description": "Reject a Plan whose catalog digest no longer matches the frozen snapshot.",
            "expected_category": "provenance_digest_mismatch",
            "mutate": mutate_snapshot_digest,
        },
        {
            "id": "authority-bypass",
            "description": "Reject authority text that bypasses Human approval.",
            "expected_category": "authority_bypass",
            "mutate": lambda text: replace_field(
                text,
                "Handoff",
                "authority_statement",
                "Composer bypasses Human authority and may continue automatically.",
            ),
        },
        {
            "id": "second-authority",
            "description": "Reject a Plan that makes Composer a second durable authority.",
            "expected_category": "authority_bypass",
            "mutate": lambda text: replace_field(
                text,
                "Handoff",
                "authority_statement",
                "Composer is the second durable authority of record.",
            ),
        },
        {
            "id": "automatic-irreversible-action",
            "description": "Reject an automatic irreversible request before handoff.",
            "expected_category": "authority_bypass",
            "mutate": lambda text: replace_field(
                text,
                "Intent",
                "permission_boundary",
                "Composer automatically deletes production artifacts without Human approval.",
            ),
        },
        {
            "id": "secret-shaped-output",
            "description": "Reject a secret-shaped literal inserted into a capability output.",
            "expected_category": "secret-shaped-output",
            "mutate": lambda text: append_field(
                text,
                "Capability composition",
                "outputs",
                " api_key=not-a-real-secret",
                step_number=1,
            ),
        },
        {
            "id": "unapproved-write",
            "description": "Reject a permission boundary that permits a production write without a gate.",
            "expected_category": "unapproved_side_effect",
            "mutate": lambda text: replace_field(
                text,
                "Intent",
                "permission_boundary",
                "Write production files.",
            ),
        },
        {
            "id": "conflicting-alternatives",
            "description": "Reject retained alternatives until a Human makes the explicit choice.",
            "expected_category": "unresolved_conflict",
            "mutate": lambda text: replace_field(
                text,
                "Capability composition",
                "excluded_alternatives",
                "CONFLICT: Human choice required between option A and option B.",
                step_number=1,
            ),
        },
        {
            "id": "missing-excluded-provenance",
            "description": "Reject excluded alternatives without a class-scoped source mapping.",
            "expected_category": "provenance_incomplete_excluded",
            "mutate": lambda text: replace_provenance_segment(text, "excluded", "none declared"),
        },
        {
            "id": "missing-suggested-provenance",
            "description": "Reject a bounded suggestion without a class-scoped source mapping.",
            "expected_category": "provenance_incomplete_suggested",
            "mutate": mutate_missing_suggested_provenance,
        },
        {
            "id": "missing-gap-provenance",
            "description": "Reject a required-skill gap without a class-scoped source mapping.",
            "expected_category": "provenance_incomplete_gap",
            "mutate": mutate_missing_gap_provenance,
        },
    ]


def diagnostic_categories(validation: dict[str, Any]) -> list[str]:
    return sorted({item.get("category") for item in validation.get("diagnostics", []) if item.get("category")})


def inspect_handoff(plan_path: Path) -> dict[str, Any]:
    """Check the textual handoff contract without dispatching anything."""

    text = plan_path.read_text(encoding="utf-8")
    sections, _ = parse_sections(text.splitlines(), [])
    handoff = sections.get("Handoff", {})
    authority, _ = field_value(handoff, "authority_statement")
    preconditions, _ = field_value(handoff, "handoff_preconditions")
    authority_text = (authority or "").casefold()
    precondition_text = (preconditions or "").casefold()
    authority_ok = bool(
        re.search(r"composer.{0,60}(?:no|without).{0,30}(?:execution|authority)", authority_text)
        or "无执行权" in authority_text
    )
    preconditions_ok = (
        "human approval" in precondition_text
        and "passing plan validation" in precondition_text
        and ("oracle" in precondition_text or "fixture" in precondition_text)
    )
    return {
        "authority_statement_present": bool(authority),
        "authority_preserves_no_execution_authority": authority_ok,
        "handoff_preconditions_present": bool(preconditions),
        "handoff_preconditions_guarded": preconditions_ok,
        "passed": authority_ok and preconditions_ok,
    }


def run_negative_case(
    fixture_id: str,
    plan_text: str,
    case: dict[str, Any],
    temp_root: Path,
    ledger: EffectLedger,
) -> dict[str, Any]:
    case_dir = temp_root / fixture_id / str(case["id"])
    plan_path = case_dir / "plan.md"
    try:
        mutated = case["mutate"](plan_text)
        if mutated == plan_text:
            raise RegressionError("mutation did not change the Plan")
        ledger.write_temporary(plan_path, mutated)
        validation = validate_plan(plan_path, ROOT, None)
        categories = diagnostic_categories(validation)
        expected = str(case["expected_category"])
        passed = not validation.get("valid", True) and expected in categories
        return {
            "id": case["id"],
            "description": case["description"],
            "expected_category": expected,
            "observed_categories": categories,
            "validator_valid": bool(validation.get("valid")),
            "passed": passed,
        }
    except Exception as exc:  # keep all cases visible in the result
        return {
            "id": case["id"],
            "description": case["description"],
            "expected_category": case["expected_category"],
            "observed_categories": [],
            "validator_valid": None,
            "passed": False,
            "error": str(exc),
        }


def run_rejected_case(
    fixture_id: str,
    plan_text: str,
    temp_root: Path,
    ledger: EffectLedger,
) -> dict[str, Any]:
    case_dir = temp_root / fixture_id / "rejected-plan"
    plan_path = case_dir / "plan.md"
    try:
        rejected_text = mutate_rejection(plan_text)
        ledger.write_temporary(plan_path, rejected_text)
        validation = validate_plan(plan_path, ROOT, None)
        sections, _ = parse_sections(rejected_text.splitlines(), [])
        identity = sections.get("Identity", {})
        status, _ = field_value(identity, "status")
        review, _ = field_value(identity, "human_review")
        rejection_reason, _ = field_value(sections.get("Human checkpoints", {}), "rejection_path")
        preserved = plan_path.is_file() and plan_path.read_text(encoding="utf-8") == rejected_text
        handoff_eligible = bool(validation.get("handoff", {}).get("eligible"))
        reason_preserved = bool(rejection_reason and "because" in rejection_reason.casefold())
        passed = (
            bool(validation.get("valid"))
            and status == "rejected"
            and review == "rejected"
            and preserved
            and reason_preserved
            and not handoff_eligible
        )
        return {
            "id": "rejected-plan",
            "expected": {
                "status": "rejected",
                "human_review": "rejected",
                "preserved": True,
                "rejection_reason_preserved": True,
                "handoff_eligible": False,
            },
            "observed": {
                "validator_valid": bool(validation.get("valid")),
                "status": status,
                "human_review": review,
                "preserved": preserved,
                "rejection_reason": rejection_reason,
                "rejection_reason_preserved": reason_preserved,
                "handoff_eligible": handoff_eligible,
            },
            "passed": passed,
        }
    except Exception as exc:
        return {
            "id": "rejected-plan",
            "expected": {
                "status": "rejected",
                "human_review": "rejected",
                "preserved": True,
                "rejection_reason_preserved": True,
                "handoff_eligible": False,
            },
            "observed": {},
            "passed": False,
            "error": str(exc),
        }


def replace_section_body(text: str, section_name: str, body: str) -> str:
    pattern = re.compile(
        rf"(^##\s+{re.escape(section_name)}\s*$\n)(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(text):
        raise RegressionError(f"section {section_name!r} not found")
    return pattern.sub(lambda match: match.group(1) + "\n" + body.rstrip() + "\n\n", text, count=1)


def run_no_match_case(plan_text: str, temp_root: Path, ledger: EffectLedger) -> dict[str, Any]:
    gap_line = "required skill：跨工具组合的统一执行能力"
    plan = replace_section_body(
        plan_text,
        "Capability composition",
        "No installed capability matches the requested need.",
    )
    plan = replace_section_body(plan, "Gaps and suggestions", gap_line)
    plan = replace_provenance_segment(plan, "selected", "none declared")
    plan = replace_provenance_segment(plan, "excluded", "none declared")
    plan = replace_provenance_segment(plan, "suggested", "none declared")
    # Exercise the real boundary: even an explicitly approved/passed artifact
    # cannot hand off when it contains only an unresolved required-skill gap.
    plan = replace_field(plan, "Identity", "status", "`approved`")
    plan = replace_field(plan, "Identity", "human_review", "`approved`")
    plan = replace_field(plan, "Verification", "plan_acceptance", "`passed`")
    path = temp_root / "no-match" / "plan.md"
    ledger.write_temporary(path, plan)
    validation = validate_plan(path, ROOT, None)
    sections, _ = parse_sections(plan.splitlines(), [])
    gap_body = [
        value
        for _, value in (
            (line_no, plan.splitlines()[line_no - 1].strip())
            for line_no in range(
                sections["Gaps and suggestions"]["line"] + 1,
                sections["Human checkpoints"]["line"],
            )
        )
        if value
    ]
    handoff_eligible = bool(validation.get("handoff", {}).get("eligible"))
    passed = bool(validation.get("valid")) and gap_body == [gap_line] and not handoff_eligible
    return {
        "id": "no-match",
        "gap_output": gap_body,
        "exact_required_skill_only": gap_body == [gap_line],
        "handoff_eligible": handoff_eligible,
        "handoff_reasons": validation.get("handoff", {}).get("reasons", []),
        "validator_valid": bool(validation.get("valid")),
        "passed": passed,
    }


def write_catalog_fixture(fixture_root: Path, ledger: EffectLedger) -> dict[Path, str]:
    """Create the smallest recursive public catalog that uses every declaration surface."""

    skill_name = "zj-nested-skill"
    files = {
        fixture_root / "README.md": (
            "- [zj-guide](./skills/engineering/zj-guide/SKILL.md) — fixture guide.\n"
            "- [zj-nested-skill](./skills/productivity/group/zj-nested-skill/SKILL.md) — nested fixture.\n"
        ),
        fixture_root / "skills/engineering/README.md": (
            "- [zj-guide](./zj-guide/SKILL.md) — fixture guide.\n"
        ),
        fixture_root / "skills/codebase-docs/README.md": "# codebase docs\n",
        fixture_root / "skills/productivity/README.md": (
            "- [zj-nested-skill](./group/zj-nested-skill/SKILL.md) — nested fixture.\n"
        ),
        fixture_root / "skills/misc/README.md": "# misc\n",
        fixture_root / "skills/research/README.md": "# research\n",
        fixture_root / "skills/engineering/zj-guide/SKILL.md": (
            "---\nname: zj-guide\ndescription: Route fixture capabilities.\n---\n"
            f"Available capability: {skill_name}.\n"
        ),
        fixture_root / "scripts/zagentic-skills-list": f"zj-guide\n{skill_name}\n",
        fixture_root / "skills/productivity/group/zj-nested-skill/SKILL.md": (
            "---\n"
            "name: zj-nested-skill\n"
            "description: Exercise recursive Composer discovery.\n"
            "inputs:\n  - nested request\n"
            "outputs:\n  - nested result\n"
            "dependencies:\n  - zj-guide\n"
            "boundaries:\n  - local fixture only\n"
            "---\n"
            "# Nested skill\n"
        ),
        fixture_root / "skills/productivity/group/zj-nested-skill/scripts/original_path.py": (
            "def run():\n"
            "    return {\n"
            "        'capability': 'zj-nested-skill',\n"
            "        'output': 'original-path-ok',\n"
            "    }\n"
        ),
    }
    for path, content in files.items():
        ledger.write_temporary(path, content)
    return files


def canonical_json_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def execute_original_fixture_path(fixture_root: Path) -> dict[str, Any]:
    """Execute the synthetic pre-Composer capability through its real entrypoint."""

    entrypoint = (
        fixture_root
        / "skills/productivity/group/zj-nested-skill/scripts/original_path.py"
    )
    namespace = runpy.run_path(str(entrypoint))
    runner = namespace.get("run")
    if not callable(runner):
        raise RegressionError(f"original fixture entrypoint has no run(): {entrypoint}")
    output = runner()
    if not isinstance(output, dict):
        raise RegressionError("original fixture entrypoint must return a JSON object")
    return output


def run_recursive_catalog_regression(temp_root: Path, ledger: EffectLedger) -> dict[str, Any]:
    fixture = temp_root / "recursive-catalog"
    write_catalog_fixture(fixture, ledger)
    catalog = discover_catalog(fixture)
    record = next((item for item in catalog["skills"] if item.get("name") == "zj-nested-skill"), None)
    snapshot = build_snapshot(fixture)
    source_path = "skills/productivity/group/zj-nested-skill/SKILL.md"
    manifest_paths = {item.get("path") for item in snapshot["source"]["files"]}
    digest_verified = (
        canonical_manifest_digest(snapshot["source"]["files"])
        == snapshot["source"]["content_digest"]
        and snapshot["snapshot_id"] == f"catalog-v1-{snapshot['source']['content_digest']}"
    )
    passed = bool(
        record
        and record.get("directory") == "group/zj-nested-skill"
        and record.get("source_reference") == source_path
        and record.get("declared")
        == {
            "inputs": ["nested request"],
            "outputs": ["nested result"],
            "dependencies": ["zj-guide"],
            "boundaries": ["local fixture only"],
        }
        and record.get("metadata_warnings") == []
        and all(record.get("declarations", {}).values())
        and source_path in manifest_paths
        and digest_verified
    )
    return {
        "nested_skill_discovered": record is not None,
        "record": record,
        "snapshot_contains_nested_source": source_path in manifest_paths,
        "snapshot_digest_verified": digest_verified,
        "passed": passed,
    }


def run_template_pinning_regression(root: Path, temp_root: Path, ledger: EffectLedger) -> dict[str, Any]:
    fixture = temp_root / "template-pinning"
    relative_template = Path("skills/productivity/zj-composer/references/plan-template.md")
    relative_registry = Path("skills/productivity/zj-composer/references/template-versions.json")
    ledger.write_temporary(fixture / relative_template, (root / relative_template).read_text(encoding="utf-8"))
    ledger.write_temporary(fixture / relative_registry, (root / relative_registry).read_text(encoding="utf-8"))
    baseline: list[Any] = []
    validate_template_pin(fixture, "1", baseline)
    ledger.write_temporary(
        fixture / relative_template,
        (fixture / relative_template).read_text(encoding="utf-8") + "\nSilent template mutation.\n",
    )
    mutated: list[Any] = []
    validate_template_pin(fixture, "1", mutated)
    categories = sorted(item.category for item in mutated)
    return {
        "baseline_categories": sorted(item.category for item in baseline),
        "mutated_categories": categories,
        "existing_plan_reinterpreted": False,
        "passed": not baseline and "template_version_mismatch" in categories,
    }


def run_stale_source_regression(
    root: Path,
    fixture_dir: Path,
    temp_root: Path,
    ledger: EffectLedger,
) -> dict[str, Any]:
    fixture = temp_root / "stale-source"
    plan_text = (fixture_dir / "plan.md").read_text(encoding="utf-8")
    snapshot_id = json.loads((fixture_dir / "input.json").read_text(encoding="utf-8"))["snapshot_id"]
    snapshot_path = root / "skills-outputs/zj-composer/catalog-snapshots" / f"{snapshot_id}.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    sections, _ = parse_sections(plan_text.splitlines(), [])
    selected_names = [
        step["fields"]["skill_or_workflow"][0]
        for step in sections["Capability composition"]["steps"]
    ]
    catalog = {item.get("name"): item for item in snapshot["catalog"]["skills"]}
    selected_paths = [Path(catalog[name]["path"]) for name in selected_names]
    for relative in selected_paths:
        ledger.write_temporary(fixture / relative, (root / relative).read_text(encoding="utf-8"))
    for relative in (
        Path("skills/productivity/zj-composer/references/plan-template.md"),
        Path("skills/productivity/zj-composer/references/template-versions.json"),
    ):
        ledger.write_temporary(fixture / relative, (root / relative).read_text(encoding="utf-8"))
    stale_path = selected_paths[0]
    ledger.write_temporary(
        fixture / stale_path,
        (fixture / stale_path).read_text(encoding="utf-8") + "\n# changed after snapshot\n",
    )
    stale_plan = fixture / "stale-plan.md"
    ledger.write_temporary(stale_plan, plan_text)
    stale_validation = validate_plan(stale_plan, fixture, snapshot_path)

    reviewed_text = replace_field(plan_text, "Identity", "status", "`approved`")
    reviewed_text = replace_field(reviewed_text, "Identity", "human_review", "`approved`")
    reviewed_text = replace_field(reviewed_text, "Verification", "plan_acceptance", "`passed`")
    reviewed_text = replace_field(
        reviewed_text,
        "Evidence and provenance",
        "unknowns",
        f"stale source reviewed: {stale_path.as_posix()}; Human explicitly accepts the pinned contract for this handoff.",
    )
    reviewed_plan = fixture / "reviewed-plan.md"
    ledger.write_temporary(reviewed_plan, reviewed_text)
    reviewed_validation = validate_plan(reviewed_plan, fixture, snapshot_path)
    stale_categories = diagnostic_categories(stale_validation)
    reviewed_categories = diagnostic_categories(reviewed_validation)
    passed = bool(
        not stale_validation.get("valid")
        and "provenance_stale" in stale_categories
        and not stale_validation.get("handoff", {}).get("eligible")
        and reviewed_validation.get("valid")
        and "provenance_stale_reviewed" in reviewed_categories
        and reviewed_validation.get("handoff", {}).get("eligible")
    )
    return {
        "changed_source": stale_path.as_posix(),
        "stale": {
            "categories": stale_categories,
            "validator_valid": bool(stale_validation.get("valid")),
            "handoff_eligible": bool(stale_validation.get("handoff", {}).get("eligible")),
        },
        "explicit_human_review": {
            "categories": reviewed_categories,
            "validator_valid": bool(reviewed_validation.get("valid")),
            "handoff_eligible": bool(reviewed_validation.get("handoff", {}).get("eligible")),
        },
        "passed": passed,
    }


def run_removal_regression(
    root: Path,
    temp_root: Path,
    plan_text: str,
    ledger: EffectLedger,
) -> dict[str, Any]:
    simulation = temp_root / "removal-regression"
    baseline_files = write_catalog_fixture(simulation, ledger)
    catalog_before = discover_catalog(simulation)
    original_before = execute_original_fixture_path(simulation)
    original_digest_before = canonical_json_digest(original_before)
    historical = simulation / "historical-artifacts" / "composer-v0-plan.md"
    ledger.write_temporary(historical, plan_text)
    historical_digest = sha256(historical)

    experimental = simulation / "skills/productivity/zj-composer"
    ledger.write_temporary(
        experimental / "SKILL.md",
        (root / "skills/productivity/zj-composer/SKILL.md").read_text(encoding="utf-8"),
    )
    index_paths = (
        simulation / "README.md",
        simulation / "skills/productivity/README.md",
        simulation / "skills/engineering/zj-guide/SKILL.md",
        simulation / "scripts/zagentic-skills-list",
    )
    additions = (
        "- [zj-composer](./skills/productivity/zj-composer/SKILL.md) — experiment.\n",
        "- [zj-composer](./zj-composer/SKILL.md) — experiment.\n",
        "Available capability: zj-composer.\n",
        "zj-composer\n",
    )
    for path, addition in zip(index_paths, additions):
        ledger.write_temporary(path, path.read_text(encoding="utf-8") + addition)
    experimental_visible = any(
        item.get("name") == "zj-composer" for item in discover_catalog(simulation)["skills"]
    )

    shutil.rmtree(experimental)
    for path in index_paths:
        ledger.write_temporary(path, baseline_files[path])
    catalog_after = discover_catalog(simulation)
    original_after = execute_original_fixture_path(simulation)
    original_digest_after = canonical_json_digest(original_after)
    historical_preserved = historical.is_file() and sha256(historical) == historical_digest
    original_path = simulation / "skills/productivity/group/zj-nested-skill/SKILL.md"
    output_equal = original_before == original_after and original_digest_before == original_digest_after
    catalog_restored = catalog_before == catalog_after
    passed = bool(
        experimental_visible
        and not experimental.exists()
        and historical_preserved
        and original_path.is_file()
        and output_equal
        and catalog_restored
    )
    return {
        "original_path_executed_before_removal": isinstance(original_before, dict),
        "original_path_executed_after_removal": isinstance(original_after, dict),
        "original_output_digest_before": original_digest_before,
        "original_output_digest_after": original_digest_after,
        "original_output_equal": output_equal,
        "catalog_restored": catalog_restored,
        "experimental_layer_was_discoverable": experimental_visible,
        "experimental_layer_removed": not experimental.exists(),
        "historical_artifact_preserved": historical_preserved,
        "original_capability_path_preserved": original_path.is_file(),
        "real_repository_touched": False,
        "passed": passed,
    }


def run_regressions(root: Path, output: Path) -> dict[str, Any]:
    global ROOT
    ROOT = root.resolve()
    ledger = EffectLedger()
    fixture_root = ROOT / "skills-outputs" / "zj-composer"
    fixture_dirs = [
        fixture_root / "external-repository-research",
        fixture_root / "tool-combination-design",
    ]
    before = {path.name: fixture_files(path) for path in fixture_dirs}
    source_paths = [
        ROOT / "skills/productivity/zj-composer/SKILL.md",
        ROOT / "skills/productivity/zj-composer/references/plan-template.md",
        ROOT / "skills/productivity/zj-composer/references/template-versions.json",
        ROOT / "skills/productivity/zj-composer/scripts/discover_catalog.py",
        ROOT / "skills/productivity/zj-composer/scripts/generate_snapshot.py",
        ROOT / "skills/productivity/zj-composer/scripts/validate_plan.py",
        ROOT / "skills/productivity/zj-composer/scripts/evaluate_fixture.py",
        ROOT / "skills/productivity/zj-composer/scripts/run_regressions.py",
        ROOT / "docs/plans/roadmap-zj-composer.json",
    ]
    # Include every path pinned by the active catalog snapshot in the integrity
    # check.  This catches an accidental mutation of a source file even when a
    # fixture Plan itself remains unchanged.
    for fixture_dir in fixture_dirs:
        fixture_input = json.loads((fixture_dir / "input.json").read_text(encoding="utf-8"))
        snapshot_id = fixture_input.get("snapshot_id")
        snapshot_path = fixture_root / "catalog-snapshots" / f"{snapshot_id}.json"
        source_paths.append(snapshot_path)
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for item in snapshot.get("source", {}).get("files", []):
            relative = item.get("path") if isinstance(item, dict) else None
            if isinstance(relative, str):
                source_paths.append(ROOT / relative)
    source_paths = list(dict.fromkeys(source_paths))
    source_before = {path.as_posix(): sha256(path) for path in source_paths}
    fixtures_result: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="zj-composer-regression-") as temp_name:
        temp_root = Path(temp_name)
        with side_effect_guards(ledger, allowed_write_roots=(temp_root,)):
            guard_probes = run_guard_probes(ROOT, temp_root, ledger)
            for fixture_dir in fixture_dirs:
                fixture_id = fixture_dir.name
                fixture_eval = evaluate_fixture(fixture_dir, ROOT)
                plan_path = fixture_dir / "plan.md"
                plan_text = plan_path.read_text(encoding="utf-8")
                handoff = inspect_handoff(plan_path)
                negative_cases = [
                    run_negative_case(fixture_id, plan_text, case, temp_root, ledger)
                    for case in case_definitions()
                ]
                rejected = run_rejected_case(fixture_id, plan_text, temp_root, ledger)
                fixtures_result.append(
                    {
                        "fixture_id": fixture_id,
                        "positive": {
                            "valid": bool(fixture_eval.get("valid")),
                            "validator_valid": bool(fixture_eval.get("validation", {}).get("valid")),
                            "oracle_valid": bool(fixture_eval.get("oracle", {}).get("valid")),
                            "errors": fixture_eval.get("validation", {}).get("summary", {}).get("errors"),
                            "warnings": fixture_eval.get("validation", {}).get("summary", {}).get("warnings"),
                        },
                        "handoff_contract": handoff,
                        "negative_cases": negative_cases,
                        "rejected_plan": rejected,
                    }
                )
            no_match = run_no_match_case(
                (fixture_dirs[1] / "plan.md").read_text(encoding="utf-8"),
                temp_root,
                ledger,
            )
            recursive_catalog = run_recursive_catalog_regression(temp_root, ledger)
            template_pinning = run_template_pinning_regression(ROOT, temp_root, ledger)
            stale_source = run_stale_source_regression(ROOT, fixture_dirs[1], temp_root, ledger)
            removal = run_removal_regression(
                ROOT,
                temp_root,
                (fixture_dirs[0] / "plan.md").read_text(encoding="utf-8"),
                ledger,
            )
    temporary_directory_removed = not temp_root.exists()

    after = {path.name: fixture_files(path) for path in fixture_dirs}
    source_after = {path.as_posix(): sha256(path) for path in source_paths}
    fixture_integrity = before == after
    source_integrity = source_before == source_after
    path_integrity = all(
        fixture_root.joinpath(fixture_id, "plan.md").is_file()
        for fixture_id in ("external-repository-research", "tool-combination-design")
    )
    negative_passed = all(
        case["passed"]
        for fixture in fixtures_result
        for case in fixture["negative_cases"]
    )
    rejected_passed = all(fixture["rejected_plan"]["passed"] for fixture in fixtures_result)
    handoff_passed = all(fixture["handoff_contract"]["passed"] for fixture in fixtures_result)
    positive_passed = all(
        fixture["positive"]["valid"]
        and fixture["positive"]["validator_valid"]
        and fixture["positive"]["oracle_valid"]
        and fixture["positive"]["errors"] == 0
        and fixture["positive"]["warnings"] == 0
        for fixture in fixtures_result
    )
    result = {
        "schema": RESULT_SCHEMA,
        "fixtures": fixtures_result,
        "checks": {
            "positive_fixtures_pass": positive_passed,
            "negative_categories_pass": negative_passed,
            "rejected_plans_preserved_and_not_handoffable": rejected_passed,
            "source_integrity": source_integrity,
            "fixture_path_integrity": path_integrity and fixture_integrity,
            "authority_and_handoff_guarded": handoff_passed and rejected_passed,
            "no_match_stops_before_handoff": no_match,
            "recursive_catalog_and_snapshot": recursive_catalog,
            "template_version_pinning": template_pinning,
            "stale_source_review_protocol": stale_source,
            "side_effect_guard_probes": guard_probes,
            "removal_regression": removal,
            "temporary_directory_removed": temporary_directory_removed,
        },
    }
    ledger.result_writes = 1
    result["side_effects"] = ledger.as_dict()
    result["valid"] = bool(
        positive_passed
        and negative_passed
        and rejected_passed
        and handoff_passed
        and source_integrity
        and fixture_integrity
        and path_integrity
        and no_match["passed"]
        and recursive_catalog["passed"]
        and template_pinning["passed"]
        and stale_source["passed"]
        and guard_probes["passed"]
        and removal["passed"]
        and temporary_directory_removed
        and ledger.as_dict()["safe"]
    )
    if not output.parent.is_dir():
        raise RegressionError(f"result allowlist parent does not exist: {output.parent}")
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with side_effect_guards(ledger, allowed_write_files=(output,)):
        output.write_text(rendered, encoding="utf-8")
    return result


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Composer negative, safety, handoff, and removal regressions.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[4] / "skills-outputs/zj-composer/regression/regression-result.json",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output = args.output.resolve()
    result = run_regressions(root, output)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
