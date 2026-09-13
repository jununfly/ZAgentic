"""#99 S1 — bundle carrier 的子节点序号（与 single-file 同语义）。

直接继承 `test_child_id_single_file.py` 里的 Slice 类，只换掉存储
（`--storage bundle`）。继承而非复制，是"两个 carrier 同语义"这条不变式唯一的
机械证明——复制一份副本的话，改了一边另一边不会红。

本刀的另一半价值在 `roadmap_bundle.py`：它原本自己写了一遍
`int(children[-1].split("-")[-1]) + 1`，现在两个 carrier 共用 `roadmap.py` 里的
`next_child_index`。

运行：python tests/test_child_id_bundle.py
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

# 以模块方式引用，不用 from-import：unittest 的 loader 会收集模块里出现的
# 每一个 TestCase 子类，from-import 会把 single-file 那边那一份也收进来跑一遍，
# 计数虚高且看不出哪份是哪个 carrier 的。
import test_child_id_single_file as sf  # noqa: E402


class BundleStorageMixin:
    """把 Slice 类接到 bundle carrier 上：换目录路径 + 换 init 的 storage。"""

    def setUp(self):
        super().setUp()
        self.roadmap = self.workdir / "roadmap.bundle"

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--storage", "bundle", "--title", "child id")


class Slice01NoReuseAfterTailDeletionBundleTest(
    BundleStorageMixin, sf.Slice01NoReuseAfterTailDeletionTest
):
    """同 Slice01，跑在 bundle carrier 上。"""


class Slice02UnchangedWithoutDeletionBundleTest(
    BundleStorageMixin, sf.Slice02UnchangedWithoutDeletionTest
):
    """同 Slice02，跑在 bundle carrier 上。"""


if __name__ == "__main__":
    unittest.main()
