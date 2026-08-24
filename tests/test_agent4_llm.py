from app.api.routes_agent4 import Agent4ThresholdsBody
from app.models.test_manual import ManualTestCase, ManualTestStep
from app.services import agent4_ambiguity_service as ambiguity_service
from app.services import agent4_quality_llm_service as quality_service


def _test_case() -> ManualTestCase:
    return ManualTestCase(
        story_id="TEST-1",
        test_name="Test ambigu",
        objective="Valider la recherche",
        steps=[
            ManualTestStep(
                index=1,
                action="Effectuer une recherche",
                expected_result="Le résultat est traité correctement",
            )
        ],
    )


def test_ambiguity_detection_uses_rules():
    findings = ambiguity_service.detect_ambiguous_steps(_test_case())

    assert len(findings) == 0


def test_ambiguity_detection_flags_verifier_with_rules():
    test = _test_case()
    test.steps[0].expected_result = "Vérifier le résultat"

    findings = ambiguity_service.detect_ambiguous_steps(test)

    assert findings[0].field == "expected_result"


def test_agent4_quality_feedback_uses_bedrock_for_nova(monkeypatch):
    calls = {}

    def fake_call_llm(**kwargs):
        calls.update(kwargs)
        return '{"score": 8, "summary": "Tests clairs"}'

    monkeypatch.setattr(quality_service, "call_llm", fake_call_llm)

    result = quality_service.llm_quality_feedback(
        story_id="TEST-1",
        story_summary="Recherche",
        testable_points=["Rechercher"],
        tests=[_test_case().model_dump()],
        metrics={},
    )

    assert result["score"] == 8
    assert calls["provider"] == "bedrock"


def test_agent4_quality_feedback_accepts_json_code_fences(monkeypatch):
    monkeypatch.setattr(
        quality_service,
        "call_llm",
        lambda **kwargs: '```json\n{"score": 7.5, "summary": "Tests cohérents"}\n```',
    )

    result = quality_service.llm_quality_feedback(
        story_id="TEST-1",
        story_summary="Recherche",
        testable_points=["Rechercher"],
        tests=[],
        metrics={},
    )

    assert result == {
        "score": 8,
        "summary": "Tests cohérents",
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
    }


def test_agent4_llm_features_are_enabled_by_default():
    defaults = Agent4ThresholdsBody()

    assert defaults.run_llm_quality_feedback is True
    assert not hasattr(defaults, "run_llm_ambiguity_detection")