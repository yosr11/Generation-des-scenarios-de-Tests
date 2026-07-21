import os


def _set_default_env(name: str, value: str) -> None:
    if not os.getenv(name):
        os.environ[name] = value


# Provide a stable test environment even when no local .env is present.
_set_default_env(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_test"
)
_set_default_env("JWT_SECRET", "test-secret-32-bytes-minimum-for-jwt")
_set_default_env("JWT_ALGORITHM", "HS256")
_set_default_env("ADMIN_EMAIL", "admin@example.com")
_set_default_env("ADMIN_PASSWORD", "strong-test-password")
_set_default_env("GROQ_API_KEY", "test-groq-key")
_set_default_env("JIRA_PROD_URL", "https://jira.example.com")
_set_default_env("JIRA_TEST_URL", "https://jira-test.example.com")
_set_default_env("JIRA_USERNAME", "jira-user")
_set_default_env("JIRA_PASSWORD", "jira-password")
_set_default_env("MICROSOFT_CLIENT_ID", "")
_set_default_env("MICROSOFT_CLIENT_SECRET", "")
_set_default_env("MICROSOFT_TENANT_ID", "common")
