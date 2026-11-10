#!/usr/bin/env python3
"""Validated adapter for the zj-research-cli/v1 protocol.

zj-research is a protocol adapter, not a compiler carrier. It requires an
external research compiler (any implementation that speaks zj-research-cli/v1)
supplied via the ZJ_RESEARCH_CLI environment variable. It bundles no compiler
and is vendor-neutral, so it runs on any agent that points at its own
compiler implementation.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROTOCOL = "zj-research-cli/v1"
REQUIRED_OPERATIONS = {"collect", "compile-report", "render-html", "evaluate"}
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_GITHUB_PREFLIGHT_TIMEOUT_SECONDS = 10.0
ERROR_SCHEMA = "zj-research-cli-error/v1"
PREFLIGHT_SCHEMA = "zj-research-github-preflight/v1"
COLLECTION_STATUS_SCHEMA = "zj-research-collection-status/v1"


class ResearchCliError(RuntimeError):
    """A stable, machine-readable failure at the research runtime seam."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        operation: str | None = None,
        phase: str | None = None,
        retryable: bool = False,
        details: dict[str, object] | None = None,
        recovery: list[str] | None = None,
        collection_status: dict[str, object] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.operation = operation
        self.phase = phase
        self.collection_status = collection_status
        self.diagnostic = {
            "schema": ERROR_SCHEMA,
            "protocol": PROTOCOL,
            "error": {
                "code": code,
                "message": message,
                "operation": operation,
                "phase": phase,
                "retryable": retryable,
                "details": details or {},
                "recovery": recovery or [],
            },
        }


