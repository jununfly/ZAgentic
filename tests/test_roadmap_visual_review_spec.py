"""Regression guards for the roadmap visual-review design pages.

These tests observe the design pages and the machine-readable SoT as *public
artifacts*. They do not scan the repository for style violations and do not emit
runtime diagnostics: the mechanical gate lives in
``scripts/roadmap_visual_review_spec.py`` and stays a single, testable unit.

Expectations below are independent literals, never recomputed from the code
under test, so a change to the spec's size or to the gate's leniency shows up
here instead of being absorbed silently.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "roadmap_visual_review_spec.py"
SPEC = ROOT / "docs" / "designs" / "zj-roadmap-visual-review.spec.json"
TECH_MD = ROOT / "docs" / "designs" / "zj-roadmap-visual-review-technical.md"
PRODUCT_MD = ROOT / "docs" / "designs" / "zj-roadmap-visual-review-product.md"
DOC_MAP = ROOT / "docs" / "README.md"

EXPECTED_SCENES = 4
EXPECTED_PROJECTS = 6
EXPECTED_DIFFERENCE_ENTRIES = 24
EXPECTED_UNKNOWN_ENTRIES = 5
EXPECTED_CAPABILITIES = 10
EXPECTED_VIEW_CONTRACTS = 8
EXPECTED_INVARIANTS = 14
EXPECTED_SLICES = 5
EXPECTED_REJECTED = 14
EXPECTED_LOAD_CONDITIONS = 4
EXPECTED_DOI_TERMS = 6
EXPECTED_DEBT_KINDS = 4
EXPECTED_READING_BUDGET = 40
EXPECTED_PRESENTATION_REGIONS = 4
EXPECTED_CARD_LOD_LEVELS = 3


def _load_module():
    module_spec = importlib.util.spec_from_file_location("roadmap_visual_review_spec", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


mod = _load_module()


def load_spec() -> dict:
    with SPEC.open(encoding="utf-8") as handle:
        return json.load(handle)


def gate_for(spec: dict):
    gate = mod.Gate()
    mod.validate(spec, gate)
    return gate


class DerivedPageTest(unittest.TestCase):
    """The technical design is a byte-for-byte projection, never hand-edited."""

    def test_technical_page_is_byte_identical_to_the_spec_projection(self):
        self.assertEqual(TECH_MD.read_text(encoding="utf-8"), mod.render(load_spec()))

    def test_rerender_is_deterministic(self):
        spec = load_spec()
        self.assertEqual(mod.render(spec), mod.render(spec))

    def test_derived_page_carries_no_clock_or_absolute_path(self):
        text = TECH_MD.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/home/", "Generated at", "generated at"):
            self.assertNotIn(forbidden, text)

    def test_derived_page_declares_its_single_source(self):
        text = TECH_MD.read_text(encoding="utf-8")
        self.assertIn(mod.GENERATED_MARKER, text)
        self.assertIn("authority-id: design.roadmap-visual-review-technical", text)

    def test_product_page_is_hand_authored_and_has_no_generated_marker(self):
        text = PRODUCT_MD.read_text(encoding="utf-8")
        self.assertNotIn(mod.GENERATED_MARKER, text)
        self.assertIn("authority-id: design.roadmap-visual-review-product", text)


class MechanicalGateTest(unittest.TestCase):
    """A gate that cannot go red is not a gate."""

    def test_valid_spec_passes_with_zero_errors(self):
        self.assertEqual(gate_for(load_spec()).errors, [])

    def test_gate_rejects_each_class_of_defect(self):
        def drop_difference_entry(spec):
            spec["difference-entries"].pop()

        def break_scene_externality(spec):
            spec["scene-set"]["derived-from-graphs"] = True

        def prescribe_implementation_in_scene(spec):
            spec["scene-set"]["scenes"][0]["nodes"] = ["n1"]

        def strip_unknown_verification_plan(spec):
            for de in spec["difference-entries"]:
                if de["verdict"] == "unknown":
                    de["verification-plan"] = ""
                    break

        def promote_unknown_to_unsupported(spec):
            for de in spec["difference-entries"]:
                if de["verdict"] == "unknown":
                    de["verdict"] = "unsupported"
                    break

        def strip_native_evidence(spec):
            for de in spec["difference-entries"]:
                if de["verdict"] == "native":
                    de["evidence-refs"] = []
                    break

        def desync_context_verdicts(spec):
            spec["difference-entries"][0]["context-verdicts"] = []

        def claim_evidence_without_refs(spec):
            spec["difference-entries"][0]["sources"] = ["human-ruling"]
            spec["difference-entries"][0]["evidence-refs"] = []

        def drop_a_source_pin(spec):
            spec["sources"][0].pop("pin")

        def orphan_a_capability_scene(spec):
            spec["capabilities"][0]["scene-refs"] = ["SC::99"]

        def remove_ir_producer(spec):
            spec["view-contracts"][0]["producer"] = ""

        def drop_invariant_guard(spec):
            spec["invariants"][0].pop("guard")

        def add_second_ir(spec):
            spec["view-contracts"][1]["kind"] = "intermediate-representation"

        def use_load_condition_as_scene(spec):
            spec["difference-entries"][0]["scene"] = "LC::01"

        def erase_prior_design_gap(spec):
            spec["problem-refinement"]["gap-in-prior-design"] = ""

        def break_scene_set_externality_note(spec):
            spec["problem-refinement"]["not-a-new-scene-set"] = "可以按需扩充场景"

        def make_doi_nondeterministic(spec):
            spec["information-selection"]["doi-function"]["deterministic"] = False

        def break_doi_weight_sum(spec):
            spec["information-selection"]["doi-function"]["terms"][0]["weight"] = 0.9

        def invert_thresholds(spec):
            spec["information-selection"]["doi-function"]["thresholds"]["overview"] = 0.1

        def allow_silent_drop(spec):
            spec["information-selection"]["reading-budget"]["silent-drop"] = True

        def drop_a_debt_kind(spec):
            spec["debt-schema"]["kinds"] = spec["debt-schema"]["kinds"][:3]

        def auto_promote_debt(spec):
            spec["debt-schema"]["promotion-rule"] = "债务自动变成 WorkItem"

        def leak_receipt_into_carrier(spec):
            spec["information-selection"]["reentry"]["receipt-storage"] = "写进 carrier"

        def drop_delta_kind(spec):
            spec["information-selection"]["reentry"]["delta-kinds"].pop()

        def remove_fail_closed(spec):
            spec["information-selection"]["reentry"]["no-hidden-state"] = "猜测上次读到哪"

        def erase_presentation_evolution(spec):
            spec["presentation"]["replaces"] = ""

        def flatten_full_dag(spec):
            spec["presentation"]["dag-encoding"]["scope"] = "铺全量 DAG"

        def use_random_layout(spec):
            spec["presentation"]["dag-encoding"]["layout"] = "force-directed 随机布局"

        def drop_text_equivalent(spec):
            spec["presentation"]["dag-encoding"]["text-equivalent"] = "无"

        def make_card_wall(spec):
            spec["presentation"]["card-lod"]["budget"] = "所有条目都渲染成卡片"

        def put_debt_on_dag(spec):
            spec["presentation"]["card-lod"]["debt"] = "债务作为 DAG 节点"

        def rely_on_colour_only(spec):
            spec["presentation"]["doi-encoding"]["no-color-only"] = False

        def drop_a_region(spec):
            spec["presentation"]["three-regions"].pop()

        defects = [
            ("cardinality", drop_difference_entry),
            ("scene externality", break_scene_externality),
            ("scene prescribes nodes", prescribe_implementation_in_scene),
            ("unknown without plan", strip_unknown_verification_plan),
            ("unknown -> unsupported", promote_unknown_to_unsupported),
            ("native without evidence", strip_native_evidence),
            ("context verdict desync", desync_context_verdicts),
            ("ruling written as evidence", claim_evidence_without_refs),
            ("source without pin", drop_a_source_pin),
            ("unresolved scene ref", orphan_a_capability_scene),
            ("missing IR producer", remove_ir_producer),
            ("invariant without guard", drop_invariant_guard),
            ("two IR producers", add_second_ir),
            ("load condition used as scene", use_load_condition_as_scene),
            ("prior design gap erased", erase_prior_design_gap),
            ("scene set expansion allowed", break_scene_set_externality_note),
            ("DOI made nondeterministic", make_doi_nondeterministic),
            ("DOI weights not normalized", break_doi_weight_sum),
            ("DOI thresholds inverted", invert_thresholds),
            ("silent budget truncation", allow_silent_drop),
            ("debt kind removed", drop_a_debt_kind),
            ("debt auto-promotion", auto_promote_debt),
            ("receipt leaks into carrier", leak_receipt_into_carrier),
            ("delta kind removed", drop_delta_kind),
            ("re-entry no longer fails closed", remove_fail_closed),
            ("presentation evolution erased", erase_presentation_evolution),
            ("full DAG instead of local", flatten_full_dag),
            ("random DAG layout", use_random_layout),
            ("text equivalent removed", drop_text_equivalent),
            ("unbounded card wall", make_card_wall),
            ("debt placed on the DAG", put_debt_on_dag),
            ("colour-only encoding", rely_on_colour_only),
            ("presentation region removed", drop_a_region),
        ]
        for name, mutate in defects:
            with self.subTest(defect=name):
                spec = load_spec()
                mutate(spec)
                self.assertTrue(gate_for(spec).errors, f"gate stayed green for defect: {name}")


class EvidenceDisciplineTest(unittest.TestCase):
    """Borrowed from zj-graphical-cross-comparison; no report is signed here."""

    def test_difference_entry_cardinality_is_an_independent_literal(self):
        spec = load_spec()
        self.assertEqual(EXPECTED_DIFFERENCE_ENTRIES, EXPECTED_SCENES * EXPECTED_PROJECTS)
        self.assertEqual(len(spec["difference-entries"]), EXPECTED_DIFFERENCE_ENTRIES)
        self.assertEqual(len(spec["scene-set"]["scenes"]), EXPECTED_SCENES)
        self.assertEqual(len(spec["projects"]), EXPECTED_PROJECTS)

    def test_unknown_is_an_evidence_gap_not_a_negation(self):
        spec = load_spec()
        unknowns = [d for d in spec["difference-entries"] if d["verdict"] == "unknown"]
        self.assertEqual(len(unknowns), EXPECTED_UNKNOWN_ENTRIES)
        for de in unknowns:
            self.assertTrue(de["verification-plan"])
            self.assertEqual(de["evidence-refs"], [])
        unsupported = [d for d in spec["difference-entries"] if d["verdict"] == "unsupported"]
        self.assertEqual(unsupported, [])

    def test_no_signed_report_while_scene_pin_is_pending(self):
        spec = load_spec()
        self.assertIs(spec["scene-set"]["human-independent-pin"], False)
        self.assertIn("signed-cross-comparison-report", spec["method-contract"]["not-applied"])
        self.assertIn("CHK-12", spec["method-contract"]["imported-conditions"])
        self.assertIn("unknown", spec["method-contract"]["no-silent-substitution"])

    def test_summary_metrics_are_display_only(self):
        result = mod.metrics(load_spec())
        self.assertIs(result["not_for_conclusion"], True)
        self.assertEqual(result["usage"], "display-only")
        self.assertEqual(result["difference_entries"], EXPECTED_DIFFERENCE_ENTRIES)

    def test_every_capability_has_an_observable_acceptance_criterion(self):
        for cap in load_spec()["capabilities"]:
            with self.subTest(capability=cap["id"]):
                self.assertTrue(cap["acceptance"])
                self.assertTrue(cap["scene-refs"])
                self.assertTrue(cap["evidence-refs"])


class InformationSelectionTest(unittest.TestCase):
    """The second-round refinement: large context, re-entry, coupling, debts."""

    def test_refinement_is_a_load_condition_not_an_expanded_scene_set(self):
        spec = load_spec()
        self.assertEqual(len(spec["scene-set"]["scenes"]), EXPECTED_SCENES)
        self.assertEqual(len(spec["difference-entries"]), EXPECTED_DIFFERENCE_ENTRIES)
        self.assertEqual(len(spec["load-conditions"]), EXPECTED_LOAD_CONDITIONS)
        self.assertTrue(spec["problem-refinement"]["gap-in-prior-design"])
        self.assertIn("CHK-04", spec["problem-refinement"]["not-a-new-scene-set"])

    def test_doi_is_deterministic_normalized_and_single_knob(self):
        doi = load_spec()["information-selection"]["doi-function"]
        self.assertIs(doi["deterministic"], True)
        self.assertIn("非 LLM", doi["owner"])
        self.assertEqual(len(doi["terms"]), EXPECTED_DOI_TERMS)
        self.assertAlmostEqual(sum(t["weight"] for t in doi["terms"]), 1.0)
        thresholds = doi["thresholds"]
        self.assertGreater(thresholds["overview"], thresholds["neighborhood"])
        self.assertGreater(thresholds["neighborhood"], thresholds["expand"])
        self.assertIn("同一", doi["single-knob"])

    def test_reading_budget_never_drops_items_silently(self):
        budget = load_spec()["information-selection"]["reading-budget"]
        self.assertEqual(budget["max"], EXPECTED_READING_BUDGET)
        self.assertIs(budget["silent-drop"], False)
        self.assertIn("显式", budget["overflow-report"])

    def test_debts_are_first_class_but_never_auto_promoted(self):
        debt = load_spec()["debt-schema"]
        self.assertEqual(len(debt["kinds"]), EXPECTED_DEBT_KINDS)
        self.assertEqual({k["name"] for k in debt["kinds"]}, {"gap", "todo", "risk", "sweep"})
        self.assertIn("不自动", debt["promotion-rule"])
        self.assertTrue(any("ready" in x for x in debt["not-in"]))
        self.assertIn("discovered-revision", debt["required-fields"])

    def test_reentry_receipt_never_enters_the_carrier(self):
        reentry = load_spec()["information-selection"]["reentry"]
        self.assertIn("carrier", reentry["receipt-storage"])
        self.assertIn("gitignored", reentry["receipt-storage"])
        self.assertEqual(set(reentry["delta-kinds"]),
                         {"added", "changed", "removed", "stable-folded"})
        self.assertIn("content hash", reentry["item-identity"])
        self.assertIn("baseline=None", reentry["carrier-identity"])
        self.assertIn("fail-closed", reentry["no-hidden-state"])

    def test_spec_size_literals_are_independent(self):
        spec = load_spec()
        self.assertEqual(len(spec["capabilities"]), EXPECTED_CAPABILITIES)
        self.assertEqual(len(spec["view-contracts"]), EXPECTED_VIEW_CONTRACTS)
        self.assertEqual(len(spec["invariants"]), EXPECTED_INVARIANTS)
        self.assertEqual(len(spec["slices"]), EXPECTED_SLICES)
        self.assertEqual(len(spec["rejected-defaults"]), EXPECTED_REJECTED)
        self.assertEqual(spec["slices"][0]["id"], "S0")
        self.assertEqual(spec["slices"][1]["depends-on"], ["S0"])

    def test_metrics_expose_load_shape_but_stay_display_only(self):
        result = mod.metrics(load_spec())
        self.assertIs(result["not_for_conclusion"], True)
        self.assertEqual(result["usage"], "display-only")
        self.assertEqual(result["doi_terms"], EXPECTED_DOI_TERMS)
        self.assertEqual(result["debt_kinds"], EXPECTED_DEBT_KINDS)
        self.assertEqual(result["load_conditions"], EXPECTED_LOAD_CONDITIONS)
        self.assertEqual(result["reading_budget_max"], EXPECTED_READING_BUDGET)


class PresentationTest(unittest.TestCase):
    """Cards + DAG are a spatial encoding of the DOI selection, not a reskin."""

    def test_the_replaced_demo_is_recorded_not_silently_dropped(self):
        pres = load_spec()["presentation"]
        self.assertIn("采纳", pres["verdict"])
        self.assertIn("换皮", pres["verdict"])
        self.assertIn("C::05", pres["replaces"])

    def test_dag_is_local_deterministic_and_has_a_text_equivalent(self):
        dag = load_spec()["presentation"]["dag-encoding"]
        self.assertIn("DOI>=theta", dag["scope"])
        self.assertIn("确定性", dag["layout"])
        self.assertIn("禁止", dag["layout"])
        self.assertIn("Mermaid", dag["text-equivalent"])
        self.assertGreaterEqual(len(dag["edge-encoding"]), 3)

    def test_cards_are_budgeted_lod_layered_and_debts_stay_off_the_graph(self):
        card = load_spec()["presentation"]["card-lod"]
        self.assertEqual(len(card["levels"]), EXPECTED_CARD_LOD_LEVELS)
        self.assertIn("预算", card["budget"])
        self.assertIn("卡片墙", card["budget"])
        self.assertIn("卡片", card["debt"])

    def test_visual_encoding_never_relies_on_colour_alone(self):
        encoding = load_spec()["presentation"]["doi-encoding"]
        self.assertIs(encoding["no-color-only"], True)
        self.assertGreaterEqual(len(encoding["channels"]), 2)
        self.assertTrue(encoding["dual-coding"])

    def test_presentation_has_four_regions_and_bound_constraints(self):
        pres = load_spec()["presentation"]
        self.assertEqual(len(pres["three-regions"]), EXPECTED_PRESENTATION_REGIONS)
        self.assertGreaterEqual(len(pres["constraints"]), 4)
        self.assertEqual(len(pres["addressed-by"]), 3)

    def test_size_literals_include_the_new_surfaces(self):
        spec = load_spec()
        self.assertEqual(len(spec["capabilities"]), EXPECTED_CAPABILITIES)
        self.assertEqual(len(spec["view-contracts"]), EXPECTED_VIEW_CONTRACTS)
        self.assertEqual(len(spec["invariants"]), EXPECTED_INVARIANTS)
        self.assertEqual(len(spec["rejected-defaults"]), EXPECTED_REJECTED)
        self.assertIn("局部 DAG", spec["slices"][2]["statement"])

    def test_metrics_expose_presentation_shape_but_stay_display_only(self):
        result = mod.metrics(load_spec())
        self.assertIs(result["not_for_conclusion"], True)
        self.assertEqual(result["presentation_regions"], EXPECTED_PRESENTATION_REGIONS)
        self.assertEqual(result["card_lod_levels"], EXPECTED_CARD_LOD_LEVELS)


class DocumentationMapTest(unittest.TestCase):
    """Both design pages are bound to exactly one authority-id in the doc map."""

    def test_both_pages_are_registered_as_design_authorities(self):
        text = DOC_MAP.read_text(encoding="utf-8")
        for authority_id in ("design.roadmap-visual-review-product",
                             "design.roadmap-visual-review-technical"):
            self.assertIn(authority_id, text)

    def test_soT_filename_appears_in_the_technical_page(self):
        self.assertIn("zj-roadmap-visual-review.spec.json", TECH_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
