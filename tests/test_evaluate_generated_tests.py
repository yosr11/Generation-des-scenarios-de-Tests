import json

import eval.comparaison_gold_test.evaluate_generated_tests as eval_mod


def test_call_llm_judge_truncates_large_payload(monkeypatch):
    captured = {}

    def fake_call_github_models(**kwargs):
        captured["user_prompt"] = kwargs["user_prompt"]
        return json.dumps(
            {
                "coverage_score": 80,
                "missing_tests_score": 80,
                "qa_quality_score": 80,
                "business_similarity": 80,
                "final_score": 80.0,
                "missing_scenarios": [],
                "summary": "ok",
            }
        )

    monkeypatch.setattr(eval_mod, "call_github_models", fake_call_github_models)

    user_story = {"title": "Titre", "description": "Description"}
    long_text = "x" * 12000

    eval_mod.call_llm_judge(user_story, long_text, long_text)

    assert "user_prompt" in captured
    assert len(captured["user_prompt"]) <= eval_mod.JUDGE_MAX_CHARS + 2000
    assert "...[tronqué" in captured["user_prompt"]
