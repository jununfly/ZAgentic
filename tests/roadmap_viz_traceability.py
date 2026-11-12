#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent spec-id -> executable-test map for the visual-review contract.

This is a hand-maintained literal, never derived from the spec or from test
discovery. `None` means "no mechanical guard exists yet"; every such id must
be justified in ACCEPTED_UNGOVERNED and is kept visible on purpose: silently
inventing a guard for an untested claim would be a false green.

Adding a new invariant/capability to spec.json without updating this map is a
red build. Adding a guard name that does not resolve to a real test is also a
red build (see tests/test_roadmap_visual_review_traceability.py).
"""
from __future__ import annotations

V = "viz.tests."
T = "tests."

TRACEABILITY: dict[str, tuple[str, ...] | None] = {
    # ---- invariants -------------------------------------------------------
    "INV::01": (
        V + "test_s3_s4.TestS4Context.test_main_view_bytes_stable_when_context_grows",
    ),
    "INV::02": (
        V + "test_s1.TwoCarrierByteIdentity.test_same_anchor_same_bytes_across_carriers",
    ),
    "INV::03": (
        V + "test_review_contracts.SelectionParityContract."
            "test_html_runtime_select_matches_python_doi_select",
    ),
    "INV::04": (
        V + "test_viz.TestS0ReadonlyContract.test_no_carrier_mutation",
    ),
    "INV::05": (
        V + "test_s1.TwoCarrierByteIdentity.test_authority_envelope_in_every_public_view",
    ),
    "INV::06": None,
    "INV::07": (
        T + "test_skill_install_smoke.InstalledCopyExecution."
            "test_quick_start_init_runs_with_only_the_declared_basis",
    ),
    "INV::08": (
        V + "test_review_contracts.ViewDeterminismContract."
            "test_same_carrier_anchor_revision_renders_identical_public_views",
    ),
    "INV::09": (
        V + "test_review_contracts.BudgetOverflowContract."
            "test_mandatory_overflow_is_reported_not_silent",
    ),
    "INV::10": (
        V + "test_viz.TestS0Selection.test_determinism",
    ),
    "INV::11": (
        V + "test_s1.DeltaReentry.test_receipt_never_enters_carrier_or_view_ir",
    ),
    "INV::12": (
        T + "test_roadmap_visual_review_spec.InformationSelectionTest."
            "test_debts_are_first_class_but_never_auto_promoted",
    ),
    "INV::13": None,
    "INV::14": (
        T + "test_roadmap_visual_review_spec.PresentationTest."
            "test_visual_encoding_never_relies_on_colour_alone",
    ),
    # ---- capabilities -----------------------------------------------------
    "C::01": None,
    "C::02": (
        V + "test_s3_s4.TestS3Dependency.test_blocked_by_matches_s1_ir_pdepth",
    ),
    "C::03": (
        V + "test_s3_s4.TestS4Context.test_anchor_roundtrip_deterministic",
    ),
    "C::04": (
        V + "test_s3_s4.TestS4Context.test_context_pack_is_side_loaded_not_embedded",
    ),
    "C::05": None,
    "C::06": (
        V + "test_s3_s4.TestS4Context.test_stale_when_revision_mismatch",
    ),
    "C::07": (
        V + "test_review_contracts.SelectionParityContract."
            "test_html_runtime_select_matches_python_doi_select",
    ),
    "C::08": (
        V + "test_viz.TestS0Debt.test_explicit_debt_wins",
    ),
    "C::09": (
        V + "test_s1.DeltaReentry.test_added_changed_removed_and_stable_folded",
        V + "test_s1b.CrossDeviceMerge."
            "test_same_context_receipts_merge_into_a_usable_baseline",
    ),
    "C::10": None,
}

# Explicitly accepted, *mechanically unguarded* claims. These are not marked
# as covered: each entry records what is missing. The count is capped so the
# set cannot grow silently when a future change drops a guard.
MAX_UNGOVERNED = 5

ACCEPTED_UNGOVERNED: dict[str, str] = {
    "INV::06": (
        "process-state 权威边界由 authority-check 实施，但现有守卫只断言命令名与 "
        "SKILL.md 纪律文本，缺「长期文档引用过程产物」的端到端拒绝用例；属真实缺口。"
    ),
    "INV::13": (
        "只有 Mermaid 文本等价物存在性与 spec 文本断言，缺 DAG 布局确定性的两次生成"
        "字节比较，以及禁用 force-directed / 随机布局的静态检查。"
    ),
    "C::01": (
        "缺「祖先链必现、非焦点兄弟折叠为分区计数」的运行时断言；现有 S2 投影测试"
        "只校 cards 键集合与 mermaid 文本存在性，不校验概览结构不变量。"
    ),
    "C::05": (
        "缺 view-kind 到输出形态的一一映射枚举断言；现有断言只读 spec 的 "
        "presentation 文本字段，没有对实际投影产物的路由做机械钉住。"
    ),
    "C::10": (
        "缺同一 θ 下局部 DAG 与信息卡片共用 DOI 排序的运行时断言；"
        "cards_match_shown 只校键集合，不校空间编码与排序同源。"
    ),
}
