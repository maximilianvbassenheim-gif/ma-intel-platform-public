import hashlib
import json
import unittest
from pathlib import Path

from scripts.compute_diligence import render_markdown, score_case


REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "data" / "internal" / "DEMO_diligence_case.json"


class TestDiligenceAssessment(unittest.TestCase):
    def setUp(self):
        raw = DEMO_PATH.read_bytes()
        self.case = json.loads(raw)
        self.source_hash = hashlib.sha256(raw).hexdigest()

    def test_score_and_provenance_are_reproducible(self):
        report = score_case(self.case, self.source_hash, "2026-10-01T00:00:00+00:00")
        self.assertEqual(report["provenance"]["input_sha256"], self.source_hash)
        self.assertEqual(report["overall_score"], 58.16)
        self.assertEqual(report["status"], "preliminary")
        self.assertEqual(len(report["criteria"]), 4)

    def test_conflicting_evidence_and_questions_are_reported(self):
        report = score_case(self.case, self.source_hash, "2026-10-01T00:00:00+00:00")
        market = report["criteria"][0]
        self.assertTrue(market["has_conflicting_evidence"])
        self.assertEqual(
            {item["stance"] for item in market["evidence"]},
            {"supports", "concerns"},
        )
        self.assertTrue(market["open_questions"])
        markdown = render_markdown(report)
        self.assertIn("Counter-evidence / concern", markdown)
        self.assertIn("Open questions", markdown)

    def test_missing_criterion_evidence_lowers_coverage(self):
        self.case["criteria"][0]["evidence"] = []
        report = score_case(self.case, self.source_hash, "2026-10-01T00:00:00+00:00")
        self.assertLess(report["confidence_coverage"], 0.7)
        self.assertIsNone(report["criteria"][0]["score"])
        self.assertEqual(report["status"], "preliminary")

    def test_invalid_confidence_is_rejected(self):
        self.case["criteria"][0]["evidence"][0]["confidence"] = 1.5
        with self.assertRaisesRegex(ValueError, "confidence must be between 0 and 1"):
            score_case(self.case, self.source_hash, "2026-10-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
