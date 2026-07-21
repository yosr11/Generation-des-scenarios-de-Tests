from fastapi.testclient import TestClient

from app.main import app


def test_auth_login_admin_success(monkeypatch):
    async def fake_get_db():
        yield None

    async def fake_authenticate_user(db, *, identifier, password):
        return {
            "success": True,
            "role": "admin",
            "access_token": "fake-token",
            "user": {"id": 1, "email": identifier, "role": "admin"},
            "projects": None,
        }

    async def fake_update_last_login(db, user_id):
        return None

    async def fake_log_action(
        db, user_identifier, role, action, details=None, ip_address=None
    ):
        return None

    monkeypatch.setattr("app.api.routes_auth.get_db", fake_get_db)
    monkeypatch.setattr("app.api.routes_auth.authenticate_user", fake_authenticate_user)
    monkeypatch.setattr("app.api.routes_auth.update_last_login", fake_update_last_login)
    monkeypatch.setattr("app.api.routes_auth.log_action", fake_log_action)

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"identifier": "admin@example.com", "password": "strong-pass"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "admin"
    assert payload["user"]["email"] == "admin@example.com"
    assert payload["projects"] is None


def test_auth_login_failure_returns_401(monkeypatch):
    async def fake_get_db():
        yield None

    async def fake_authenticate_user(db, *, identifier, password):
        return {"success": False, "error": "Invalid credentials."}

    monkeypatch.setattr("app.api.routes_auth.get_db", fake_get_db)
    monkeypatch.setattr("app.api.routes_auth.authenticate_user", fake_authenticate_user)

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"identifier": "bad@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials."
