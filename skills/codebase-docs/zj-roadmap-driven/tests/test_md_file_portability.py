"""#169 — md_file 支持相对路径：同一份 roadmap 跨机（macOS/Windows）共享不失联。

旧行为：`link` 强制 `os.path.abspath`，`md_file` 恒为**机器相关绝对路径**。
同一份 roadmap 经 Git 在 macOS ↔ Windows 之间共享时，`render` 在"没写路径"的
那台机上把 `C:\\workspace\\...\\ROADMAP.md` 当成相对路径，在仓库根造出同名垃圾
目录，而真正的 `app/ROADMAP.md` 反而不更新。

三条不变量（本文件守的门）：

1. `link` 存**相对载体文件目录的 posix 相对路径**，不存机器相关绝对路径；
2. `render` 把相对 `md_file` 相对**载体文件所在目录**解析 —— 仓库整体搬到
   另一个根路径（模拟另一台机器上仓库位置不同）后仍命中正确文件，且存储值
   本身不被改写；
3. **异机绝对路径宁可报错也不静默写文件** —— `C:\\...` 落在 POSIX 上、
   `/Users/...` 落在 nt 上都返 `E_MD_PATH`，不再污染仓库。

carrier 契约：single 与 sqlite 两个 carrier 各跑一遍（#116 契约纪律）。

运行：python tests/test_md_file_portability.py
"""

import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import (  # noqa: E402
    ERROR_EXIT_CODES,
    MdFileNotPortable,
    Roadmap,
    resolve_md_file,
    to_relative_md_file,
)
from roadmap_sqlite import RoadmapSqlite  # noqa: E402

CLI = SKILL_DIR / "roadmap_cli.py"
TMP_ROOT = Path(os.environ.get("TMPDIR") or "/tmp")

# 两条"别人机器上"的路径：一台 Windows、一台 macOS。
WINDOWS_MD = "C:\\workspace\\ZAgentic\\app\\ROADMAP.md"
POSIX_MD = "/Users/bilibili/workspace/ZAgentic/app/ROADMAP.md"


