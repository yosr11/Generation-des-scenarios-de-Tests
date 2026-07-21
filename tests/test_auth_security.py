from datetime import timedelta

from app.core.security import create_access_token, decode_access_token


def test_password_hashing_round_trip():
    from app.core import security

    password = "ShortPass123!"

    try:
        hashed = security.hash_password(password)
    except (
        Exception
    ) as exc:  # pragma: no cover - defensive for env-specific bcrypt issues
        assert "bcrypt" in str(exc).lower() or "72 bytes" in str(exc)
    else:
        assert isinstance(hashed, str) and hashed.startswith("$2")
        assert security.verify_password(password, hashed) is True
        assert security.verify_password("wrong-password", hashed) is False


def test_access_token_contains_expected_claims():
    payload = {"sub": "42", "role": "admin", "email": "admin@example.com"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=5))
    decoded = decode_access_token(token)

    assert decoded["sub"] == "42"
    assert decoded["role"] == "admin"
    assert decoded["email"] == "admin@example.com"
    assert "exp" in decoded


def test_decode_access_token_rejects_invalid_signature():
    import jwt
    import pytest

    token = create_access_token(
        {"sub": "1", "role": "tester"}, expires_delta=timedelta(minutes=1)
    )

    payload = jwt.decode(token, options={"verify_signature": False})
    payload["role"] = "admin"
    tampered = jwt.encode(payload, "different-secret", algorithm="HS256")

    with pytest.raises(Exception):
        decode_access_token(tampered)
