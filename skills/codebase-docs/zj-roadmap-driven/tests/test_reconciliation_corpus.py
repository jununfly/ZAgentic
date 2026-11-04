from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


CORPUS = Path(__file__).with_name("reconciliation_corpus.py")
SPEC = importlib.util.spec_from_file_location("reconciliation_corpus", CORPUS)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReconciliationCorpusContractTest(unittest.TestCase):
    def test_corpus_has_thirty_labeled_scenarios_and_required_classes(self):
        scenarios = MODULE.SCENARIOS
        self.assertEqual(len(scenarios), 30)
        self.assertEqual(len({scenario["id"] for scenario in scenarios}), 30)
        labels = {scenario["label"] for scenario in scenarios}
        for required in (
            "exact duplicate",
            "near duplicate different exit criteria",
            "cross-subtree overlap",
            "completed WorkItem refinement",
            "dependency reversal",
            "split one obligation",
            "merge duplicate owners",
            "combined changes form a cycle",
            "stale revision",
            "renderer publication failure",
        ):
            self.assertIn(required, labels)


if __name__ == "__main__":
    unittest.main()
