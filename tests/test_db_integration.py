from fastapi.testclient import TestClient

from app.main import app
import app.api.routes_db as routes_db


def test_db_routes_can_start_with_empty_database(monkeypatch):
    monkeypatch.setattr(routes_db, "get_all_stories", lambda: [])
    monkeypatch.setattr(routes_db, "get_story_by_id", lambda story_id: None)

    client = TestClient(app)
    response = client.get("/db/stories")

    assert response.status_code == 200
    assert response.json() == []
