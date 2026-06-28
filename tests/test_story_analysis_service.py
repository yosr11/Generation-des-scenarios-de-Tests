import unittest

from app.models.analysis import StoryAnalysisResult, StoryClassificationResult
from app.services.story_analysis_service import merge_story_analysis


class StoryAnalysisMergeTests(unittest.TestCase):
    def test_non_functional_classification_keeps_empty_extraction_arrays(self):
        classification = StoryClassificationResult(
            story_id="TEST-1",
            story_title="Example story",
            story_type="technical",
            analysis_reason=["Internal refactor only"],
        )

        merged = merge_story_analysis(
            classification=classification,
            analysis=None,
            story={"id": "TEST-1", "summary": "Example story"},
        )

        self.assertEqual(merged.story_type, "technical")
        self.assertEqual(merged.actors, [])
        self.assertEqual(merged.actions, [])
        self.assertEqual(merged.business_rules, [])
        self.assertEqual(merged.testable_points, [])
        self.assertEqual(merged.analysis_reason, ["Internal refactor only"])

    def test_functional_story_merges_classification_and_extraction(self):
        classification = StoryClassificationResult(
            story_id="TEST-2",
            story_title="Functional story",
            story_type="functional",
            analysis_reason=["User-visible behavior"],
        )
        analysis = StoryAnalysisResult(
            story_id="TEST-2",
            story_title="Functional story",
            story_type="functional",
            actors=["User"],
            actions=["Submit form"],
            business_rules=["Must select a value"],
            technical_scope=[],
            testable_points=["Verify field validation"],
            user_flows=["Open form", "Submit"],
            acceptance_criteria_explicit=["Field is required"],
            acceptance_criteria_inferred=[],
            clarification_questions=[],
            analysis_reason=["Extraction reason"],
            resolved_from_references=[],
        )

        merged = merge_story_analysis(
            classification=classification,
            analysis=analysis,
            story={"id": "TEST-2", "summary": "Functional story"},
        )

        self.assertEqual(merged.story_type, "functional")
        self.assertEqual(merged.actors, ["User"])
        self.assertEqual(merged.actions, ["Submit form"])
        self.assertEqual(merged.analysis_reason, ["User-visible behavior"])
        self.assertEqual(merged.testable_points, ["Verify field validation"])


if __name__ == "__main__":
    unittest.main()
