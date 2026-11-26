#!/usr/bin/env python3
"""§4.4 single-writer file lock — invariant locks."""

import multiprocessing
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
for p in (str(SKILL_DIR), str(SKILL_DIR / "scripts")):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

import dp_driven_lock as L


def _holder(carrier_path: str, hold_seconds: float, ready_file: str):
    """Child-process helper: acquire and hold for a duration; touch a ready file first."""
    sys.path.insert(0, str(Path(carrier_path).parent))   # for sidecar visibility
    with L.acquire(carrier_path, timeout=5.0):
        Path(ready_file).write_text("ready\n")
        time.sleep(hold_seconds)


class LockAcquire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "dp_driven.sqlite")
        Path(self.db).write_bytes(b"")   # dummy carrier

    def test_lock_path_naming(self):
        self.assertEqual(L.lock_path(self.db), self.db + ".lock")

    def test_acquire_releases(self):
        with L.acquire(self.db, timeout=1.0):
            pass
        # reacquire succeeds → first was released
        with L.acquire(self.db, timeout=1.0):
            pass

    def test_cross_process_exclusive(self):
        """§4.4 single writer: while child holds the lock, parent's acquire times out."""
        ready = str(Path(self.tmp.name) / "ready.txt")
        proc = multiprocessing.Process(target=_holder, args=(self.db, 1.5, ready))
        proc.start()
        try:
            # wait until child has acquired
            for _ in range(200):
                if os.path.exists(ready):
                    break
                time.sleep(0.02)
            else:
                self.fail("child never signalled readiness")
            with self.assertRaises(L.LockTimeout):
                with L.acquire(self.db, timeout=0.2, poll=0.02):
                    self.fail("parent unexpectedly acquired while child holds lock")
        finally:
            proc.join(timeout=3.0)
            if proc.is_alive():
                proc.terminate()

    def test_lock_file_created(self):
        with L.acquire(self.db, timeout=1.0):
            self.assertTrue(os.path.exists(self.db + ".lock"))


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    unittest.main(verbosity=2)
