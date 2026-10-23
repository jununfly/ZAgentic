#!/usr/bin/env python3
"""Guard for unittest runs inside the gate scripts.

Problem it closes: on CPython < 3.12, `python -m unittest discover` reports
"Ran 0 tests ... OK" and exits 0 when it collects nothing. A mis-filtered path
or a renamed test file then reads as green by absence of a check — the exact
"checks: 0" regression class this repo keeps re-introducing.

Contract: read a captured unittest log, exit 0 only if at least one test ran
and none failed/errored. Anything else is a failure so the gate aborts.
"""
import sys


def check(log_text: str) -> tuple[bool, str]:
    if "Ran 0 tests" in log_text:
        return False, "unittest collected 0 tests (nothing actually checked)"
    if "FAILED" in log_text or "ERROR" in log_text:
        return False, "unittest reported failures/errors"
    if "OK" not in log_text and "Ran" not in log_text:
        return False, "unexpected unittest output (no result line seen)"
    return True, "ok"


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: assert_unittest_result.py <logfile> [label]", file=sys.stderr)
        return 2
    path = argv[1]
    label = argv[2] if len(argv) > 2 else path
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"FAIL: {label}: cannot read log {path}: {exc}")
        return 1
    ok, msg = check(text)
    if not ok:
        print(f"FAIL: {label}: {msg}")
        return 1
    print(f"    OK  {label}: suite actually ran and passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
