import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from validate_review import validate_path  # noqa: E402


FIXTURES = SKILL_DIR / "tests" / "fixtures"


class ValidateReviewTest(unittest.TestCase):
    def test_three_representative_documents_pass(self):
        for path in sorted((FIXTURES / "valid").glob("*.md")):
            with self.subTest(path=path.name):
                result = validate_path(path)
                self.assertTrue(result.ok, result.errors)

    def test_unknown_is_not_silently_absent(self):
        result = validate_path(FIXTURES / "invalid" / "unknown-as-absent.md")
        self.assertFalse(result.ok)
        self.assertIn("unknown-as-absent", {issue.code for issue in result.errors})

    def test_approval_requires_evidence(self):
        result = validate_path(FIXTURES / "invalid" / "approve-without-evidence.md")
        self.assertFalse(result.ok)
        codes = {issue.code for issue in result.errors}
        self.assertIn("missing-evidence", codes)
        self.assertIn("unsupported-approve", codes)

    def test_chromium_specific_guidance_is_marked(self):
        result = validate_path(FIXTURES / "invalid" / "chrome-generalization.md")
        self.assertFalse(result.ok)
        self.assertIn(
            "vendor-specific-generalization",
            {issue.code for issue in result.errors},
        )

    def test_missing_contract_heading_is_reported(self):
        text = (FIXTURES / "valid" / "new-proposal.md").read_text(encoding="utf-8")
        text = text.replace("## Open decisions", "## Decisions")
        from validate_review import validate_text

        result = validate_text(text)
        self.assertIn("missing-heading", {issue.code for issue in result.errors})


if __name__ == "__main__":
    unittest.main()