def _compiler_error_payload(stderr: str) -> tuple[str, dict[str, object] | None]:
    cleaned = stderr.strip()
    for line in reversed(cleaned.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            return payload["error"], payload
    return cleaned or "compiler exited without diagnostics", None


def classify_compiler_failure(stderr: str, operation: str, returncode: int | None = None) -> ResearchCliError:
    """Turn compiler stderr into a stable diagnostic without hiding its cause."""

    raw_message, payload = _compiler_error_payload(stderr)
    normalized = raw_message.lower()
    details: dict[str, object] = {"compilerMessage": raw_message}
    if returncode is not None:
        details["returncode"] = returncode
    if payload is not None:
        details["compilerErrorPayload"] = payload
    if "rate limit" in normalized or "ratelimit" in normalized or "github_rate_limited" in normalized or "status 429" in normalized:
        return ResearchCliError(
            f"GitHub API rate limit blocked {operation}; no fresh sealed ledger was produced",
            code="GITHUB_RATE_LIMITED",
            operation=operation,
            phase="compiler",
            retryable=True,
            details=details,
            recovery=["wait until the GitHub reset time", "configure a valid GITHUB_TOKEN", "rerun fresh collection"],
        )
    if "401" in normalized or "credential" in normalized or "unauthorized" in normalized or "authentication" in normalized:
        return ResearchCliError(
            f"GitHub authentication failed during {operation}; no fresh sealed ledger was produced",
            code="GITHUB_AUTHENTICATION_FAILED",
            operation=operation,
            phase="compiler",
            details=details,
            recovery=["configure a valid GITHUB_TOKEN", "rerun the GitHub preflight"],
        )
    if "403" in normalized or "forbidden" in normalized or "permission" in normalized:
        return ResearchCliError(
            f"GitHub forbidden the {operation} request; no fresh sealed ledger was produced",
            code="GITHUB_FORBIDDEN",
            operation=operation,
            phase="compiler",
            details=details,
            recovery=["check token scopes and repository visibility", "rerun the GitHub preflight"],
        )
    if re.search(r"fetch failed|econn|enotfound|etimedout|network|socket|connection refused|dns", normalized):
        return ResearchCliError(
            f"GitHub network failure interrupted {operation}; no fresh sealed ledger was produced",
            code="GITHUB_NETWORK_FAILED",
            operation=operation,
            phase="compiler",
            retryable=True,
            details=details,
            recovery=["check network access to api.github.com", "rerun fresh collection"],
        )
    if "undefined.map" in normalized or "cannot read properties of undefined" in normalized:
        return ResearchCliError(
            f"research compiler failed during {operation} with an uncontextualized runtime error: {raw_message}",
            code="COMPILER_ERROR",
            operation=operation,
            phase="compiler",
            details=details,
            recovery=[
                "verify the compiler supplied via ZJ_RESEARCH_CLI",
                "do not treat the failed run as a sealed ledger",
                "rerun after the runtime is repaired",
            ],
        )
    return ResearchCliError(
        f"research compiler failed during {operation}: {raw_message}",
        code="COMPILER_ERROR",
        operation=operation,
        phase="compiler",
        details=details,
        recovery=["inspect the compiler diagnostic", "do not treat the failed run as a sealed ledger"],
    )


def _header(headers: object, name: str) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if callable(getter):
        value = getter(name)
        if value is None:
            value = getter(name.lower())
        if value is not None:
            return str(value)
    if isinstance(headers, dict):
        lowered = name.lower()
        for key, value in headers.items():
            if str(key).lower() == lowered:
                return str(value)
    return None


def _iso_reset(value: object) -> str | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _http_failure(status: int, headers: object, body: str, operation: str = "collect") -> ResearchCliError:
    remaining = _header(headers, "x-ratelimit-remaining")
    normalized = body.lower()
    if status == 401:
        return ResearchCliError(
            "GitHub authentication failed during preflight; fresh collection was blocked",
            code="GITHUB_AUTHENTICATION_FAILED",
            operation=operation,
            phase="preflight",
            details={"status": status},
            recovery=["configure a valid GITHUB_TOKEN", "rerun the GitHub preflight"],
        )
    if status == 429 or remaining == "0" or "rate limit" in normalized or "ratelimit" in normalized:
        reset_at = _iso_reset(_header(headers, "x-ratelimit-reset"))
        details: dict[str, object] = {"status": status}
        if reset_at is not None:
            details["resetAt"] = reset_at
        return ResearchCliError(
            "GitHub API rate limit blocked the collection preflight",
            code="GITHUB_RATE_LIMITED",
            operation=operation,
            phase="preflight",
            retryable=True,
            details=details,
            recovery=["wait until the GitHub reset time", "configure a valid GITHUB_TOKEN", "rerun fresh collection"],
        )
    if status == 403:
        return ResearchCliError(
            "GitHub forbidden the collection preflight",
            code="GITHUB_FORBIDDEN",
            operation=operation,
            phase="preflight",
            details={"status": status},
            recovery=["check token scopes and repository visibility", "rerun the GitHub preflight"],
        )
    return ResearchCliError(
        f"GitHub preflight returned HTTP {status}",
        code="GITHUB_PREFLIGHT_FAILED",
        operation=operation,
        phase="preflight",
        retryable=status >= 500,
        details={"status": status},
        recovery=["inspect GitHub API availability", "rerun the GitHub preflight"],
    )


def github_preflight(
    *,
    opener=None,
    token: str | None = None,
    api_url: str = DEFAULT_GITHUB_API_URL,
    timeout: float = DEFAULT_GITHUB_PREFLIGHT_TIMEOUT_SECONDS,
    minimum_remaining: int = 1,
) -> dict[str, object]:
    """Check GitHub auth mode and core quota before a fresh collection."""

    if timeout <= 0:
        raise ResearchCliError(
            "GitHub preflight timeout must be a positive number",
            code="INVALID_CONFIGURATION",
            operation="collect",
            phase="preflight",
        )
    if minimum_remaining < 0:
        raise ResearchCliError(
            "GitHub preflight minimum remaining quota must not be negative",
            code="INVALID_CONFIGURATION",
            operation="collect",
            phase="preflight",
        )
    configured_token = os.environ.get("GITHUB_TOKEN") if token is None else token
    configured_token = (configured_token or "").strip()
    request = Request(
        f"{api_url.rstrip('/')}/rate_limit",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zj-research-adapter",
            **({"Authorization": f"Bearer {configured_token}"} if configured_token else {}),
        },
    )
    open_request = urlopen if opener is None else opener
    try:
        with open_request(request, timeout=timeout) as response:
            status = int(getattr(response, "status", getattr(response, "code", 200)))
            headers = getattr(response, "headers", None)
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raw_body = error.read().decode("utf-8", errors="replace")
        raise _http_failure(error.code, error.headers, raw_body) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ResearchCliError(
            "GitHub network failure interrupted the collection preflight",
            code="GITHUB_NETWORK_FAILED",
            operation="collect",
            phase="preflight",
            retryable=True,
            details={"reason": str(error)},
            recovery=["check network access to api.github.com", "rerun the GitHub preflight"],
        ) from error
    if status >= 400:
        raise _http_failure(status, headers, body)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise ResearchCliError(
            "GitHub preflight returned invalid JSON",
            code="GITHUB_PREFLIGHT_INVALID",
            operation="collect",
            phase="preflight",
            details={"status": status},
            recovery=["inspect the GitHub API response", "rerun the GitHub preflight"],
        ) from error
    core = payload.get("resources", {}).get("core", {}) if isinstance(payload, dict) else {}
    if not isinstance(core, dict):
        core = {}
    limit_value = core.get("limit", _header(headers, "x-ratelimit-limit"))
    remaining_value = core.get("remaining", _header(headers, "x-ratelimit-remaining"))
    reset_value = core.get("reset", _header(headers, "x-ratelimit-reset"))
    try:
        limit = int(limit_value)
        remaining = int(remaining_value)
    except (TypeError, ValueError) as error:
        raise ResearchCliError(
            "GitHub preflight response does not contain a usable core quota",
            code="GITHUB_PREFLIGHT_INVALID",
            operation="collect",
            phase="preflight",
            details={"status": status},
            recovery=["inspect the GitHub API response", "rerun the GitHub preflight"],
        ) from error
    reset_at = _iso_reset(reset_value)
    rate_limit: dict[str, object] = {"resource": "core", "limit": limit, "remaining": remaining}
    if reset_at is not None:
        rate_limit["resetAt"] = reset_at
    return {
        "schema": PREFLIGHT_SCHEMA,
        "provider": "github",
        "authentication": {"mode": "authenticated" if configured_token else "anonymous", "tokenConfigured": bool(configured_token)},
        "rateLimit": rate_limit,
        "canCollect": remaining >= minimum_remaining,
    }


