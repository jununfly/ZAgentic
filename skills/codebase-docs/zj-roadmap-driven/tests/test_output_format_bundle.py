"""#104 S5 — bundle carrier 的输出格式 / context / next（与 single-file 同语义）。

继承 `test_output_format_single_file.py` 的 Slice，只换存储（`--storage bundle`）。
发射器与 context/next 的判定两个 carrier 共用一份 `roadmap` 模块级函数
（`_emit` 在 CLI 层、`node_context` / 就绪排序在 carrier 方法里委托），所以行为一致，
这里不复制断言。

运行：python tests/test_output_format_bundle.py
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

import test_output_format_single_file as sf  # noqa: E402


class BundleStorageMixin:
    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "fmt")


class SliceAGetFormatBundleTest(BundleStorageMixin, sf.SliceAGetFormatTest):
    """同 SliceA：get 经 --format/--fields/--quiet，默认逐字节不变。"""


class SliceBStructuralFormatBundleTest(BundleStorageMixin, sf.SliceBStructuralFormatTest):
    """同 SliceB：stats/decisions/edge list/focus 接格式控制。"""


class SliceCRowFormatBundleTest(BundleStorageMixin, sf.SliceCRowFormatTest):
    """同 SliceC：行式命令 --quiet/--format。"""


class SliceDContextBundleTest(BundleStorageMixin, sf.SliceDContextTest):
    """同 SliceD：context 上游/下游/阻塞链。"""


class SliceENextBundleTest(BundleStorageMixin, sf.SliceENextTest):
    """同 SliceE：next 就绪优先建议。"""


if __name__ == "__main__":
    unittest.main()
