"""#105 S3 — bundle carrier 的 uid 引用解析（与 single-file 同语义）。

继承 `test_resolve_node_single_file.py` 的 Slice，只换存储（`--storage bundle`）。
解析规则两个 carrier 共用一份 `roadmap.resolve_node`，所以行为一致，这里不复制断言。

运行：python tests/test_resolve_node_bundle.py
"""

import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import test_resolve_node_single_file as sf  # noqa: E402


class BundleStorageMixin:
    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "resolve")


class Slice01ResolveByUidBundleTest(BundleStorageMixin, sf.Slice01ResolveByUidTest):
    """同 Slice01，跑在 bundle carrier 上。"""


class Slice02ResolveErrorsBundleTest(BundleStorageMixin, sf.Slice02ResolveErrorsTest):
    """同 Slice02：uid 报错清晰、错的显示 id 仍走 legacy KeyError。"""


class Slice03OtherCommandsAcceptUidBundleTest(
    BundleStorageMixin, sf.Slice03OtherCommandsAcceptUidTest
):
    """同 Slice03：update / decide / edge / siblings 都认 uid。"""


if __name__ == "__main__":
    unittest.main()