def brief_fingerprint(brief: dict[str, object]) -> str:
    """Match the compiler's normalized brief fingerprint for explicit reuse."""

    normalized: dict[str, object] = {
        "schema": brief.get("schema"),
        "topic": brief.get("topic"),
        "criteria": [
            {
                "id": criterion.get("id"),
                "question": criterion.get("question"),
                "critical": criterion.get("critical"),
                "keywords": list(criterion.get("keywords", [])),
            }
            for criterion in brief.get("criteria", [])
            if isinstance(criterion, dict)
        ],
        "repositories": [
            {"owner": repository.get("owner"), "name": repository.get("name")}
            for repository in brief.get("repositories", [])
            if isinstance(repository, dict)
        ],
    }
    discovery = brief.get("discovery")
    if isinstance(discovery, dict):
        normalized["discovery"] = {
            "query": discovery.get("query"),
            "limit": discovery.get("limit"),
            "topicKeywords": list(discovery.get("topicKeywords", [])),
        }
    normalized["policyVersion"] = brief.get("policyVersion")
    budget = brief.get("budget")
    if isinstance(budget, dict):
        normalized["budget"] = {
            key: budget[key]
            for key in ("maxFiles", "maxBytes", "deadlineMs")
            if key in budget
        }
    rendered = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def validate_sealed_ledger(
    ledger: object,
    brief: dict[str, object] | None = None,
    *,
    context: str = "reuse",
) -> dict[str, object]:
    failure_code = "COMPILER_OUTPUT_INVALID" if context == "compiler" else "LEDGER_REUSE_INVALID"
    failure_phase = "compiler" if context == "compiler" else "reuse"
    if not isinstance(ledger, dict):
        raise ResearchCliError(
            "sealed ledger must be a JSON object",
            code=failure_code,
            operation="collect",
            phase=failure_phase,
            details={"path": "result"},
            recovery=["provide a sealed ledger response", "rerun fresh collection"],
        )
    if ledger.get("schema") != "zj-verified-evidence-ledger/v1":
        raise ResearchCliError(
            "sealed ledger has an unsupported schema",
            code=failure_code,
            operation="collect",
            phase=failure_phase,
            details={"schema": ledger.get("schema")},
            recovery=["provide a zj-verified-evidence-ledger/v1 result", "rerun fresh collection"],
        )
    required_arrays = ("repositories", "candidates", "evidence", "unknownCriteria", "navigation")
    missing = [key for key in required_arrays if not isinstance(ledger.get(key), list)]
    if not isinstance(ledger.get("collection"), dict):
        missing.append("collection")
    if not isinstance(ledger.get("briefFingerprint"), str) or not re.fullmatch(r"[0-9a-f]{64}", ledger["briefFingerprint"]):
        missing.append("briefFingerprint")
    if missing:
        raise ResearchCliError(
            "sealed ledger is missing required fields",
            code=failure_code,
            operation="collect",
            phase=failure_phase,
            details={"missing": missing},
            recovery=["provide a complete sealed ledger", "rerun fresh collection"],
        )
    # 机器可检的形状不变量：repositories 须为对象数组，不得被标量估计替换
    # （「字段不得被模型估计替换」的语义校验属 review 层职责，见 research-cli.md 边界注记）。
    for index, repo in enumerate(ledger.get("repositories", [])):
        if not isinstance(repo, dict):
            raise ResearchCliError(
                "sealed ledger repositories must be objects owned by the ledger, not scalar estimates",
                code=failure_code,
                operation="collect",
                phase=failure_phase,
                details={"repositoryIndex": index},
                recovery=["provide repository objects sourced from the verified evidence ledger", "rerun fresh collection"],
            )
    if brief is not None:
        expected = brief_fingerprint(brief)
        actual = ledger["briefFingerprint"]
        if actual != expected:
            raise ResearchCliError(
                "sealed ledger does not match the current brief; it was not reused",
                code="COMPILER_OUTPUT_INVALID" if context == "compiler" else "LEDGER_REUSE_MISMATCH",
                operation="collect",
                phase=failure_phase,
                details={"expectedBriefFingerprint": expected, "ledgerBriefFingerprint": actual},
                recovery=["use the brief that produced this ledger", "rerun fresh collection for the current brief"],
            )
    return ledger


