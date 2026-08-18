#!/usr/bin/env python3
"""Validated adapter for the versioned ZHarness research CLI protocol."""

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROTOCOL = "zj-research-cli/v1"
LOCK_SCHEMA = "zj-research-compiler-lock/v1"
REQUIRED_OPERATIONS = {"collect", "compile-report", "render-html", "evaluate"}
DEFAULT_TIMEOUT_SECONDS = 300.0
ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as content:
        for chunk in iter(lambda: content.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compiler_cache() -> Path:
    configured = os.environ.get("ZJ_RESEARCH_COMPILER_CACHE")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "zj-research" / "compiler"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "zj-research" / "compiler"


def bundled_command() -> list[str]:
    lock_path = ARTIFACTS / "compiler-lock.json"
    if not lock_path.is_file():
        raise RuntimeError(f"bundled compiler lock is unavailable: {lock_path}")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema") != LOCK_SCHEMA or lock.get("protocol") != PROTOCOL:
        raise RuntimeError("bundled compiler lock is incompatible")
    artifact_name = lock.get("artifact")
    expected_hash = lock.get("sha256")
    if not isinstance(artifact_name, str) or Path(artifact_name).name != artifact_name:
        raise RuntimeError("bundled compiler lock has an invalid artifact name")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise RuntimeError("bundled compiler lock has an invalid SHA-256")
    try:
        int(expected_hash, 16)
    except ValueError as error:
        raise RuntimeError("bundled compiler lock has an invalid SHA-256") from error
    minimum_node_major = lock.get("minimumNodeMajor")
    if not isinstance(minimum_node_major, int) or minimum_node_major < 1:
        raise RuntimeError("bundled compiler lock has an invalid Node.js requirement")
    try:
        node_version = subprocess.run(["node", "--version"], text=True, capture_output=True, check=False)
    except FileNotFoundError as error:
        raise RuntimeError("Node.js is unavailable for the bundled compiler") from error
    if node_version.returncode != 0:
        raise RuntimeError("Node.js is unavailable for the bundled compiler")
    try:
        version = node_version.stdout.strip()
        node_major = int((version[1:] if version.startswith("v") else version).split(".", 1)[0])
    except ValueError as error:
        raise RuntimeError("Node.js returned an invalid version") from error
    if node_major < minimum_node_major:
        raise RuntimeError(f"bundled compiler requires Node.js {minimum_node_major} or newer")
    artifact = ARTIFACTS / artifact_name
    if not artifact.is_file():
        raise RuntimeError(f"bundled compiler artifact is unavailable: {artifact}")
    actual_hash = file_sha256(artifact)
    if actual_hash != expected_hash:
        raise RuntimeError(f"bundled compiler artifact SHA-256 mismatch: expected {expected_hash}, got {actual_hash}")
    target = compiler_cache() / expected_hash
    executable = target / "lib" / "bin.js"
    if not executable.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"{expected_hash}.tmp-", dir=target.parent) as directory:
            temporary = Path(directory)
            with tarfile.open(artifact, "r:gz") as archive:
                for member in archive.getmembers():
                    path = Path(member.name)
                    invalid_kind = not member.isfile() and not member.isdir()
                    if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or invalid_kind:
                        raise RuntimeError("bundled compiler artifact contains an unsafe path")
                if hasattr(tarfile, "data_filter"):
                    archive.extractall(temporary, filter="data")
                else:
                    archive.extractall(temporary)
            if not (temporary / "lib" / "bin.js").is_file():
                raise RuntimeError("bundled compiler artifact has no executable")
            try:
                os.replace(temporary, target)
            except OSError:
                if not executable.is_file():
                    raise
    return ["node", str(executable)]


def command() -> list[str]:
    configured = os.environ.get("ZJ_RESEARCH_CLI")
    if configured:
        return shlex.split(configured)
    return bundled_command()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    executable = command()
    if args.check:
        response = invoke(executable, {"protocol": PROTOCOL, "operation": "describe"})
        operations = set(response.get("result", {}).get("operations", []))
        missing = sorted(REQUIRED_OPERATIONS - operations)
        if missing:
            raise RuntimeError(f"compiler is missing required operations: {', '.join(missing)}")
        print(f"{PROTOCOL}: {', '.join(sorted(operations))}")
        return 0
    if args.request is None:
        parser.error("request is required unless --check is used")
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("protocol") != PROTOCOL:
        raise RuntimeError(f"request protocol must be {PROTOCOL}")
    response = invoke(executable, request)
    rendered = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


def invoke(executable: list[str], request: dict[str, object]) -> dict[str, object]:
    configured_timeout = os.environ.get("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS")
    try:
        timeout = DEFAULT_TIMEOUT_SECONDS if configured_timeout is None else float(configured_timeout)
    except ValueError as error:
        raise RuntimeError("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number") from error
    if timeout <= 0:
        raise RuntimeError("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number")
    try:
        completed = subprocess.run(
            executable,
            input=json.dumps(request, separators=(",", ":")),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"dsh-research exceeded the {timeout:g}s adapter timeout") from error
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"dsh-research exited {completed.returncode}")
    response = json.loads(completed.stdout)
    if response.get("protocol") != PROTOCOL:
        raise RuntimeError(f"compiler response protocol must be {PROTOCOL}")
    if response.get("operation") != request.get("operation"):
        raise RuntimeError("compiler response operation does not match the request")
    return response


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"research-cli adapter: {error}", file=sys.stderr)
        raise SystemExit(1)
