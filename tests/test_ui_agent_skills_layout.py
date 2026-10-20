"""Guards for 1-6-1: the ten `ui/` skill skeletons and every index that must list them.

Why these tests exist: "the skill was created" is not a fact anything can check,
and "it is discoverable" degrades silently the moment a README line or the bucket
allowlist drifts. So this file asserts the things the roadmap node claims:

1. ten directories exist, one per stage, and recursion actually returns them;
2. every SKILL.md carries the frozen 16-field capability manifest, with exactly
   the keys 1-3-1 declared — no extras, no missing, no renamed;
3. the stage/precedence/fixture declarations stay mutually consistent and each
   fixture id resolves to the owner 1-3-1 §4 assigned;
4. both README indexes, zj-guide, AGENTS.md, ZJ-CONTEXT.md and the generated
   install inventory listed them, so the skeleton is not a hidden directory.

These are static checks. They do not claim any skill executes: the skeletons
declare `contract-skeleton`, and a test below fails if that marker disappears
without the implementation landing.
"""

import importlib.util
import json
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
UI_ROOT = REPO / "skills/ui"
DOC = REPO / "docs/plans/ui-agent-skills-skill-capability-manifest.md"
TEMPLATE = REPO / "docs/plans/ui-agent-skills-skill-md-template.md"

# Stage order is the chain order; the index of an entry is its stage number - 1.
EXPECTED_SKILLS = [
    "zj-ui-brief",
    "zj-ui-discover",
    "zj-ui-direction",
    "zj-ui-design-system",
    "zj-ui-flow",
    "zj-ui-prototype",
    "zj-ui-visual-review",
    "zj-ui-break",
    "zj-ui-verify",
    "zj-ui-handoff",
]

MANIFEST_KEYS = (
    "skill_id",
    "manifest_version",
    "stage",
    "owner_scope",
    "writes",
    "reads",
    "input",
    "output",
    "forbidden",
    "dependencies",
    "required_capabilities",
    "stop_conditions",
    "owner",
    "precedence",
    "failure_fixtures",
    "human_gate",
)

OWNER_SCOPES = {"write", "read", "emit"}
HUMAN_GATES = {"required", "conditional", "none"}
STOP_ACTIONS = {"STOP", "WAIT_HUMAN", "RETRY_ONCE", "ROLLBACK", "ESCALATE"}


def read(path):
    return path.read_text(encoding="utf-8")


def manifest_of(skill):
    """Return the parsed capability manifest declared in a skill's SKILL.md."""
    text = read(UI_ROOT / skill / "SKILL.md")
    match = re.search(
        r"^## Capability Manifest\s*\n+```json\n(.*?)\n```", text, re.MULTILINE | re.DOTALL
    )
    if match is None:
        raise AssertionError(f"{skill}: no ```json block under '## Capability Manifest'")
    return json.loads(match.group(1))


def frontmatter_of(skill):
    text = read(UI_ROOT / skill / "SKILL.md")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"{skill}: missing frontmatter")
    return match.group(1)


