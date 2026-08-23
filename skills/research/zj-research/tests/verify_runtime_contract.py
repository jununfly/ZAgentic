#!/usr/bin/env python3
"""Contract tests for the zj-research adapter's collection runtime seam."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "research_cli.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("research_cli_runtime_contract", ADAPTER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load research adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: dict[str, object], headers: dict[str, str] | None = None, status: int = 200):
        self.payload = payload
        self.headers = headers or {}
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


BRIEF = {
    "schema": "zj-research-brief/v1",
    "topic": "runtime contract",
    "criteria": [{"id": "runtime", "question": "What runs?", "critical": True, "keywords": ["runtime"]}],
    "repositories": [{"owner": "example", "name": "research"}],
    "policyVersion": "v1",
    "budget": {"maxFiles": 1, "maxBytes": 1000, "deadlineMs": 1000},
}


def make_ledger(adapter):
    return {
        "schema": "zj-verified-evidence-ledger/v1",
        "compilerVersion": "research/v1",
        "briefFingerprint": adapter.brief_fingerprint(BRIEF),
        "policyVersion": "v1",
        "observedAt": "2026-08-23T00:00:00.000Z",
        "repositories": [],
        "candidates": [],
        "evidence": [],
        "unknownCriteria": [],
        "navigation": [],
        "collection": {"filesRead": 0, "sourceBytesRead": 0, "durationMs": 0, "cacheHit": False},
    }


def compiler_command(response: dict[str, object]) -> list[str]:
    rendered = json.dumps(response, ensure_ascii=False)
    script = f"import sys; sys.stdout.write({rendered!r})"
    return [sys.executable, "-c", script]


def test_compiler_failures_are_structured(adapter):
    cases = [
        ("{\"error\":\"GitHub API rate limit exhausted; retry after 2030-01-01T00:00:00Z\"}", "GITHUB_RATE_LIMITED"),
        ("{\"error\":\"GitHub rejected the configured credential (401)\"}", "GITHUB_AUTHENTICATION_FAILED"),
        ("{\"error\":\"GitHub returned 403 Forbidden\"}", "GITHUB_FORBIDDEN"),
        ("fetch failed: ECONNRESET", "GITHUB_NETWORK_FAILED"),
        ("TypeError: Cannot read properties of undefined (reading 'map')", "COMPILER_ERROR"),
    ]
    for stderr, expected_code in cases:
        error = adapter.classify_compiler_failure(stderr, "collect", returncode=1)
        assert error.code == expected_code, (stderr, error.code)
        assert error.diagnostic["schema"] == adapter.ERROR_SCHEMA
        assert error.diagnostic["error"]["operation"] == "collect"
    undefined_error = adapter.classify_compiler_failure(cases[-1][0], "collect", returncode=1)
    assert "collect" in str(undefined_error)
    assert "uncontextualized" in str(undefined_error).lower()

    failing = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('{\"protocol\":\"zj-research-cli/v1\",\"error\":\"GitHub API rate limit exhausted\"}'); raise SystemExit(1)",
    ]
    try:
        adapter.invoke(failing, {"protocol": adapter.PROTOCOL, "operation": "collect"})
    except adapter.ResearchCliError as error:
        assert error.code == "GITHUB_RATE_LIMITED"
        assert error.diagnostic["error"]["details"]["returncode"] == 1
    else:
        raise AssertionError("compiler subprocess failure was not structured")


def test_github_preflight_reports_auth_and_quota(adapter):
    calls: list[object] = []

    def opener(request, timeout):
        calls.append((request.full_url, request.headers, timeout))
        return FakeResponse(
            {"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": 1_900_000_000}}},
            headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "4999", "x-ratelimit-reset": "1900000000"},
        )

    preflight = adapter.github_preflight(opener=opener, token="secret", api_url="https://api.github.test", timeout=2)
    assert preflight["authentication"] == {"mode": "authenticated", "tokenConfigured": True}
    assert preflight["rateLimit"]["remaining"] == 4999
    assert preflight["canCollect"] is True
    assert calls[0][0] == "https://api.github.test/rate_limit"
    assert "authorization" in {key.lower() for key in calls[0][1]}


def test_github_preflight_classifies_quota_and_network_failures(adapter):
    def exhausted(_request, _timeout):
        return FakeResponse({"resources": {"core": {"limit": 60, "remaining": 0, "reset": 1_900_000_000}}})

    exhausted_result = adapter.github_preflight(opener=exhausted, token=None)
    assert exhausted_result["authentication"]["mode"] == "anonymous"
    assert exhausted_result["canCollect"] is False

    def offline(_request, _timeout):
        raise URLError("offline")

    try:
        adapter.github_preflight(opener=offline, token=None)
    except adapter.ResearchCliError as error:
        assert error.code == "GITHUB_NETWORK_FAILED"
    else:
        raise AssertionError("network preflight failure was not structured")

    body = io.BytesIO(b'{"message":"API rate limit exceeded"}')
    headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"}

    def rate_limited(_request, _timeout):
        raise HTTPError("https://api.github.test/rate_limit", 403, "forbidden", headers, body)

    try:
        adapter.github_preflight(opener=rate_limited, token="secret")
    except adapter.ResearchCliError as error:
        assert error.code == "GITHUB_RATE_LIMITED"
    else:
        raise AssertionError("HTTP rate-limit preflight failure was not structured")

    def unauthorized(_request, _timeout):
        raise HTTPError("https://api.github.test/rate_limit", 401, "unauthorized", {}, io.BytesIO(b'{"message":"Bad credentials"}'))

    try:
        adapter.github_preflight(opener=unauthorized, token="stale-token")
    except adapter.ResearchCliError as error:
        assert error.code == "GITHUB_AUTHENTICATION_FAILED"
    else:
        raise AssertionError("HTTP authentication preflight failure was not structured")


def test_collection_states_preserve_the_brief_and_never_fallback(adapter):
    ledger = make_ledger(adapter)
    response = {"protocol": adapter.PROTOCOL, "operation": "collect", "result": ledger}
    request = {"protocol": adapter.PROTOCOL, "operation": "collect", "brief": BRIEF}
    preflight = {
        "schema": adapter.PREFLIGHT_SCHEMA,
        "provider": "github",
        "authentication": {"mode": "anonymous", "tokenConfigured": False},
        "rateLimit": {"resource": "core", "limit": 60, "remaining": 0, "resetAt": "2030-01-01T00:00:00Z"},
        "canCollect": False,
    }

    try:
        adapter.execute_request(request, compiler_command(response), preflight=lambda: preflight)
    except adapter.ResearchCliError as error:
        assert error.code == "GITHUB_RATE_LIMITED"
        status = error.collection_status
        assert status["state"] == "collection-blocked"
        assert status["brief"] == BRIEF
        assert status["ledger"]["relationship"] == "not-produced"
        assert status["fallback"]["automatic"] is False
        json.dumps(status)
        json.dumps(error.diagnostic)
    else:
        raise AssertionError("quota exhaustion did not block fresh collection")

    available = dict(preflight)
    available["rateLimit"] = {"resource": "core", "limit": 60, "remaining": 1}
    available["canCollect"] = True
    fresh, fresh_status = adapter.execute_request(request, compiler_command(response), preflight=lambda: available)
    assert fresh["result"] == ledger
    assert fresh_status["state"] == "fresh-collection"
    assert fresh_status["ledger"]["relationship"] == "fresh-collection"

    with tempfile.TemporaryDirectory(prefix="zj-research-runtime-") as directory:
        ledger_path = Path(directory) / "sealed-ledger.json"
        ledger_path.write_text(json.dumps({"protocol": adapter.PROTOCOL, "operation": "collect", "result": ledger}), encoding="utf-8")
        reused, status = adapter.execute_request(
            request,
            ["this-command-must-not-run"],
            preflight=lambda: (_ for _ in ()).throw(AssertionError("reuse must skip preflight")),
            reuse_ledger=ledger_path,
        )
        assert reused["result"] == ledger
        assert status["state"] == "reused-sealed-ledger"
        assert status["brief"] == BRIEF
        assert status["ledger"]["relationship"] == "explicit-reuse"

        mismatched_brief = dict(BRIEF)
        mismatched_brief["topic"] = "different brief"
        try:
            adapter.load_reusable_ledger(ledger_path, mismatched_brief)
        except adapter.ResearchCliError as error:
            assert error.code == "LEDGER_REUSE_MISMATCH"
        else:
            raise AssertionError("a ledger for another brief was reused")

        request_path = Path(directory) / "request.json"
        response_path = Path(directory) / "response.json"
        status_path = Path(directory) / "status.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        environment = dict(os.environ)
        completed = subprocess.run(
            [
                sys.executable,
                str(ADAPTER),
                str(request_path),
                "--reuse-ledger",
                str(ledger_path),
                "--output",
                str(response_path),
                "--status-output",
                str(status_path),
            ],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert json.loads(status_path.read_text(encoding="utf-8"))["state"] == "reused-sealed-ledger"
        assert json.loads(response_path.read_text(encoding="utf-8"))["result"] == ledger


def main() -> int:
    adapter = load_adapter()
    test_compiler_failures_are_structured(adapter)
    test_github_preflight_reports_auth_and_quota(adapter)
    test_github_preflight_classifies_quota_and_network_failures(adapter)
    test_collection_states_preserve_the_brief_and_never_fallback(adapter)
    print("zj-research runtime contract: structured failures, preflight, and collection states passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
