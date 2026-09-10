#!/usr/bin/env python3
"""Contract tests for roadmap lock contention.

Why this file exists
--------------------
`docs/plans/zj-roadmap-dag-concurrency.md` Problem #1 originally reported a
lost update when two writers mutate the same carrier. A probe (see the PR that
introduced this file) reproduced it, and the cause turned out to be neither
"no leases" nor "no transactions": the roadmap already serialises every write
command inside a whole-graph lock, and parent status is derived, not
snapshotted. What was broken is the lock's contended branch -- the loser
crashed with exit 1 before it ever wrote, so the write was missing, not
overwritten. The spec's attribution has since been corrected (issue #48);
this file is the regression guard for that correction: it asserts no writer
exits 1.

`roadmap_file_lock()` acquires the lock with `os.mkdir` and used to catch only
`FileExistsError`. Any runtime that interposes `os.mkdir` — this repository's
own safe-delete shim, or a sitecustomize doing the same — raises
`PermissionError` with `errno` unset instead. The `except FileExistsError`
clause cannot see it, so the wait/retry loop never runs and the writer dies
with exit 1 before it ever touches the carrier. Widening that one clause made
the probe go from 23/25 invariant violations to 0/25, with zero lock timeouts.

Contract under test
-------------------
  1. "The lock directory already exists" is recognised regardless of which
     exception type the platform uses to say so (§IsLockContention).
  2. Recognised contention makes the acquirer WAIT, then acquire — not crash
     (§WaitAndAcquire).
  3. Unrecognised OSErrors are re-raised; the lock never swallows a real
     filesystem failure (§NotContention).
  4. Contention that outlasts the deadline surfaces as RoadmapLockTimeout,
     the documented exit code 2 — never as an uncaught exception (§Timeout).
  5. N concurrent writers leave the carrier intact: no exit 1, no lost
     completions, parent rollup consistent with its children, no leftover lock
     directory (§ConcurrentWriters). Plus a serial control case: if it fails,
     these tests are measuring the wrong thing.

Run: python tests/test_lock_contention.py        (also works under pytest)
"""

import errno
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

import roadmap
from roadmap import (  # noqa: E402
    RoadmapLockTimeout,
    _is_lock_contention,
    roadmap_file_lock,
    roadmap_lock_dir,
    unlock_roadmap,
)

PY = sys.executable
PARENT = "1"

# Small enough to stay fast, large enough to make contention real.
WRITERS = 8
REPEATS = 2


def raise_permission_eexist(path):
    """What an interposed os.mkdir raises for an existing path.

    Deliberately mirrors the observed shim behaviour: PermissionError, message
    carrying EEXIST, but `errno` left as None. That combination is exactly what
    the old `except FileExistsError` could not catch.
    """
    return PermissionError(f"[Errno 17] EEXIST: file already exists: mkdir '{path}'")