class MdFilePortabilityContractTest:
    """抽象契约基类——不继承 unittest.TestCase，避免被 loadTestsFromModule 收集。

    两个 carrier 的具体子类各自继承 (本类, unittest.TestCase)。
    carrier 相关构造交给子类 hook（#116 mixin 纪律）。
    """

    def setUp(self):
        # 不用 tempfile：本机 Security Center 会拦临时目录的删除，导致
        # tempfile.gettempdir() 在探测阶段就判定"没有可用临时目录"（环境噪音，
        # 与被测逻辑无关）。自建目录 + 清理时忽略删除失败。落点取系统 TMPDIR
        # 而不是 /tmp —— /tmp 下 sqlite 的 journal I/O 会被同一策略拦掉。
        self.scratch = TMP_ROOT / "zj-mdfile-{}".format(uuid.uuid4().hex)
        self.scratch.mkdir(parents=True)
        self.root = self.scratch.resolve()
        self.app = self.root / "app"
        self.app.mkdir()
        self.carrier_path = self._build()

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)
        shutil.rmtree(self.scratch.parent / (self.scratch.name + "-other-machine"),
                      ignore_errors=True)

    # ── carrier 相关 hook（子类实现）─────────────────────────

    def _build(self):
        """在 self.app 下建一个含根节点的 carrier，返回其路径（Path）。"""
        raise NotImplementedError

    def _carrier(self, path=None):
        """从给定路径重新加载 carrier（落盘后回读，不复用内存对象）。"""
        raise NotImplementedError

    # ── 共用 helper ────────────────────────────────────────

    def _stored_md_file(self, path=None):
        return self._carrier(path).data.get("metadata", {}).get("md_file", "")

    def _set_md_file_raw(self, value, path=None):
        """原样写入 md_file（`relative=False` = 兼容既有绝对路径台账）。"""
        carrier = self._carrier(path)
        carrier.link_md_file(value, relative=False)
        carrier.save()

    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(self.root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    # ── 契约 1：存储形态是相对路径 ──────────────────────────

    def test_link_same_dir_absolute_stores_relative(self):
        carrier = self._carrier()
        carrier.link_md_file(str(self.app / "ROADMAP.md"))
        carrier.save()

        self.assertEqual(self._stored_md_file(), "ROADMAP.md")

    def test_link_nested_absolute_stores_relative_with_posix_separator(self):
        nested = self.root / "docs" / "ROADMAP.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("# 计划\n", encoding="utf-8")

        carrier = self._carrier()
        carrier.link_md_file(str(nested))
        carrier.save()

        # 正斜杠而不是反斜杠：posix 分隔符在两台机上都能被打开。
        self.assertEqual(self._stored_md_file(), "../docs/ROADMAP.md")

    def test_init_with_absolute_md_file_stores_relative(self):
        carrier = self._carrier()
        carrier.init(title="portable", description="", md_file=str(self.app / "ROADMAP.md"))
        carrier.save()

        self.assertEqual(self._stored_md_file(), "ROADMAP.md")

    def test_relative_input_is_left_alone(self):
        carrier = self._carrier()
        carrier.link_md_file("ROADMAP.md")
        carrier.save()

        self.assertEqual(self._stored_md_file(), "ROADMAP.md")

    # ── 契约 2：render 相对载体目录解析 + 可搬移 ───────────────

    def test_render_writes_next_to_carrier_not_elsewhere(self):
        carrier = self._carrier()
        carrier.link_md_file(str(self.app / "ROADMAP.md"))
        carrier.save()

        target = self._carrier().write_markdown_section()

        self.assertEqual(Path(target).resolve(), (self.app / "ROADMAP.md").resolve())
        self.assertTrue((self.app / "ROADMAP.md").exists())

    def test_render_follows_the_repo_after_it_moves(self):
        """把整个仓库搬到另一个根路径 = 换一台机器：仍写仓库内那个文件。"""
        carrier = self._carrier()
        carrier.link_md_file(str(self.app / "ROADMAP.md"))
        carrier.save()

        moved_root = self.root.parent / (self.root.name + "-other-machine")
        shutil.copytree(self.root, moved_root)
        moved_carrier = moved_root / self.carrier_path.relative_to(self.root)

        target = self._carrier(moved_carrier).write_markdown_section()

        self.assertEqual(Path(target).resolve(), (moved_root / "app" / "ROADMAP.md").resolve())
        # 存储值不被改写 —— 否则两台机会在 Git 里对 md_file 乒乓漂移。
        self.assertEqual(self._stored_md_file(moved_carrier), "ROADMAP.md")
        # 原来那台机器上的文件不被这次 render 碰过。
        self.assertFalse((self.app / "ROADMAP.md").exists())

    def test_legacy_absolute_md_file_still_works(self):
        """既有台账里的本机绝对路径必须照旧可用（兼容，不是破坏性改动）。"""
        legacy = self.app / "LEGACY.md"
        self._set_md_file_raw(str(legacy))

        target = self._carrier().write_markdown_section()

        self.assertEqual(Path(target).resolve(), legacy.resolve())
        self.assertTrue(legacy.exists())

    # ── 契约 3：异机绝对路径报错而不是造垃圾 ───────────────────

    def test_windows_absolute_md_file_refuses_to_write(self):
        self._set_md_file_raw(WINDOWS_MD)

        with self.assertRaises(MdFileNotPortable) as ctx:
            self._carrier().write_markdown_section()

        self.assertEqual(ctx.exception.code, "E_MD_PATH")
        # 关键：仓库里没有多出 `C:` 开头的垃圾目录/文件。
        self.assertFalse(any(p.name.startswith("C:") for p in self.root.rglob("*")))

    def test_cli_render_windows_absolute_exits_with_e_md_path(self):
        self._set_md_file_raw(WINDOWS_MD)

        result = self._run_cli("render", self.carrier_path)

        self.assertEqual(result.returncode, ERROR_EXIT_CODES["E_MD_PATH"])
        self.assertIn("E_MD_PATH", result.stderr)
        self.assertFalse((self.root / "C:").exists())

    # ── CLI 缝 ─────────────────────────────────────────────

    def test_cli_link_then_render_lands_in_the_repo(self):
        linked = self._run_cli("link", self.carrier_path, str(self.app / "ROADMAP.md"))
        self.assertEqual(linked.returncode, 0, linked.stderr)

        rendered = self._run_cli("render", self.carrier_path)
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.assertIn(str((self.app / "ROADMAP.md").resolve()), rendered.stdout)
        self.assertTrue((self.app / "ROADMAP.md").exists())

    def test_cli_link_reports_the_stored_relative_value(self):
        result = self._run_cli("link", self.carrier_path, str(self.app / "ROADMAP.md"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ROADMAP.md", result.stdout)
        self.assertEqual(self._stored_md_file(), "ROADMAP.md")


class SingleFileCarrierTest(MdFilePortabilityContractTest, unittest.TestCase):
    def _build(self):
        path = self.app / "roadmap.json"
        r = Roadmap(str(path))
        r.init(title="portable", description="")
        r.save()
        return path

    def _carrier(self, path=None):
        r = Roadmap(str(path or self.carrier_path))
        r.load()
        return r


class SqliteCarrierTest(MdFilePortabilityContractTest, unittest.TestCase):
    def _build(self):
        path = self.app / "roadmap.sqlite"
        r = RoadmapSqlite(str(path))
        r.init(title="portable", description="")
        r.save()
        return path

    def _carrier(self, path=None):
        r = RoadmapSqlite(str(path or self.carrier_path))
        r.load()
        return r


class ResolveMdFileTest(unittest.TestCase):
    """纯函数层：两台机的命名体系互不认识，判定要能脱离本机确定化测试。"""

    CARRIER = "/repo/app/roadmap.json"

    def test_relative_resolves_against_the_carrier_dir(self):
        self.assertEqual(
            resolve_md_file("ROADMAP.md", self.CARRIER, os_name="posix"),
            "/repo/app/ROADMAP.md",
        )

    def test_relative_is_normalized(self):
        self.assertEqual(
            resolve_md_file("md/../ROADMAP.md", self.CARRIER, os_name="posix"),
            "/repo/app/ROADMAP.md",
        )

    def test_empty_returns_empty(self):
        self.assertEqual(resolve_md_file("", self.CARRIER), "")

    def test_posix_absolute_is_native_on_posix(self):
        self.assertEqual(resolve_md_file(POSIX_MD, self.CARRIER, os_name="posix"), POSIX_MD)

    def test_windows_absolute_is_native_on_nt(self):
        self.assertEqual(resolve_md_file(WINDOWS_MD, self.CARRIER, os_name="nt"), WINDOWS_MD)

    def test_msys_absolute_is_native_on_nt(self):
        self.assertEqual(
            resolve_md_file("/c/Users/zj/repo/app/ROADMAP.md", self.CARRIER, os_name="nt"),
            "/c/Users/zj/repo/app/ROADMAP.md",
        )

    def test_windows_absolute_is_foreign_on_posix(self):
        with self.assertRaises(MdFileNotPortable):
            resolve_md_file(WINDOWS_MD, self.CARRIER, os_name="posix")

    def test_posix_absolute_is_foreign_on_nt(self):
        with self.assertRaises(MdFileNotPortable):
            resolve_md_file(POSIX_MD, self.CARRIER, os_name="nt")

    def test_foreign_path_error_names_the_machine_family(self):
        with self.assertRaises(MdFileNotPortable) as ctx:
            resolve_md_file(WINDOWS_MD, self.CARRIER, os_name="posix")
        self.assertIn(WINDOWS_MD, str(ctx.exception))
        self.assertIn("link", str(ctx.exception))


class ToRelativeMdFileTest(unittest.TestCase):
    """存储形态：绝对路径进来，posix 相对路径出去。

    这一层不落盘，所以在临时目录被 Security Center 搞坏的环境里照样能跑——
    它是 #169 存储契约的最终判据。
    """

    CARRIER = "/repo/app/roadmap.json"

    def test_same_dir_becomes_a_bare_filename(self):
        self.assertEqual(
            to_relative_md_file("/repo/app/ROADMAP.md", self.CARRIER), "ROADMAP.md"
        )

    def test_sibling_dir_becomes_a_relative_path(self):
        self.assertEqual(
            to_relative_md_file("/repo/docs/ROADMAP.md", self.CARRIER), "../docs/ROADMAP.md"
        )

    def test_deeper_nesting_becomes_a_relative_path(self):
        self.assertEqual(
            to_relative_md_file("/repo/app/md/ROADMAP.md", self.CARRIER), "md/ROADMAP.md"
        )

    def test_parent_dir_becomes_a_relative_path(self):
        self.assertEqual(
            to_relative_md_file("/repo/ROADMAP.md", self.CARRIER), "../ROADMAP.md"
        )

    def test_output_never_carries_windows_separators(self):
        """posix 分隔符：同一份 JSON 在 Windows 上也能被打开。"""
        self.assertNotIn("\\", to_relative_md_file("/repo/app/md/ROADMAP.md", self.CARRIER))


class MdPathErrorContractTest(unittest.TestCase):
    """E_MD_PATH 并入既有错误码表，不另起一套机制（#110 §不变式 2）。"""

    def test_joins_the_existing_code_table(self):
        self.assertIn("E_MD_PATH", ERROR_EXIT_CODES)
        self.assertEqual(ERROR_EXIT_CODES["E_MD_PATH"], 1)

    def test_is_a_roadmap_error_with_exit_code_1(self):
        self.assertEqual(MdFileNotPortable.code, "E_MD_PATH")
        self.assertEqual(MdFileNotPortable.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
