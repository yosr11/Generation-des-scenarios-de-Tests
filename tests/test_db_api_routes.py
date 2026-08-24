from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.db.postgres import Base, SyncSessionLocal, sync_engine
import app.repositories.story_repository as story_repository
import app.api.routes_db as routes_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_db_story_get_and_delete(monkeypatch, client):
    Base.metadata.create_all(bind=sync_engine)

    monkeypatch.setattr(story_repository, "get_sync_session", SyncSessionLocal)
    monkeypatch.setattr(routes_db, "get_sync_session", SyncSessionLocal)

    # Insérer directement une story via le repository pour tester la lecture / suppression.
    story_repository.save_story(
        {
            "id": "STORY-42",
            "summary": "Story for API test",
            "description_raw": "raw",
            "description_clean": "clean",
            "epic_key": "EPIC-1",
            "epic_summary": "Epic summary",
            "epic_description": "Epic description",
        }
    )

    response = client.get("/db/stories/STORY-42")
    assert response.status_code == 200
    assert response.json()["id"] == "STORY-42"
    assert response.json()["summary"] == "Story for API test"

    response = client.get("/db/stories")
    assert response.status_code == 200
    assert any(story["id"] == "STORY-42" for story in response.json())

    response = client.delete("/db/stories/STORY-42")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "story_id": "STORY-42"}

    response = client.get("/db/stories/STORY-42")
    assert response.status_code == 404


def test_db_story_not_found_returns_404(monkeypatch, client):
    Base.metadata.create_all(bind=sync_engine)

    monkeypatch.setattr(story_repository, "get_sync_session", SyncSessionLocal)
    monkeypatch.setattr(routes_db, "get_sync_session", SyncSessionLocal)

    response = client.get("/db/stories/UNKNOWN")
    assert response.status_code == 404
    assert "introuvable" in response.json()["detail"].lower()
