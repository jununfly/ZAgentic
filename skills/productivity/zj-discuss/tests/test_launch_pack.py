"""Regression tests: zj-discuss static launch-pack generator.

Guard for discussion item 2 (``zj-discuss launch <sub-doc>`` static generator),
prescribed by
``discussions/improve-zj-discuss-with-decision-model-and-gstack/MASTER.md``
but only *documented* in the previous round. These tests fail loudly if the
generator stops being a real, runnable artifact.

Seam: the CLI (``main(argv) -> int``) plus the pure helpers, so the suite runs
in-process and exercises the same entry point a Human would.
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import launch_pack  # noqa: E402

REAL_MATRIX = SKILL_DIR / "references" / "role-matrix.md"
SUBDOC_NAME = "sub-01-demo.md"

SUBDOC_TEMPLATE = """# 子问题：示例子问题

> stub

## 上下文

- **所属主文档：** [../MASTER.md](../MASTER.md)
- **本子问题独立性：** 仅为测试
- **成功判据：** 生成器能解析出声明必需集
- **声明必需角色集：** {roles}

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`
<待撰写>

## conclusion（含沉淀指令）

- **状态协议：** DONE
"""


def _write_subdoc(d: Path, roles: str = "B,C,A,T") -> Path:
    p = d / SUBDOC_NAME
    p.write_text(SUBDOC_TEMPLATE.format(roles=roles), encoding="utf-8")
    return p


class DeclaredSetParsing(unittest.TestCase):
    def test_parses_comma_separated_keys(self):
        self.assertEqual(
            launch_pack.parse_declared_set(_make_text("B,C,A,T")),
            ["B", "C", "A", "T"],
        )

    def test_tolerates_fullwidth_comma_and_spaces(self):
        self.assertEqual(
            launch_pack.parse_declared_set(_make_text("B， C、A；T")),
            ["B", "C", "A", "T"],
        )

    def test_single_role(self):
        self.assertEqual(launch_pack.parse_declared_set(_make_text("T")), ["T"])

    def test_missing_field_returns_empty(self):
        self.assertEqual(launch_pack.parse_declared_set("# 没有该字段\n"), [])


def _make_text(roles: str) -> str:
    return "- **声明必需角色集：** {}\n".format(roles)


class RolePoolFromMatrix(unittest.TestCase):
    def test_real_matrix_contains_base_and_optional(self):
        pool = launch_pack.load_role_pool(REAL_MATRIX)
        for key in ("B", "C", "A", "T", "S", "O", "D", "L", "F", "U", "R", "P", "E"):
            self.assertIn(key, pool, "role {} missing from parsed pool".format(key))

    def test_role_has_name_and_intro(self):
        pool = launch_pack.load_role_pool(REAL_MATRIX)
        self.assertTrue(pool["B"]["name"])
        self.assertTrue(pool["B"]["intro"])


class GenerateLaunchPacks(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.subdoc = _write_subdoc(self.tmp, "B,C,A,T")
        self.out = self.tmp / "briefings"

    def tearDown(self):
        self._tmp.cleanup()

    def test_one_pack_per_declared_role(self):
        packs = launch_pack.generate(self.subdoc, None, self.out, REAL_MATRIX)
        self.assertEqual(len(packs), 4)
        names = sorted(p.name for p in packs)
        for role in ("B", "C", "A", "T"):
            self.assertTrue(
                any("-{}.".format(role) in n or "-{}.md".format(role) in n for n in names),
                "no pack written for role {} in {}".format(role, names),
            )

    def test_pack_carries_read_order_and_paste_command(self):
        packs = launch_pack.generate(self.subdoc, None, self.out, REAL_MATRIX)
        for pack in packs:
            body = pack.read_text(encoding="utf-8")
            self.assertIn(str(self.subdoc), body, "pack lacks the Read-original order")
            self.assertIn("zj-discuss-view --role ", body, "pack lacks the paste command")

    def test_roles_override_declared_set(self):
        packs = launch_pack.generate(self.subdoc, ["B"], self.out, REAL_MATRIX)
        self.assertEqual(len(packs), 1)

    def test_cli_exit_zero_and_writes_files(self):
        code = launch_pack.main(
            ["--out", str(self.out), str(self.subdoc)]
        )
        self.assertEqual(code, 0)
        self.assertTrue(any(self.out.iterdir()))


class Refusals(unittest.TestCase):
    def test_missing_subdoc_refuses(self):
        with self.assertRaises(launch_pack.Refusal):
            launch_pack.generate(Path("/nope/does-not-exist.md"), None, Path("/tmp"), REAL_MATRIX)

    def test_unknown_role_refused(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            sd = _write_subdoc(d, "B,Z")
            with self.assertRaises(launch_pack.Refusal):
                launch_pack.generate(sd, None, d / "out", REAL_MATRIX)

    def test_custom_role_allowed_with_flag(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            sd = _write_subdoc(d, "B,Z")
            packs = launch_pack.generate(sd, None, d / "out", REAL_MATRIX, allow_custom=True)
            self.assertEqual(len(packs), 2)


class NoRuntimeInvariant(unittest.TestCase):
    """The prescription forbids a session-orchestration runtime.

    The generator must be purely static: it writes text, never spawns sessions,
    shells out, or opens sockets. This test is the mechanical guard.
    """

    def test_script_imports_no_runtime_primitives(self):
        src = (SCRIPTS_DIR / "launch_pack.py").read_text(encoding="utf-8")
        for banned in ("import subprocess", "os.system", "import socket", "popen"):
            self.assertNotIn(banned, src, "generator regressed into a runtime: " + banned)


if __name__ == "__main__":
    unittest.main()
