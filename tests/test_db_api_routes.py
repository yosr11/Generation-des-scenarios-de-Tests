from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.pg_models import Base
import app.repositories.story_repository as story_repository
import app.api.routes_db as routes_db


def test_db_story_get_and_delete(monkeypatch, tmp_path):
    # Création d'une DB SQLite temporaire pour simuler les routes DB sans PostgreSQL.
    sqlite_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(story_repository, "get_sync_session", lambda: SessionLocal())
    monkeypatch.setattr(routes_db, "get_sync_session", lambda: SessionLocal())

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

    with TestClient(app) as client:
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


def test_db_story_not_found_returns_404(monkeypatch, tmp_path):
    sqlite_url = f"sqlite:///{tmp_path / 'test2.db'}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(story_repository, "get_sync_session", lambda: SessionLocal())
    monkeypatch.setattr(routes_db, "get_sync_session", lambda: SessionLocal())

    with TestClient(app) as client:
        response = client.get("/db/stories/UNKNOWN")
        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()
