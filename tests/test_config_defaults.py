from app.core.config import settings


def test_required_settings_are_available_in_test_environment():
    assert settings.JWT_SECRET
    assert settings.ADMIN_EMAIL
    assert settings.ADMIN_PASSWORD
    assert settings.GROQ_API_KEY