def load_reusable_ledger(path: Path, brief: dict[str, object]) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ResearchCliError(
            f"sealed ledger is unavailable: {path}",
            code="LEDGER_REUSE_INVALID",
            operation="collect",
            phase="reuse",
            details={"path": str(path)},
            recovery=["provide an existing sealed ledger", "rerun fresh collection"],
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise ResearchCliError(
            f"sealed ledger could not be read: {path}",
            code="LEDGER_REUSE_INVALID",
            operation="collect",
            phase="reuse",
            details={"path": str(path), "reason": str(error)},
            recovery=["repair or replace the sealed ledger", "rerun fresh collection"],
        ) from error
    if isinstance(value, dict) and value.get("protocol") == PROTOCOL and value.get("operation") == "collect":
        value = value.get("result")
    return validate_sealed_ledger(value, brief)


def collection_run_status(
    request: dict[str, object],
    state: str,
    *,
    preflight: dict[str, object] | None = None,
    ledger_source: str | None = None,
    error: ResearchCliError | None = None,
) -> dict[str, object]:
    brief = request.get("brief")
    relationship = (
        "explicit-reuse"
        if state == "reused-sealed-ledger"
        else "not-produced"
        if state == "collection-blocked"
        else "fresh-collection"
    )
    status: dict[str, object] = {
        "schema": COLLECTION_STATUS_SCHEMA,
        "protocol": PROTOCOL,
        "operation": "collect",
        "state": state,
        "brief": brief,
        "briefFingerprint": brief_fingerprint(brief) if isinstance(brief, dict) else None,
        "preflight": preflight,
        "ledger": {"relationship": relationship, "source": ledger_source},
        "fallback": {"automatic": False, "oldLedgerUsed": state == "reused-sealed-ledger"},
    }
    if error is not None:
        status["error"] = dict(error.diagnostic["error"])
    return status


def _attach_collection_status(error: ResearchCliError, status: dict[str, object]) -> ResearchCliError:
    error.collection_status = status
    error.diagnostic["error"]["collectionStatus"] = status
    return error


def execute_request(
    request: dict[str, object],
    executable: list[str],
    *,
    preflight=github_preflight,
    reuse_ledger: Path | None = None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Execute one request and return its optional collection run status."""

    operation = request.get("operation")
    if reuse_ledger is not None and operation != "collect":
        raise ResearchCliError(
            "--reuse-ledger is only valid for collect requests",
            code="INVALID_REQUEST",
            operation=str(operation or "unknown"),
            phase="request",
        )
    if operation != "collect":
        return invoke(executable, request), None
    brief = request.get("brief")
    if not isinstance(brief, dict):
        raise ResearchCliError(
            "collect request must contain a brief object",
            code="INVALID_REQUEST",
            operation="collect",
            phase="request",
        )
    if reuse_ledger is not None:
        ledger = load_reusable_ledger(reuse_ledger, brief)
        response = {"protocol": PROTOCOL, "operation": "collect", "result": ledger}
        return response, collection_run_status(request, "reused-sealed-ledger", ledger_source=str(reuse_ledger))
    try:
        preflight_result = preflight()
        preflight_valid = isinstance(preflight_result, dict) and isinstance(preflight_result.get("canCollect"), bool)
        if not preflight_valid or preflight_result.get("canCollect") is not True:
            error = ResearchCliError(
                "GitHub quota preflight did not permit fresh collection; no sealed ledger was produced"
                if preflight_valid
                else "GitHub quota preflight returned an invalid result; no sealed ledger was produced",
                code="GITHUB_RATE_LIMITED" if preflight_valid else "GITHUB_PREFLIGHT_INVALID",
                operation="collect",
                phase="preflight",
                retryable=preflight_valid,
                details={"preflight": preflight_result},
                recovery=["wait until the GitHub reset time", "configure a valid GITHUB_TOKEN", "rerun fresh collection"]
                if preflight_valid
                else ["inspect the GitHub preflight result", "rerun the GitHub preflight"],
            )
            raise _attach_collection_status(
                error,
                collection_run_status(request, "collection-blocked", preflight=preflight_result, error=error),
            )
        response = invoke(executable, request)
        validate_sealed_ledger(response.get("result"), brief, context="compiler")
    except ResearchCliError as error:
        if error.collection_status is None:
            preflight_snapshot = locals().get("preflight_result")
            if preflight_snapshot is None and error.phase == "preflight":
                preflight_snapshot = {
                    "schema": PREFLIGHT_SCHEMA,
                    "provider": "github",
                    "state": "failed",
                    "error": dict(error.diagnostic["error"]),
                }
            raise _attach_collection_status(
                error,
                collection_run_status(request, "collection-blocked", preflight=preflight_snapshot, error=error),
            )
        raise
    return response, collection_run_status(request, "fresh-collection", preflight=preflight_result)


def command() -> list[str]:
    """Resolve the research compiler command.

    zj-research is a protocol adapter. It does not bundle a compiler and carries
    no vendor tie; the caller must supply a zj-research-cli/v1 compatible
    compiler through ZJ_RESEARCH_CLI. Failing that, fail loudly with the setup
    pointer rather than silently falling back to a vendored artifact.
    """
    configured = os.environ.get("ZJ_RESEARCH_CLI")
    if not configured:
        raise RuntimeError(
            "ZJ_RESEARCH_CLI is not set. zj-research is a protocol adapter and requires an "
            "external research compiler that speaks zj-research-cli/v1. Provide it, for example: "
            'export ZJ_RESEARCH_CLI="node /path/to/compiler/lib/bin.js"'
        )
    return shlex.split(configured)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--status-output", type=Path, help="write the collection run state beside the ledger output")
    parser.add_argument("--reuse-ledger", type=Path, help="explicitly reuse a sealed ledger for a matching collect brief")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        response = invoke(command(), {"protocol": PROTOCOL, "operation": "describe"})
        operations = set(response.get("result", {}).get("operations", []))
        missing = sorted(REQUIRED_OPERATIONS - operations)
        if missing:
            raise RuntimeError(f"compiler is missing required operations: {', '.join(missing)}")
        print(f"{PROTOCOL}: {', '.join(sorted(operations))}")
        return 0
    if args.request is None:
        parser.error("request is required unless --check is used")
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResearchCliError(
            f"research request could not be read: {args.request}",
            code="INVALID_REQUEST",
            phase="request",
            details={"path": str(args.request), "reason": str(error)},
        ) from error
    if not isinstance(request, dict):
        raise ResearchCliError("research request must be a JSON object", code="INVALID_REQUEST", phase="request")
    if request.get("protocol") != PROTOCOL:
        raise ResearchCliError(
            f"request protocol must be {PROTOCOL}",
            code="PROTOCOL_MISMATCH",
            operation=str(request.get("operation") or "unknown"),
            phase="request",
        )
    executable = [] if args.reuse_ledger is not None and request.get("operation") == "collect" else command()
    try:
        response, status = execute_request(request, executable, reuse_ledger=args.reuse_ledger)
    except ResearchCliError as error:
        if args.status_output is not None and error.collection_status is not None:
            args.status_output.write_text(json.dumps(error.collection_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    rendered = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    if args.status_output is not None and status is not None:
        args.status_output.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def invoke(executable: list[str], request: dict[str, object]) -> dict[str, object]:
    operation = str(request.get("operation") or "unknown")
    configured_timeout = os.environ.get("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS")
    try:
        timeout = DEFAULT_TIMEOUT_SECONDS if configured_timeout is None else float(configured_timeout)
    except ValueError as error:
        raise ResearchCliError(
            "ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number",
            code="INVALID_CONFIGURATION",
            operation=operation,
            phase="adapter",
        ) from error
    if timeout <= 0:
        raise ResearchCliError(
            "ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number",
            code="INVALID_CONFIGURATION",
            operation=operation,
            phase="adapter",
        )
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
        raise ResearchCliError(
            f"research compiler exceeded the {timeout:g}s adapter timeout",
            code="TIMEOUT",
            operation=operation,
            phase="compiler",
            retryable=True,
            recovery=["increase ZJ_RESEARCH_CLI_TIMEOUT_SECONDS if the brief permits", "rerun the operation"],
        ) from error
    except FileNotFoundError as error:
        raise ResearchCliError(
            "research compiler executable is unavailable",
            code="RUNTIME_UNAVAILABLE",
            operation=operation,
            phase="adapter",
            details={"executable": executable[0] if executable else None},
            recovery=["run the adapter check", "repair the compiler supplied via ZJ_RESEARCH_CLI"],
        ) from error
    except OSError as error:
        raise ResearchCliError(
            "research compiler could not be started",
            code="RUNTIME_UNAVAILABLE",
            operation=operation,
            phase="adapter",
            details={"reason": str(error)},
            recovery=["run the adapter check", "repair the compiler supplied via ZJ_RESEARCH_CLI"],
        ) from error
    if completed.returncode != 0:
        raise classify_compiler_failure(completed.stderr, operation, completed.returncode)
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ResearchCliError(
            "research compiler returned invalid JSON",
            code="COMPILER_OUTPUT_INVALID",
            operation=operation,
            phase="compiler",
            details={"stdoutPrefix": completed.stdout[:500]},
            recovery=["verify the compiler supplied via ZJ_RESEARCH_CLI", "rerun the operation"],
        ) from error
    if not isinstance(response, dict):
        raise ResearchCliError(
            "research compiler returned a non-object response",
            code="COMPILER_OUTPUT_INVALID",
            operation=operation,
            phase="compiler",
            details={"responseType": type(response).__name__},
            recovery=["verify the compiler supplied via ZJ_RESEARCH_CLI", "rerun the operation"],
        )
    expected_protocol = request.get("protocol")
    if response.get("protocol") != expected_protocol:
        raise ResearchCliError(
            f"compiler response protocol must be {expected_protocol}",
            code="PROTOCOL_MISMATCH",
            operation=operation,
            phase="adapter",
            details={"actualProtocol": response.get("protocol")},
        )
    if response.get("operation") != request.get("operation"):
        raise ResearchCliError(
            "compiler response operation does not match the request",
            code="PROTOCOL_MISMATCH",
            operation=operation,
            phase="adapter",
            details={"actualOperation": response.get("operation")},
        )
    if not isinstance(response.get("result"), dict):
        raise ResearchCliError(
            "research compiler response is missing its result object",
            code="COMPILER_OUTPUT_INVALID",
            operation=operation,
            phase="compiler",
            details={"responseKeys": sorted(response.keys())},
            recovery=["verify the compiler supplied via ZJ_RESEARCH_CLI", "rerun the operation"],
        )
    return response


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ResearchCliError as error:
        print(f"research-cli adapter: {json.dumps(error.diagnostic, ensure_ascii=False)}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"research-cli adapter: {error}", file=sys.stderr)
        raise SystemExit(1)