def fixture_table():
    """Parse 1-3-1 §4: skill -> (fixture ids, responsible owner)."""
    rows = {}
    for line in read(DOC).splitlines():
        if not line.startswith("| `zj-ui-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        skill = cells[0].strip("`")
        fixture_ids = re.findall(r"FF-[A-Z]+-\d\d", "|".join(cells))
        rows[skill] = (fixture_ids, cells[-1])
    return rows


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, REPO / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DirectoryLayout(unittest.TestCase):
    def test_exactly_the_ten_stage_directories_exist(self):
        found = sorted(path.name for path in UI_ROOT.iterdir() if path.is_dir())
        self.assertEqual(found, sorted(EXPECTED_SKILLS))

    def test_every_skill_has_a_skill_md_and_no_nested_skill(self):
        for skill in EXPECTED_SKILLS:
            self.assertTrue((UI_ROOT / skill / "SKILL.md").is_file(), skill)
        nested = [path for path in UI_ROOT.rglob("SKILL.md")]
        self.assertEqual(len(nested), len(EXPECTED_SKILLS))

    def test_recursion_discovers_all_ten(self):
        validator = load_module("zj_layout_validator", "scripts/validate-zagentic-plugin.py")
        self.assertIn("ui", validator.PUBLIC_BUCKETS)
        errors = []
        manifests = validator.discover_skill_manifests(REPO, errors)
        self.assertEqual(errors, [])
        discovered = {path.parent.name for path in manifests if path.parent.parent == UI_ROOT}
        self.assertEqual(discovered, set(EXPECTED_SKILLS))


class ManifestContract(unittest.TestCase):
    def test_each_manifest_has_exactly_the_sixteen_keys(self):
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                self.assertEqual(tuple(manifest_of(skill)), MANIFEST_KEYS)

    def test_skill_id_matches_directory_and_frontmatter(self):
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                self.assertEqual(manifest_of(skill)["skill_id"], skill)
                self.assertIn(f"name: {skill}\n", frontmatter_of(skill) + "\n")

    def test_stage_and_precedence_form_one_chain(self):
        stages, precedences = [], []
        for position, skill in enumerate(EXPECTED_SKILLS, start=1):
            manifest = manifest_of(skill)
            stages.append(manifest["stage"])
            precedences.append(manifest["precedence"])
            self.assertEqual(manifest["stage"], f"S{position}", skill)
            self.assertEqual(manifest["precedence"], position * 10, skill)
        self.assertEqual(len(set(stages)), len(stages))
        self.assertEqual(len(set(precedences)), len(precedences))

    def test_owner_scope_matches_the_write_contract(self):
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                manifest = manifest_of(skill)
                self.assertIn(manifest["owner_scope"], OWNER_SCOPES)
                self.assertTrue(manifest["writes"], f"{skill}: writes must not be empty")
                self.assertFalse(
                    set(manifest["writes"]) & set(manifest["reads"]),
                    f"{skill}: reads must not restate its own writes",
                )
                self.assertTrue(manifest["forbidden"], f"{skill}: forbidden must not be empty")
                self.assertTrue(manifest["owner"].strip())
                self.assertIn(manifest["human_gate"], HUMAN_GATES)
                self.assertRegex(manifest["manifest_version"], r"^\d+\.\d+\.\d+$")
                for stop in manifest["stop_conditions"]:
                    self.assertEqual(set(stop), {"condition", "action", "next"})
                    self.assertIn(stop["action"], STOP_ACTIONS)
                for entry in manifest["input"]:
                    self.assertEqual(set(entry), {"name", "type", "required", "source"})
                for entry in manifest["output"]:
                    self.assertEqual(set(entry), {"name", "type", "artifact_kind", "atomic"})

    def test_only_the_prototype_emits_a_non_canonical_artifact(self):
        emitters = [skill for skill in EXPECTED_SKILLS if manifest_of(skill)["owner_scope"] == "emit"]
        self.assertEqual(emitters, ["zj-ui-prototype"])
        self.assertEqual(manifest_of("zj-ui-prototype")["writes"], ["preview"])


class FixtureOwnership(unittest.TestCase):
    def test_fixture_ids_resolve_to_the_documented_owner(self):
        table = fixture_table()
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                manifest = manifest_of(skill)
                self.assertGreaterEqual(len(manifest["failure_fixtures"]), 3)
                documented_ids, documented_owner = table[skill]
                # The §4 table lists conflict/failure columns in its own order for
                # two lanes, so the contract is the id set, not its sequence.
                self.assertEqual(sorted(manifest["failure_fixtures"]), sorted(documented_ids))
                self.assertEqual(manifest["owner"], documented_owner)

    def test_every_fixture_id_is_mentioned_in_the_skill_body(self):
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                body = read(UI_ROOT / skill / "SKILL.md")
                for fixture in manifest_of(skill)["failure_fixtures"]:
                    self.assertIn(fixture, body)


class SkeletonIsNotClaimedAsWorking(unittest.TestCase):
    def test_status_marker_is_present_in_metadata_and_body(self):
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                frontmatter = frontmatter_of(skill)
                self.assertIn("status: contract-skeleton", frontmatter)
                self.assertIn("implemented_in: 1-6-", frontmatter)
                body = read(UI_ROOT / skill / "SKILL.md")
                self.assertIn("状态：契约骨架（1-6-1）", body)
                self.assertIn("实现落地前不要把本 skill", body)


class Indexes(unittest.TestCase):
    def test_bucket_readme_registers_every_skill(self):
        text = read(UI_ROOT / "README.md")
        for skill in EXPECTED_SKILLS:
            self.assertIn(f"](./{skill}/SKILL.md)", text, skill)

    def test_top_level_readme_registers_every_skill_and_the_bucket_count(self):
        text = read(REPO / "README.md")
        for skill in EXPECTED_SKILLS:
            self.assertIn(f"](./skills/ui/{skill}/SKILL.md)", text, skill)
        self.assertIn("six purpose-based buckets", text)
        self.assertNotIn("five purpose-based buckets", text)

    def test_agents_md_lists_the_ui_bucket(self):
        self.assertIn("`ui/`", read(REPO / "AGENTS.md"))

    def test_guide_routes_every_skill(self):
        validator = load_module("zj_layout_validator_guide", "scripts/validate-zagentic-plugin.py")
        errors = []
        manifests = validator.discover_skill_manifests(REPO, errors)
        validator.validate_guide_coverage(REPO, manifests, errors)
        validator.validate_readme_registration(REPO, manifests, errors)
        # Scope the assertion to this node's bucket: the repository has unrelated
        # pre-existing registration drift elsewhere, and letting that noise in
        # would make this test red for reasons 1-6-1 cannot fix.
        ui_errors = [error for error in errors if "zj-ui-" in error or "skills/ui" in error]
        self.assertEqual(ui_errors, [])
        for skill in EXPECTED_SKILLS:
            self.assertIn(skill, read(REPO / "skills/engineering/zj-guide/SKILL.md"))

    def test_generated_install_inventory_lists_every_skill(self):
        listed = set(read(REPO / "scripts/zagentic-skills-list").split())
        for skill in EXPECTED_SKILLS:
            self.assertIn(skill, listed)

    def test_glossary_registers_each_skill_vocabulary(self):
        glossary = read(REPO / "ZJ-CONTEXT.md")
        self.assertIn("`ui/`", glossary)
        for term in (
            "UI delivery chain",
            "Experience Version",
            "Canonical UI artifact",
            "Capability manifest",
            "Write owner",
            "Direction card",
            "ui-flow/v1",
            "Unknown quartet",
            "Verification receipt",
            "Human gate",
            "Failure fixture",
            "Contract skeleton",
        ):
            self.assertIn(f"**{term}**", glossary, term)

    def test_template_lists_the_sixteen_fields(self):
        template = read(TEMPLATE)
        for key in MANIFEST_KEYS:
            self.assertIn(key, template, key)


class FrontmatterValidator(unittest.TestCase):
    def test_repository_frontmatter_validator_accepts_the_skeletons(self):
        try:
            import yaml  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("PyYAML missing: install requirements.txt to run frontmatter validation")
        validator = load_module(
            "zj_frontmatter_validator", "scripts/validate-skill-frontmatter.py"
        )
        for skill in EXPECTED_SKILLS:
            with self.subTest(skill=skill):
                self.assertEqual(validator.validate_skill(UI_ROOT / skill / "SKILL.md"), [])


if __name__ == "__main__":
    unittest.main()
