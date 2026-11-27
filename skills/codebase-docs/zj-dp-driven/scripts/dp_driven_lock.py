"""§4.4 single-writer file lock for the zj-dp-driven carrier.

Design:
  §4.4 [定稿] "并发原子性保证：finding 处置和热插 add 的原子性由 carrier 单写者保证——
                sqlite 的串行化写入天然确保..."
  §8 [未决]  "claim 超时释放 / TTL 机制"

Phase 2 introduced this **process-level flock** wrapped around every CLI write, satisfying the
single-writer invariant (§4.4) for the "先自用（单人单 agent）" rollout (§8 渐进策略). It is
*not* the lease: claim TTL/heartbeat landed later in Phase-4a (§4.4) and lives in
`dp_driven_model.claim/renew/_is_expired` — the flock serializes writers, the lease revives a
plan whose holder died.

Notes
-----
* The lock file is `<carrier>.lock` (same directory). It lives alongside the sqlite, is
  cleaned at closeout, and never leaves the Human-specified directory (§5.4).
* Blocking is bounded by `timeout` seconds. Callers (CLI) translate `LockTimeout` into a
  stable exit code (`4`).
* macOS + Linux both support `fcntl.flock`. Windows would need `msvcrt.locking`; §5.4
  assumes a POSIX Human-specified directory and does not claim Windows support in Phase 2.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import os
import time

LOCK_SUFFIX = ".lock"
ACQUIRE_TIMEOUT_DEFAULT = 10.0  # seconds


class LockTimeout(RuntimeError):
    """Raised when `acquire` could not obtain the exclusive lock within its timeout."""


def lock_path(carrier_path: str) -> str:
    """Return the sibling lockfile path for a given carrier."""
    return carrier_path + LOCK_SUFFIX


@contextlib.contextmanager
def acquire(carrier_path: str, timeout: float = ACQUIRE_TIMEOUT_DEFAULT,
            poll: float = 0.05):
    """Exclusive flock around the carrier write window.

    Usage:
        with dp_driven_lock.acquire(db):
            model = DpDriven.open(db)
            ... mutations ...
            model.save()

    Yields the lockfile path. Raises LockTimeout on expiry.
    """
    lp = lock_path(carrier_path)
    fd = os.open(lp, os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                os.close(fd)
                raise
            if time.monotonic() >= deadline:
                os.close(fd)
                raise LockTimeout(f"carrier lock timeout on {lp}") from exc
            time.sleep(poll)
    try:
        yield lp
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
