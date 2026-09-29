#!/usr/bin/env python3
"""§8 digest 注入语义兼容 PoC 回归守卫。

PoC 目标（见 docs/designs/zj-discuss/design.md §8 / §7）：验证在子文档或 MASTER 中
加入一个 digest 区块后，结构性闸门（check_subdoc）与度量计算机（metrics）把它当作
**惰性**内容处理——

  - 不计为独立视角（viewpoint_count 不变）；
  - 不污染 raw / solution 字符量（digest 不是视角区块，也不属于 解决思路）；
  - 不触发闸门任何违规；
  - 不破坏 conclusion 状态协议解析。

尖锐用例：digest 围栏内**故意嵌一段 `### 视角：B` 回声文本**，模拟结构性 digest
回显视角。在 split_sections 围栏感知修复前，这段会被误判为真实视角（RED）；
修复后必须惰性（GREEN）。这同时锁住一个普遍解析 bug：子文档里任何代码围栏内的
`#` 标题都不应被当成分节。

期望值一律为**独立手算常量**，不调用被测算法的同义逻辑（防假绿）。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import check_subdoc  # noqa: E402
import metrics  # noqa: E402

# --- 基线子文档（无 digest） ---
BASE_SUBDOC = """# 子问题：示例

## 上下文

- **声明必需角色集：** B,C

## 待讨论问题（scope 草案）

- Q1：问题一
- Q2：问题二

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

**观点 1** — 排期
- 发现：原文 L10 要求排期可行
- 影响：否则延期
- 建议：显式关键路径

**观点 2** — 风险
- 发现：原文 L20 列出主风险
- 影响：无回退
- 建议：补回退方案

**观点 3** — 验收
- 发现：原文 L30 验收口径缺失
- 影响：做到算完模糊
- 建议：量化验收

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1** — 用户价值
- 发现：原文 L9 面向外部评估
- 影响：内部场景空转
- 建议：改写为自证价值

**观点 2** — 生态竞品
- 发现：原文 L13 无真实市场
- 影响：竞品锚点空
- 建议：solo 场景降 N

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`
主力AI 的整合文字，不应被计入独立视角。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- |
| 1 | B | 采纳 | 否 | — |

## conclusion（含沉淀指令）

- **状态协议：** DONE（已回填 MASTER.md 索引）
- 子问题结论：定了。
- 解法：方案 X。
"""

# --- 同种子文档，但末尾追加 voice-only digest（围栏包裹） ---
DIGEST_FENCED_SUBDOC = BASE_SUBDOC + """

## AI 上下文 digest（可选，voice-only）

把本讨论的 zj voice-only 上下文贴进下方代码块（零安装注入立场 / 语气，
**不**自动注入讨论状态 digest，见 design.md §8）。围栏内的任何 `#` 标题都不会被
结构性闸门 / 度量计算机误判：

```text
<在此粘贴 voice-only digest：zj-discuss 的 ethos/voice 简述>
### 视角：B（回声示例 — 这一段绝不可被当作真实独立视角）
这是一段被引用的回声内容，仅用于演示 digest 内含标题也不应被误判为视角。
```
"""

# --- MASTER（含 digest），用于讨论级度量 ---
MASTER_WITH_DIGEST = """# 复杂问题示例

## 核心问题

- **问题陈述：** 示例问题
- **成功判据：** 可验证结果

## 解决思路（整合叙事）

整合后的解决思路文字，这是应当被度量的 solution 内容。

## 文档索引

| 子文档 | 独立子问题 | 状态 | 解法摘要 |
| --- | --- | --- | --- |
| [sub-01.md](./sub-01.md) | 子问题 | ✅ 已结论 | 摘要 |

## 跨子文档约束

- 约束 1

## 本文件夹的性质与处置契约

本文件夹是过程性质权威依据。

## 复盘度量（可选，删除前填）

```json
{"placeholder": true}
```

## AI 上下文 digest（可选，voice-only）

