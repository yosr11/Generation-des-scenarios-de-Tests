from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.db.postgres import Base
from app.main import app


def test_db_routes_can_start_with_empty_database(tmp_path, monkeypatch):
    # Utilise une base SQLite temporaire pour vérifier les routes DB basiques.
    sqlite_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    Base.metadata.create_all(bind=engine)

    monkeypatch.setenv("DATABASE_URL", sqlite_url)
    client = TestClient(app)

    response = client.get("/db/stories")
    assert response.status_code == 200
    assert response.json() == []
