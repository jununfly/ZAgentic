#!/usr/bin/env python3
"""Check the deterministic contract of a technical design review Markdown file.

This deliberately does not judge prose quality. It reports structural omissions and
known anti-patterns so a human can spend review time on meaning and trade-offs.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_HEADINGS = (
    "one-page overview",
    "problem and goals",
    "design",
    "metrics and experiments",
    "rollout, recovery, and lifecycle",
    "principle considerations",
    "testing and validation",
    "open decisions",
    "review record",
)

STATUS_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:decision|conclusion|review status)\s*:\s*"
    r"(approve|revise|reject|defer)\b"
)
HEADING_RE = re.compile(r"(?im)^\s*#{1,6}\s+(.+?)\s*#*\s*$")
EVIDENCE_RE = re.compile(
    r"(?im)(?:\b(?:evidence|source|citation)\s*:\s*\S+|\[[^\]]+\]\([^\)]+\)|https?://\S+)"
)
UNKNOWN_AS_ABSENT_RE = re.compile(
    r"(?i)\bunknown\s*(?:=|means|is|should be)\s*absent\b"
)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    path: str
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def _headings(text: str) -> set[str]:
    return {match.group(1).strip().lower() for match in HEADING_RE.finditer(text)}


def _has_marker(text: str, *terms: str) -> bool:
    lowered = text.lower()
    return all(term.lower() in lowered for term in terms)


def _issue(code: str, message: str) -> Issue:
    return Issue(code=code, message=message)


def validate_text(text: str, path: str = "<memory>") -> ValidationResult:
    """Validate one review document and return structured errors/warnings."""

    errors: list[Issue] = []
    warnings: list[Issue] = []
    headings = _headings(text)
    lowered = text.lower()

    for required in REQUIRED_HEADINGS:
        if required not in headings:
            errors.append(_issue("missing-heading", f"missing heading: {required}"))

    if not _has_marker(text, "goal", "non-goal"):
        errors.append(_issue("missing-goals", "include both goals and non-goals"))
    if "alternative" not in lowered:
        errors.append(_issue("missing-alternatives", "state alternatives considered"))
    if "owner" not in lowered:
        errors.append(_issue("missing-owner", "name an owner for decisions or risks"))
    if not _has_marker(text, "baseline", "unit", "method"):
        errors.append(
            _issue("incomplete-metrics", "metrics must name a baseline, unit, and method")
        )
    if "threshold" not in lowered and "target" not in lowered:
        errors.append(_issue("missing-threshold", "metrics or validation need a target/threshold"))
    if "scenario" not in lowered and "fixture" not in lowered:
        errors.append(_issue("missing-scenario", "name a reproducible validation scenario"))
    if "rollout" not in lowered:
        errors.append(_issue("missing-rollout", "describe rollout or release strategy"))
    if "rollback" not in lowered:
        errors.append(_issue("missing-rollback", "describe rollback or recovery conditions"))
    if "blocking" not in lowered:
        errors.append(_issue("missing-blocking-label", "classify blocking findings"))
    if "non-blocking" not in lowered and "nonblocking" not in lowered:
        errors.append(_issue("missing-nonblocking-label", "classify non-blocking findings"))
    if not EVIDENCE_RE.search(text):
        errors.append(_issue("missing-evidence", "include at least one evidence/source pointer"))

    status = STATUS_RE.search(text)
    if status is None:
        errors.append(_issue("missing-decision", "declare approve, revise, reject, or defer"))

    if UNKNOWN_AS_ABSENT_RE.search(text):
        errors.append(_issue("unknown-as-absent", "unknown must not be treated as absent"))

    chrome_only = ("finch", "speed launch", "chrome platform", "internal privacy template")
    for line in text.splitlines():
        line_lower = line.lower()
        if any(term in line_lower for term in chrome_only) and not any(
            marker in line_lower for marker in ("optional", "example", "browser-specific")
        ):
            errors.append(
                _issue(
                    "vendor-specific-generalization",
                    "mark Chromium-specific guidance as optional/example",
                )
            )
            break

    if status and status.group(1).lower() == "approve" and not EVIDENCE_RE.search(text):
        errors.append(_issue("unsupported-approve", "approve requires evidence"))
    if "open decisions" in headings and not re.search(
        r"(?i)\b(?:open question|question|decision)\b", text
    ):
        errors.append(_issue("empty-open-decisions", "list questions or decisions still open"))

    if "no material impact" in lowered:
        warnings.append(
            _issue("manual-impact-check", "verify that the stated no-impact rationale is sufficient")
        )

    return ValidationResult(path=path, errors=tuple(errors), warnings=tuple(warnings))


def validate_path(path: Path) -> ValidationResult:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(str(path), (_issue("read-error", str(exc)),))
    return validate_text(text, str(path))


def _print_result(result: ValidationResult) -> None:
    print(f"{result.path}: {'PASS' if result.ok else 'FAIL'}")
    for issue in result.errors:
        print(f"  ERROR [{issue.code}] {issue.message}")
    for issue in result.warnings:
        print(f"  WARN  [{issue.code}] {issue.message}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown review documents")
    args = parser.parse_args(argv)

    results = [validate_path(path) for path in args.paths]
    for result in results:
        _print_result(result)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
