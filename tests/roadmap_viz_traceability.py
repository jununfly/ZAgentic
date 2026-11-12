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
    "INV::06": (
        T + "test_process_authority_boundary.ProcessAuthorityBoundaryContract."
            "test_durable_doc_citing_process_state_is_rejected",
    ),
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
    "INV::13": (
        V + "test_review_contracts.DagLayoutDeterminismContract."
            "test_two_renders_are_byte_identical",
    ),
    "INV::14": (
        T + "test_roadmap_visual_review_spec.PresentationTest."
            "test_visual_encoding_never_relies_on_colour_alone",
    ),
    # ---- capabilities -----------------------------------------------------
    "C::01": (
        V + "test_review_contracts.AncestorChainContract."
            "test_tree_ancestors_are_always_visible",
    ),
    "C::02": (
        V + "test_s3_s4.TestS3Dependency.test_blocked_by_matches_s1_ir_pdepth",
    ),
    "C::03": (
        V + "test_s3_s4.TestS4Context.test_anchor_roundtrip_deterministic",
    ),
    "C::04": (
        V + "test_s3_s4.TestS4Context.test_context_pack_is_side_loaded_not_embedded",
    ),
    "C::05": (
        V + "test_review_contracts.ViewKindRoutingContract."
            "test_spec_view_contracts_match_the_independent_route_table",
    ),
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
    "C::10": (
        V + "test_review_contracts.DoiOrderingContract."
            "test_dag_and_cards_share_one_doi_ordering",
    ),
}

# Explicitly accepted, *mechanically unguarded* claims. Empty as of S1c:
# all 24 spec ids now have an executable guard. MAX_UNGOVERNED = 0 means any
# future `None` in TRACEABILITY is a hard failure, so a dropped guard can
# never be laundered into a "recorded gap" without an explicit decision.
MAX_UNGOVERNED = 0

ACCEPTED_UNGOVERNED: dict[str, str] = {}
