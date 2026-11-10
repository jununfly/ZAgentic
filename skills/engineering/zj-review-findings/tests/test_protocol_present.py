#!/usr/bin/env python3
"""zj-review-findings 协议结构钉死测试（不引入运行时依赖，只校验协议文本完整）。

评审发现 D-1：该技能是纯文档响应协议，此前无任何制品强制其 6 步协议与
mutation-test 边界要求。本测试把协议结构钉为可机检不变量：删步、删
mutation-test 要求、删机器检查边界，都会在此处失败。
"""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


class ProtocolPresenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SKILL_MD.read_text(encoding="utf-8").lower()

    def test_six_step_protocol_present(self):
        for step in range(1, 7):
            self.assertIn(f"## step {step}", self.text, f"Step {step} heading missing")

    def test_mutation_test_requirement_present(self):
        self.assertIn("mutation test", self.text)

    def test_machine_check_boundary_is_explicit(self):
        # Step 4：必须显式划出机器检查边界，而非静默接受偏差。
        self.assertIn("machine-check", self.text)
        self.assertIn("asymmetric cost", self.text)


if __name__ == "__main__":
    unittest.main()