class IsLockContention(unittest.TestCase):
    """Which exceptions mean "someone else holds the lock"."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lock_dir = os.path.join(self.tmp.name, "roadmap.json.lock")

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_exists_error_is_contention(self):
        self.assertTrue(_is_lock_contention(self.lock_dir, FileExistsError(errno.EEXIST, "x")))

    def test_oserror_with_eexist_errno_is_contention(self):
        self.assertTrue(_is_lock_contention(self.lock_dir, OSError(errno.EEXIST, "x")))

    def test_shim_permission_error_is_contention_when_dir_exists(self):
        """The regression this file is guarding: shim raises PermissionError,
        errno unset, but the lock directory really is there."""
        os.mkdir(self.lock_dir)
        exc = raise_permission_eexist(self.lock_dir)
        self.assertIsNone(exc.errno)
        self.assertNotIsInstance(exc, FileExistsError)  # why the old clause missed it
        self.assertTrue(_is_lock_contention(self.lock_dir, exc))

    def test_permission_error_is_not_contention_when_dir_absent(self):
        """A real permissions failure must not be mistaken for contention."""
        exc = PermissionError(errno.EACCES, "permission denied")
        self.assertFalse(_is_lock_contention(self.lock_dir, exc))

    def test_enospc_is_not_contention(self):
        """Permanent failures must surface, not be waited out."""
        for code in (errno.ENOSPC, errno.EROFS, errno.ENOENT):
            with self.subTest(errno=errno.errorcode[code]):
                self.assertFalse(_is_lock_contention(self.lock_dir, OSError(code, "disk full")))

    def test_shim_eexist_is_contention_even_after_the_holder_released(self):
        """TOCTOU regression: the holder can unlink the lock directory between
        our failed mkdir and our stat, so "the directory is gone" is NOT proof
        the failure was permanent. Classifying it as permanent made roughly one
        concurrent writer in five die with exit 1."""
        self.assertFalse(os.path.exists(self.lock_dir))
        self.assertTrue(_is_lock_contention(self.lock_dir, raise_permission_eexist(self.lock_dir)))

    def test_errno_less_oserror_is_treated_as_contention(self):
        """When the platform withholds errno there is no witness left, so the
        conservative reading is to wait — the deadline is still the backstop."""
        exc = PermissionError("operation not permitted by the sandbox")
        self.assertIsNone(exc.errno)
        self.assertTrue(_is_lock_contention(self.lock_dir, exc))

    def test_non_oserror_is_not_contention(self):
        self.assertFalse(_is_lock_contention(self.lock_dir, RuntimeError("boom")))


class WaitAndAcquire(unittest.TestCase):
    """Contention makes the acquirer wait — it never escapes as a crash."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmp.name, "roadmap.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _patch_mkdir(self, failures, exc_factory):
        """Fail the first `failures` mkdir calls the way a real contender would.

        The failing calls leave the lock directory behind — that is what "another
        writer owns the lock" means on disk, and it is the only signal available
        when the platform reports EEXIST as PermissionError with errno unset.
        Before the call that is allowed to succeed, the directory is removed,
        as if that writer had released the lock.
        """
        import shutil

        real_mkdir = os.mkdir
        state = {"calls": 0}

        def fake_mkdir(path, *a, **kw):
            state["calls"] += 1
            if state["calls"] <= failures:
                if not os.path.isdir(path):
                    real_mkdir(path)
                raise exc_factory(path)
            shutil.rmtree(path, ignore_errors=True)
            return real_mkdir(path, *a, **kw)

        patcher = unittest.mock.patch.object(roadmap.os, "mkdir", fake_mkdir)
        patcher.start()
        self.addCleanup(patcher.stop)
        return state

    def test_shim_contention_is_retried_until_acquired(self):
        state = self._patch_mkdir(3, raise_permission_eexist)
        with roadmap_file_lock(self.target, timeout_seconds=5.0):
            self.assertTrue(os.path.isdir(roadmap_lock_dir(self.target)))
        self.assertGreaterEqual(state["calls"], 4)
        self.assertFalse(os.path.exists(roadmap_lock_dir(self.target)),
                         "lock directory must be released on exit")

    def test_contention_is_retried_when_the_holder_releases_first(self):
        """Same as above, except the failing mkdir leaves nothing behind — the
        holder released the lock before we could look. This is the intermittent
        variant of the crash: it only shows up when the release wins the race.
        """
        real_mkdir = os.mkdir
        state = {"calls": 0}

        def fake_mkdir(path, *a, **kw):
            state["calls"] += 1
            if state["calls"] <= 3:
                raise raise_permission_eexist(path)  # no directory created
            return real_mkdir(path, *a, **kw)

        patcher = unittest.mock.patch.object(roadmap.os, "mkdir", fake_mkdir)
        patcher.start()
        self.addCleanup(patcher.stop)
        with roadmap_file_lock(self.target, timeout_seconds=5.0):
            self.assertTrue(os.path.isdir(roadmap_lock_dir(self.target)))
        self.assertGreaterEqual(state["calls"], 4)

    def test_native_contention_is_retried_until_acquired(self):
        state = self._patch_mkdir(3, lambda p: FileExistsError(errno.EEXIST, "exists"))
        with roadmap_file_lock(self.target, timeout_seconds=5.0):
            pass
        self.assertGreaterEqual(state["calls"], 4)

    def test_owner_json_is_written_while_held(self):
        with roadmap_file_lock(self.target, timeout_seconds=5.0):
            owner_path = os.path.join(roadmap_lock_dir(self.target), "owner.json")
            owner = json.loads(Path(owner_path).read_text(encoding="utf-8"))
            self.assertEqual(owner["pid"], os.getpid())


