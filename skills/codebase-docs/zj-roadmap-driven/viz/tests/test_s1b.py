#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1b: a view-receipt is a disposable, portable, mergeable, expirable cache.

Seams under test: receipt.write_receipt / load_receipt / merge_baselines /
is_expired, plus the published viz.cli flags. No private helper is imported.
Expected field sets below are independent literals, never derived from the
module under test.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from viz import receipt  # noqa: E402
from viz.cli import main  # noqa: E402

SAMPLE = SKILL / "demos" / "roadmap_viz_sample.json"
CLI_REF = SKILL / "references" / "roadmap-cli.md"
PRODUCT = SKILL.parent.parent.parent / "docs" / "designs" / "zj-roadmap-visual-review-product.md"

V1_FIELDS = {
    "version", "anchor", "carrier_revision", "theta", "seen_item_hashes",
}
V2_FIELDS = V1_FIELDS | {"device_id", "generated_at", "ttl_seconds"}
V1_VERSION = "zj-roadmap-view-receipt/v1"
V2_VERSION = "zj-roadmap-view-receipt/v2"


def _write(path, *, device_id=None, ttl_seconds=None, now=1000.0,
           hashes=None, anchor="a|token", revision="rev-1", theta=0.45):
    """Call the published writer with only the fields this slice cares about."""
    return receipt.write_receipt(
        path, anchor=anchor, carrier_revision=revision, theta=theta,
        hashes={"1": "h1", "1-1": "h11"} if hashes is None else hashes,
        device_id=device_id, ttl_seconds=ttl_seconds, now=now,
    )


def _loaded(path, *, now=1000.0):
    got, warning = receipt.load_receipt(path, now=now)
    if warning:
        raise AssertionError(f"fixture receipt should be readable: {warning}")
    return got