```text
voice-only digest 内容，不应计入 solution_volume_chars
```
"""


class DigestPocTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, text):
        p = Path(self.tmp.name) / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_subdoc_digest_inert_in_metrics(self):
        """含 digest 的子文档，度量须与基线逐字段一致（digest 完全惰性）。"""
        base = self._write("base.md", BASE_SUBDOC)
        dig = self._write("dig.md", DIGEST_FENCED_SUBDOC)
        m_base = metrics.compute_subdoc_metrics(base)
        m_dig = metrics.compute_subdoc_metrics(dig)

        self.assertEqual(m_dig["viewpoint_count"], m_base["viewpoint_count"],
                         "digest 不应改变视角计数")
        self.assertEqual(m_dig["roles_used"], m_base["roles_used"])
        self.assertEqual(m_dig["raw_volume_chars"], m_base["raw_volume_chars"],
                         "digest 不应计入 raw 字符量")
        self.assertEqual(m_dig["solution_volume_chars"],
                         m_base["solution_volume_chars"],
                         "digest 不应改变 solution 字符量")
        self.assertEqual(m_dig["compression_ratio"], m_base["compression_ratio"])
        # 独立手算基线期望值（不依赖算法）
        self.assertEqual(m_base["viewpoint_count"], 2)
        self.assertEqual(m_base["roles_used"], ["B", "C"])
        self.assertEqual(m_base["open_questions_closed"], 1)

    def test_subdoc_digest_passes_gate(self):
        """含 digest 的子文档必须通过结构性闸门（无违规）。"""
        dig = self._write("dig.md", DIGEST_FENCED_SUBDOC)
        violations = check_subdoc.check(dig.read_text(encoding="utf-8"))
        self.assertEqual(violations, [],
                         "digest 区块不应触发任何闸门违规：{}".format(violations))

    def test_digest_fence_inner_heading_not_a_viewpoint(self):
        """digest 围栏内的 `### 视角：B` 回声，绝不能算作独立视角（PoC 核心修复点）。"""
        dig = self._write("dig.md", DIGEST_FENCED_SUBDOC)
        m = metrics.compute_subdoc_metrics(dig)
        base = self._write("base.md", BASE_SUBDOC)
        m_base = metrics.compute_subdoc_metrics(base)
        # 若 split_sections 不认围栏，围栏内的 `### 视角：B` 会被当视角 → 计数变 3
        self.assertEqual(m["viewpoint_count"], 2,
                         "围栏内回声标题被误判为视角（split_sections 未围栏感知）")
        self.assertEqual(m["viewpoint_count"], m_base["viewpoint_count"])

    def test_master_digest_not_in_solution_volume(self):
        """MASTER 含 digest 时，solution_volume_chars 仅计 解决思路，不含 digest。"""
        disc = Path(self.tmp.name) / "disc"
        disc.mkdir()
        (disc / "MASTER.md").write_text(MASTER_WITH_DIGEST, encoding="utf-8")
        (disc / "sub-01.md").write_text(BASE_SUBDOC, encoding="utf-8")

        rec = metrics.compute_discussion_metrics(disc)
        # 手算 解决思路 段纯文本长度（不含末尾 digest）
        expected_solution = len("整合后的解决思路文字，这是应当被度量的 solution 内容。")
        self.assertEqual(rec["solution_volume_chars"], expected_solution,
                         "MASTER digest 污染了 solution 字符量")
        # digest 在 master 末尾，不应影响 raw（raw 只来自子文档视角）
        self.assertEqual(rec["raw_volume_chars"],
                         metrics.compute_subdoc_metrics(disc / "sub-01.md")["raw_volume_chars"])

    def test_cli_check_passes_with_digest(self):
        """CLI 入口：含 digest 的子文档退出码须为 0。"""
        dig = self._write("dig.md", DIGEST_FENCED_SUBDOC)
        result = subprocess.run(
            [sys.executable, str(SKILL_SCRIPTS / "check_subdoc.py"), str(dig)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         "CLI 闸门对含 digest 子文档应退出 0：{}".format(result.stderr))


if __name__ == "__main__":
    unittest.main()