class NotContention(unittest.TestCase):
    """Real filesystem errors propagate; the lock never swallows them."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmp.name, "roadmap.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_permission_denied_propagates(self):
        def fake_mkdir(path, *a, **kw):
            raise PermissionError(errno.EACCES, "permission denied")

        patcher = unittest.mock.patch.object(roadmap.os, "mkdir", fake_mkdir)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(PermissionError):
            with roadmap_file_lock(self.target, timeout_seconds=0.5):
                pass


class Timeout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tmp.name, "roadmap.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_unresolvable_contention_raises_roadmap_lock_timeout(self):
        """Exit code 2, not an uncaught PermissionError."""
        real_mkdir = os.mkdir

        def fake_mkdir(path, *a, **kw):
            # Lock is held for the whole test: every attempt sees it on disk.
            if not os.path.isdir(path):
                real_mkdir(path)
            raise raise_permission_eexist(path)

        patcher = unittest.mock.patch.object(roadmap.os, "mkdir", fake_mkdir)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(RoadmapLockTimeout):
            with roadmap_file_lock(self.target, timeout_seconds=0.2):
                pass


# ── end-to-end: real processes, real carrier ───────────────

def run_cli(*args, cli=CLI):
    return subprocess.run([PY, str(cli), *map(str, args)],
                          capture_output=True, text=True)


def build_roadmap(path: Path, children: int) -> list[str]:
    r = run_cli("init", path, "--title", "lock-contract", "--storage", "single")
    if r.returncode != 0:
        raise RuntimeError(f"init failed: {r.stderr}")
    ids = []
    for i in range(children):
        r = run_cli("add", path, PARENT, f"child-{i + 1}")
        if r.returncode != 0:
            raise RuntimeError(f"add failed: {r.stderr}")
        ids.append(f"{PARENT}-{i + 1}")
    return ids


def check(data: dict, completed_ids: list[str], expected_children: set[str]) -> list[str]:
    """Invariants on the final carrier. Empty list == pass."""
    problems = []
    nodes = data["nodes"]

    for nid in completed_ids:
        actual = nodes.get(nid, {}).get("status")
        if actual != "completed":
            problems.append(f"{nid} status={actual!r}, expected 'completed' (lost update)")

    parent = nodes.get(PARENT, {})
    kids = parent.get("children", [])
    if any(c not in nodes for c in kids):
        problems.append("parent.children references nodes that do not exist")
    if set(kids) != expected_children:
        problems.append(
            f"parent.children mismatch missing={sorted(expected_children - set(kids))} "
            f"extra={sorted(set(kids) - expected_children)}"
        )
    if len(set(kids)) != len(kids):
        problems.append("parent.children contains duplicates")

    if kids and all(nodes[c]["status"] == "completed" for c in kids):
        if parent.get("status") != "completed":
            problems.append(
                f"parent status={parent.get('status')!r} but every child is completed "
                "(stale rollup)"
            )
    return problems


class ConcurrentWriters(unittest.TestCase):
    """N real processes mutate siblings at the same instant."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "roadmap.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_serial_control(self):
        """Control: the same mutations applied serially. If this fails the
        concurrency cases below prove nothing."""
        ids = build_roadmap(self.path, WRITERS)
        codes = [run_cli("update", self.path, nid, "--status", "completed").returncode
                 for nid in ids]
        self.assertEqual([0] * len(ids), codes)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual([], check(data, ids, set(ids)))

    def test_concurrent_sibling_completion(self):
        for _ in range(REPEATS):
            with self.subTest(attempt=_):
                ids = build_roadmap(self.path, WRITERS)
                procs = [subprocess.Popen(
                    [PY, str(CLI), "update", str(self.path), nid, "--status", "completed"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    for nid in ids]
                outs = [p.communicate() for p in procs]
                codes = [p.returncode for p in procs]

                # The bug this file guards: writers crashed with 1 instead of
                # waiting for the lock (2 = timeout, which is a legal outcome).
                self.assertEqual([0] * len(ids), codes,
                                 f"writer stderr: {[e.strip()[-200:] for _, e in outs]}")
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.assertEqual([], check(data, ids, set(ids)))

    def test_mixed_status_and_structural_writes(self):
        """One process completes siblings while another adds a child: the two
        writers touch different fields of the same document."""
        ids = build_roadmap(self.path, WRITERS)
        jobs = [["update", str(self.path), nid, "--status", "completed"] for nid in ids]
        jobs.append(["add", str(self.path), PARENT, "late-child"])
        procs = [subprocess.Popen([PY, str(CLI), *j],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for j in jobs]
        outs = [p.communicate() for p in procs]
        codes = [p.returncode for p in procs]
        self.assertEqual([0] * len(jobs), codes,
                         f"writer stderr: {[e.strip()[-200:] for _, e in outs]}")

        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual([], check(data, ids, set(ids) | {f"{PARENT}-{WRITERS + 1}"}))

    def test_no_lock_directory_left_behind(self):
        ids = build_roadmap(self.path, WRITERS)
        procs = [subprocess.Popen(
            [PY, str(CLI), "update", str(self.path), nid, "--status", "completed"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for nid in ids]
        for p in procs:
            p.communicate()
        self.assertFalse(os.path.exists(roadmap_lock_dir(str(self.path))),
                         "stale lock directory would wedge every future writer")

    def test_manual_unlock_still_clears_a_stale_lock(self):
        ids = build_roadmap(self.path, 1)
        lock_dir = roadmap_lock_dir(str(self.path))
        os.mkdir(lock_dir)
        self.assertTrue(os.path.isdir(lock_dir))
        unlock_roadmap(str(self.path))
        self.assertFalse(os.path.exists(lock_dir))
        self.assertEqual(0, run_cli("update", self.path, ids[0],
                                    "--status", "completed").returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