class PortableReceipt(unittest.TestCase):
    def test_v2_receipt_carries_device_and_ttl_and_survives_a_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "isolated" / "receipt.json"
            _write(path, device_id="mac-a", ttl_seconds=3600, now=1000.0)
            saved_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                got, warning = receipt.load_receipt(path, now=1000.0 + 10)
            finally:
                os.chdir(saved_cwd)
            self.assertIsNone(warning)
            self.assertEqual(V2_FIELDS, set(got))
            self.assertEqual(V2_VERSION, got["version"])
            self.assertEqual("mac-a", got["device_id"])
            self.assertEqual(1000.0, got["generated_at"])
            self.assertEqual(3600, got["ttl_seconds"])
            self.assertEqual({"1": "h1", "1-1": "h11"}, got["seen_item_hashes"])

    def test_v1_writer_stays_byte_compatible_with_s1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            receipt.write_receipt(
                path, anchor="a|token", carrier_revision="rev-1", theta=0.45,
                hashes={"1": "h1"},
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(V1_FIELDS, set(payload))
            self.assertEqual(V1_VERSION, payload["version"])
            got, warning = receipt.load_receipt(path)
            self.assertIsNone(warning)
            self.assertEqual({"1": "h1"}, got["seen_item_hashes"])

    def test_v2_receipt_is_a_plain_portable_json_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            _write(path, device_id="mac-a", ttl_seconds=3600)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(V2_FIELDS, set(payload))
            self.assertEqual(sorted(payload), list(payload))
            self.assertEqual({"1": "h1", "1-1": "h11"}, payload["seen_item_hashes"])


class CrossDeviceMerge(unittest.TestCase):
    def test_same_context_receipts_merge_into_a_usable_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "mac-a.receipt.json"
            b = Path(tmp) / "mac-b.receipt.json"
            _write(a, device_id="mac-a", ttl_seconds=3600, hashes={"1": "h1"})
            _write(b, device_id="mac-b", ttl_seconds=3600, hashes={"1-1": "h11"})
            baseline, warning = receipt.merge_baselines(
                _loaded(a), _loaded(b), now=1010.0,
            )
            self.assertIsNone(warning)
            self.assertEqual({"1": "h1", "1-1": "h11"},
                             baseline["seen_item_hashes"])
            delta = receipt.compute_delta(
                {"1": "h1", "1-1": "h11", "2": "h2"}, baseline, None,
            )
            self.assertEqual("delta", delta["mode"])
            self.assertEqual(["2"], delta["added"])
            self.assertEqual(2, delta["stable-folded"])

    def test_conflicting_hashes_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            _write(a, device_id="mac-a", ttl_seconds=3600, hashes={"1": "h1"})
            _write(b, device_id="mac-b", ttl_seconds=3600, hashes={"1": "OTHER"})
            baseline, warning = receipt.merge_baselines(
                _loaded(a), _loaded(b), now=1010.0,
            )
            self.assertIsNone(baseline)
            self.assertIn("fail-closed", warning)

    def test_any_context_mismatch_fails_closed(self):
        cases = {
            "anchor": {"anchor": "other|token"},
            "revision": {"revision": "rev-2"},
            "theta": {"theta": 0.20},
        }
        with tempfile.TemporaryDirectory() as tmp:
            for label, overrides in cases.items():
                with self.subTest(mismatch=label):
                    a = Path(tmp) / f"a-{label}.json"
                    b = Path(tmp) / f"b-{label}.json"
                    _write(a, device_id="mac-a", ttl_seconds=3600)
                    _write(b, device_id="mac-b", ttl_seconds=3600, **overrides)
                    baseline, warning = receipt.merge_baselines(
                        _loaded(a), _loaded(b), now=1010.0,
                    )
                    self.assertIsNone(baseline)
                    self.assertIn("fail-closed", warning)

    def test_mixed_versions_and_v1_receipts_are_not_mergeable(self):
        with tempfile.TemporaryDirectory() as tmp:
            v1 = Path(tmp) / "v1.json"
            v1b = Path(tmp) / "v1b.json"
            v2 = Path(tmp) / "v2.json"
            _write(v1)
            _write(v1b)
            _write(v2, device_id="mac-b", ttl_seconds=3600)
            for left, right in ((v1, v1b), (v1, v2), (v2, v1)):
                with self.subTest(pair=(left.name, right.name)):
                    baseline, warning = receipt.merge_baselines(
                        _loaded(left), _loaded(right), now=1010.0,
                    )
                    self.assertIsNone(baseline)
                    self.assertIn("fail-closed", warning)

    def test_same_device_receipt_is_idempotent_not_a_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            _write(a, device_id="mac-a", ttl_seconds=3600, hashes={"1": "h1"})
            _write(b, device_id="mac-a", ttl_seconds=3600, hashes={"1-1": "h11"})
            baseline, warning = receipt.merge_baselines(
                _loaded(a), _loaded(b), now=1010.0,
            )
            self.assertIsNone(warning)
            self.assertEqual({"1": "h1"}, baseline["seen_item_hashes"])


class ExpiryAndPublishedEntrypoints(unittest.TestCase):
    def test_expiry_boundary_is_explicit_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            _write(path, device_id="mac-a", ttl_seconds=3600, now=1000.0)
            at_boundary = _loaded(path, now=4600.0)
            self.assertFalse(receipt.is_expired(at_boundary, now=4600.0))
            got, warning = receipt.load_receipt(path, now=4600.1)
            self.assertIsNone(got)
            self.assertIn("fail-closed", warning)
            delta = receipt.compute_delta({"1": "h1"}, got, warning)
            self.assertEqual("full-fallback", delta["mode"])
            with self.assertRaises(ValueError):
                _write(Path(tmp) / "bad.json", device_id="mac-a", ttl_seconds=0)

    def test_merge_rejects_an_expired_remote_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            _write(a, device_id="mac-a", ttl_seconds=3600, now=1000.0)
            _write(b, device_id="mac-b", ttl_seconds=10, now=1000.0)
            baseline, warning = receipt.merge_baselines(
                _loaded(a, now=1000.0), _loaded(b, now=1000.0), now=1011.0,
            )
            self.assertIsNone(baseline)
            self.assertIn("fail-closed", warning)

    def _run_cli(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                return main([str(SAMPLE), *extra])
            except SystemExit as exc:
                self.fail(f"viz.cli rejected a published S1b flag: {exc}")

    def test_cli_exposes_and_runs_the_s1b_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "local.receipt.json"
            remote = Path(tmp) / "remote.receipt.json"
            delta_path = Path(tmp) / "delta.json"
            ir_path = Path(tmp) / "ir.json"
            carrier_before = SAMPLE.read_bytes()
            self.assertEqual(0, self._run_cli(
                "--receipt", str(local), "--device-id", "mac-a",
                "--receipt-ttl", "3600", "--out", str(Path(tmp) / "view.html"),
            ))
            payload = json.loads(local.read_text(encoding="utf-8"))
            self.assertEqual(V2_FIELDS, set(payload))
            self.assertEqual("mac-a", payload["device_id"])
            # Simulate the other device carrying the same view context.
            payload["device_id"] = "mac-b"
            remote.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True),
                              encoding="utf-8")
            self.assertEqual(0, self._run_cli(
                "--receipt", str(local), "--merge-receipt", str(remote),
                "--device-id", "mac-a", "--receipt-ttl", "3600",
                "--delta", str(delta_path), "--ir", str(ir_path),
            ))
            delta = json.loads(delta_path.read_text(encoding="utf-8"))
            self.assertEqual("delta", delta["mode"],
                             "a mergeable peer must not degrade to a full view")
            view_ir = json.loads(ir_path.read_text(encoding="utf-8"))
            # The corpus has a card literally labelled "receipt 契约"; what
            # must never appear is receipt *state*, not the English word.
            raw_ir = json.dumps(view_ir)
            for forbidden in ("seen_item_hashes", "device_id", "ttl_seconds",
                              "generated_at", "merge_receipt"):
                self.assertNotIn(forbidden, raw_ir)
            self.assertEqual(carrier_before, SAMPLE.read_bytes(),
                             "merged baseline leaked into the carrier")

    def test_cli_reference_publishes_the_s1b_flags(self):
        body = CLI_REF.read_text(encoding="utf-8")
        for flag in ("--device-id", "--receipt-ttl", "--merge-receipt"):
            self.assertIn(flag, body, f"CLI reference does not publish {flag}")
        self.assertIn("跨设备", body)

    def test_product_ledger_no_longer_marks_s1b_as_open(self):
        body = PRODUCT.read_text(encoding="utf-8")
        self.assertIn("S1b delivered", body)
        self.assertNotIn("不擅自加", body)


