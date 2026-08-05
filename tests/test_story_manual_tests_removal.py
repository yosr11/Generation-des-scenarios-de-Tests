from app.repositories.manual_tests_repository import (
    get_latest_manual_tests,
    save_manual_tests_snapshot,
)
from app.repositories.scenario_repository import get_scenarios_by_story


def test_manual_tests_repository_reads_from_scenarios(monkeypatch):
    calls = []

    def fake_scenarios(story_id):
        calls.append(story_id)
        return [
            {
                "id": 1,
                "story_id": story_id,
                "title": "Scenario",
                "type": "",
                "priority": "",
                "preconditions": [],
                "steps": [],
                "expected_result": "",
                "source_ustype": "",
                "model": "",
                "created_at": "",
            }
        ]

    monkeypatch.setattr(
        "app.repositories.manual_tests_repository.get_scenarios_by_story",
        fake_scenarios,
    )

    result = get_latest_manual_tests("story-123")

    assert result is not None
    assert result[0]["test_name"] == "Scenario"
    assert result[0]["priority"] == ""
    assert calls == ["story-123"]


def test_save_manual_tests_snapshot_replaces_existing(monkeypatch):
    calls = []

    def fake_delete(story_id):
        calls.append(("delete", story_id))
        return True

    def fake_save_bulk(scenarios, model=""):
        calls.append(("save", scenarios, model))
        return len(scenarios)

    monkeypatch.setattr(
        "app.repositories.manual_tests_repository.delete_scenarios_by_story",
        fake_delete,
    )
    monkeypatch.setattr(
        "app.repositories.manual_tests_repository.save_scenarios_bulk",
        fake_save_bulk,
    )

    count = save_manual_tests_snapshot(
        "story-123",
        [
            {
                "test_name": "Scenario 1",
                "preconditions": ["precondition"],
                "steps": ["step1"],
                "expected_result": "result",
                "priority": "high",
                "source_ustype": "auto",
                "model": "nova-lite-2",
            }
        ],
        generation_model="nova-lite-2",
    )

    assert count == 1
    assert calls[0] == ("delete", "story-123")
    assert calls[1][0] == "save"
    assert calls[1][2] == "nova-lite-2"
    assert calls[1][1][0]["title"] == "Scenario 1"


def test_scenarios_repository_reads_by_story():
    scenarios = get_scenarios_by_story("nonexistent-story")
    assert scenarios == []
