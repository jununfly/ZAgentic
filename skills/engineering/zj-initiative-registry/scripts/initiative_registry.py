#!/usr/bin/env python3
"""Resolve a Registry checkout and delegate to its versioned management scripts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def normalize_url(value: str) -> str:
    normalized = value.rstrip("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized.lower()


def verify_checkout(path: Path, expected_url: str) -> None:
    if not (path / ".git").exists():
        raise SystemExit(f"Registry checkout is not a Git repository: {path}")
    try:
        actual = subprocess.check_output(
            ["git", "-C", str(path), "remote", "get-url", "origin"], text=True
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise SystemExit("Registry checkout has no readable origin remote") from exc
    if normalize_url(actual) != normalize_url(expected_url):
        raise SystemExit(f"Registry origin mismatch: expected {expected_url}, found {actual}")


def delegate(path: Path, script: str, arguments: list[str]) -> int:
    target = path / "scripts" / script
    if not target.is_file():
        raise SystemExit(f"Registry script is missing: {target}")
    return subprocess.run([sys.executable, str(target), *arguments], cwd=path).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-repo", required=True)
    parser.add_argument("--registry-path", type=Path, required=True)
    parser.add_argument("operation", choices=["show", "compile", "validate", "register", "remove", "semantic-diff", "check-drift", "sync", "create-branch", "publish-plan"])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    registry_path = args.registry_path.expanduser().resolve()
    verify_checkout(registry_path, args.registry_repo)
    routes = {
        "compile": ("compile_registry.py", []),
        "validate": ("validate_registry.py", []),
        "show": ("registry_admin.py", ["show"]),
        "register": ("registry_admin.py", ["register"]),
        "remove": ("registry_admin.py", ["remove"]),
        "semantic-diff": ("registry_admin.py", ["semantic-diff"]),
        "check-drift": ("registry_admin.py", ["check-drift"]),
        "sync": ("git_workflow.py", ["sync"]),
        "create-branch": ("git_workflow.py", ["create-branch"]),
        "publish-plan": ("git_workflow.py", ["publish-plan"]),
    }
    script, prefix = routes[args.operation]
    return delegate(registry_path, script, [*prefix, *args.arguments])


if __name__ == "__main__":
    raise SystemExit(main())
