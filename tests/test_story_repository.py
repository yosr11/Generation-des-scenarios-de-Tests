from app.db.postgres import Base, SyncSessionLocal, sync_engine
from app.repositories import story_repository as story_repo


def test_story_repository_save_and_retrieve(monkeypatch):
    Base.metadata.create_all(bind=sync_engine)

    monkeypatch.setattr(story_repo, "get_sync_session", SyncSessionLocal)

    story = {
        "id": "STORY-1",
        "summary": "Story repository integration test",
        "description_raw": "Raw description",
        "description_clean": "Clean description",
        "labels": ["backend"],
        "components": ["api"],
        "issuelinks": [],
        "priority": "High",
        "status": "open",
        "fixVersions": [],
        "requirement_status": {},
        "references": {},
        "flags": {},
        "story_context_llm": "",
        "epic_key": "EPIC-1",
        "epic_summary": "Epic summary",
        "epic_description": "Epic description",
        "jira_updated": "2026-07-21",
    }

    saved_id = story_repo.save_story(story)
    assert saved_id == "STORY-1"

    loaded = story_repo.get_story_by_id("STORY-1")
    assert loaded is not None
    assert loaded["id"] == "STORY-1"
    assert loaded["summary"] == "Story repository integration test"
    assert loaded["epic_key"] == "EPIC-1"

    all_stories = story_repo.get_all_stories()
    assert any(story["id"] == "STORY-1" for story in all_stories)
