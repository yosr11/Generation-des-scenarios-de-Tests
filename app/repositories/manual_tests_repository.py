"""Dernier jeu de tests manuels (Agent 3) par story — PostgreSQL (SQLAlchemy ORM)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.scenario_repository import (
    delete_scenarios_by_story,
    get_scenarios_by_story,
    save_scenarios_bulk,
)


def _test_dict_to_scenario(test_dict: Dict[str, Any], story_id: str) -> Dict[str, Any]:
    return {
        "source_story": story_id,
        "title": test_dict.get("test_name") or test_dict.get("title") or "",
        "type": test_dict.get("type", ""),
        "priority": test_dict.get("priority", ""),
        "preconditions": test_dict.get("preconditions", []),
        "steps": test_dict.get("steps", []),
        "expected_result": test_dict.get("expected_result", ""),
        "source_ustype": test_dict.get("source_ustype", ""),
        "model": test_dict.get("model", ""),
    }


def _scenario_to_test_dict(scenario: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "test_name": scenario.get("title", ""),
        "preconditions": scenario.get("preconditions", []) or [],
        "steps": scenario.get("steps", []) or [],
        "expected_result": scenario.get("expected_result", ""),
        "priority": scenario.get("priority", ""),
        "source_ustype": scenario.get("source_ustype", ""),
        "model": scenario.get("model", ""),
    }


def save_manual_tests_snapshot(
    story_id: str, tests: List[Dict[str, Any]], generation_model: str = ""
) -> int:
    """Persiste les tests manuels en remplaçant l'ensemble des scénarios existants."""
    if not story_id:
        return -1

    delete_scenarios_by_story(story_id)
    if not tests:
        return 0

    scenarios = [
        _test_dict_to_scenario(test, story_id)
        for test in tests
        if isinstance(test, dict)
    ]
    return save_scenarios_bulk(scenarios, model=generation_model)


def get_latest_manual_tests(story_id: str) -> Optional[List[Dict[str, Any]]]:
    """Retourne les tests manuels reconstruits depuis generated_scenarios."""
    if not story_id:
        return None

    scenarios = get_scenarios_by_story(story_id)
    if not scenarios:
        return None

    return [_scenario_to_test_dict(s) for s in scenarios]


def get_latest_manual_tests_as_pydantic(story_id: str):
    """Retourne ManualTestGenerationResult (objet Pydantic) au lieu de liste de dicts."""
    from app.models.test_manual import (
        ManualGenerationStatus,
        ManualTestCase,
        ManualTestGenerationResult,
        RecommendedTestStrategy,
    )

    tests_raw = get_latest_manual_tests(story_id)
    if not tests_raw:
        return None

    try:
        tests = []
        for test_dict in tests_raw:
            try:
                tests.append(ManualTestCase(**test_dict))
            except Exception as e:
                print(f"Error converting test to ManualTestCase: {e}")
                continue

        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy=RecommendedTestStrategy.MANUAL,
            generation_status=ManualGenerationStatus.GENERATED,
            message=f"{len(tests)} tests générés",
            tests=tests,
            notes=[],
        )
    except Exception as e:
        print(f"Error converting manual tests to Pydantic: {e}")
        return None