class MultiPeerSync(unittest.TestCase):
    """S1c: one Human-addressed path per peer, repeatable --merge-receipt."""

    def _run(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                return main([str(SAMPLE), *extra])
            except SystemExit as exc:
                self.fail(f"viz.cli rejected a published flag: {exc}")

    def test_chain_merges_three_devices_into_one_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "local.json"
            peer_a = Path(tmp) / "a.json"
            peer_b = Path(tmp) / "b.json"
            _write(local, device_id="mac-a", ttl_seconds=3600, hashes={"1": "h1"})
            _write(peer_a, device_id="mac-b", ttl_seconds=3600, hashes={"1-1": "h11"})
            _write(peer_b, device_id="mac-c", ttl_seconds=3600, hashes={"2": "h2"})
            baseline, warning = receipt.merge_baseline_chain(
                _loaded(local), [_loaded(peer_a), _loaded(peer_b)], now=1010.0,
            )
            self.assertIsNone(warning)
            self.assertEqual({"1": "h1", "1-1": "h11", "2": "h2"},
                             baseline["seen_item_hashes"])
            delta = receipt.compute_delta(
                {"1": "h1", "1-1": "h11", "2": "h2"}, baseline, None,
            )
            self.assertEqual("delta", delta["mode"])
            self.assertEqual(3, delta["stable-folded"])

    def test_any_unmergeable_peer_fails_the_whole_chain_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "local.json"
            good = Path(tmp) / "good.json"
            bad = Path(tmp) / "bad.json"
            _write(local, device_id="mac-a", ttl_seconds=3600, hashes={"1": "h1"})
            _write(good, device_id="mac-b", ttl_seconds=3600, hashes={"1-1": "h11"})
            _write(bad, device_id="mac-c", ttl_seconds=3600,
                   hashes={"2": "h2"}, revision="rev-2")
            baseline, warning = receipt.merge_baseline_chain(
                _loaded(local), [_loaded(good), _loaded(bad)], now=1010.0,
            )
            self.assertIsNone(baseline)
            self.assertIn("fail-closed", warning)

    def test_cli_accepts_repeated_merge_receipt_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "local.receipt.json"
            first = Path(tmp) / "first.receipt.json"
            second = Path(tmp) / "second.receipt.json"
            delta_path = Path(tmp) / "delta.json"
            self.assertEqual(0, self._run(
                "--receipt", str(local), "--device-id", "mac-a",
                "--receipt-ttl", "3600",
            ))
            base = json.loads(local.read_text(encoding="utf-8"))
            all_hashes = base["seen_item_hashes"]
            keys = sorted(all_hashes)
            third = len(keys) // 3
            # This device saw only the first third; each peer supplies one of
            # the other two. Honouring only the last flag leaves a visible gap.
            base["seen_item_hashes"] = {k: all_hashes[k] for k in keys[:third]}
            local.write_text(json.dumps(base, ensure_ascii=False, sort_keys=True),
                             encoding="utf-8")
            for path, device, subset in (
                (first, "mac-b", keys[third : 2 * third]),
                (second, "mac-c", keys[2 * third :]),
            ):
                peer = dict(base)
                peer["device_id"] = device
                peer["seen_item_hashes"] = {k: all_hashes[k] for k in subset}
                path.write_text(json.dumps(peer, ensure_ascii=False, sort_keys=True),
                                encoding="utf-8")
            self.assertEqual(0, self._run(
                "--receipt", str(local),
                "--merge-receipt", str(first),
                "--merge-receipt", str(second),
                "--device-id", "mac-a", "--receipt-ttl", "3600",
                "--delta", str(delta_path),
            ))
            delta = json.loads(delta_path.read_text(encoding="utf-8"))
            self.assertEqual([], delta["added"],
                             "only the last --merge-receipt was honoured")
            self.assertEqual([], delta["removed"])
            self.assertEqual(len(all_hashes), delta["stable-folded"])


if __name__ == "__main__":
    unittest.main()
