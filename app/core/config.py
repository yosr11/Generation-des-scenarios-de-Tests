# Gère les variables d'environnement (.env).
# Centralise les chemins JSON, credentials API, seuils et paramètres agents.

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Set it in your .env file or shell environment before starting the app."
        )
    return value


def _get_optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Configuration centralisée pour tous les agents."""

    # ── Core application settings ─────────────────────────────
    DATABASE_URL = _get_required_env("DATABASE_URL")
    JWT_SECRET = _get_required_env("JWT_SECRET")
    JWT_ALGORITHM = _get_optional_env("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(_get_optional_env("JWT_EXPIRE_MINUTES", "480"))
    COOKIE_NAME = _get_optional_env("COOKIE_NAME", "access_token")
    COOKIE_SECURE = _get_bool_env("COOKIE_SECURE", False)
    COOKIE_SAMESITE = _get_optional_env("COOKIE_SAMESITE", "lax")

    # ── Auth / admin bootstrap ───────────────────────────────
    ADMIN_EMAIL = _get_required_env("ADMIN_EMAIL")
    ADMIN_PASSWORD = _get_required_env("ADMIN_PASSWORD")

    # ── Microsoft OAuth ───────────────────────────────────────
    MICROSOFT_CLIENT_ID = _get_optional_env("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = _get_optional_env("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID = _get_optional_env("MICROSOFT_TENANT_ID", "common")
    MICROSOFT_REDIRECT_URI = _get_optional_env(
        "MICROSOFT_REDIRECT_URI",
        "http://localhost:8000/auth/microsoft/callback",
    )
    MICROSOFT_SCOPES = _get_optional_env(
        "MICROSOFT_SCOPES",
        "openid profile email User.Read offline_access",
    )
    MICROSOFT_PROMPT = _get_optional_env("MICROSOFT_PROMPT", "login")
    MICROSOFT_ALLOWED_EMAIL_DOMAIN = _get_optional_env("MICROSOFT_ALLOWED_EMAIL_DOMAIN")
    FRONTEND_BASE_URL = _get_optional_env("FRONTEND_BASE_URL", "http://localhost:5173")

    # ── SMTP Mail ────────────────────────────────────────────
    SMTP_HOST = _get_optional_env("SMTP_HOST")
    SMTP_PORT = int(_get_optional_env("SMTP_PORT", "587"))
    SMTP_USER = _get_optional_env("SMTP_USER")
    SMTP_PASSWORD = _get_optional_env("SMTP_PASSWORD")
    SMTP_FROM = _get_optional_env("SMTP_FROM")

    # ── LLM / Groq ──────────────────────────────────────────
    GROQ_API_KEY = _get_required_env("GROQ_API_KEY")
    LLM_PROVIDER = _get_optional_env("LLM_PROVIDER", "groq")
    LLM_DEFAULT_MODEL = _get_optional_env("LLM_DEFAULT_MODEL", "qwen3")
    LLM_TEMPERATURE = float(_get_optional_env("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS = int(_get_optional_env("LLM_MAX_TOKENS", "2000"))
    LLM_MAX_RETRIES = int(_get_optional_env("LLM_MAX_RETRIES", "6"))
    LLM_RETRY_SLEEP = float(_get_optional_env("LLM_RETRY_SLEEP", "1.5"))
    LLM_TIMEOUT = int(_get_optional_env("LLM_TIMEOUT", "60"))

    # ── AWS / Bedrock ────────────────────────────────────────
    AWS_ACCESS_KEY_ID = _get_optional_env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = _get_optional_env("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = _get_optional_env("AWS_REGION", "eu-west-3")
    BEDROCK_MODEL_ID = _get_optional_env("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")

    # ── Jira ─────────────────────────────────────────────────
    JIRA_PROD_URL = _get_required_env("JIRA_PROD_URL")
    JIRA_TEST_URL = _get_required_env("JIRA_TEST_URL")
    JIRA_USERNAME = _get_required_env("JIRA_USERNAME")
    JIRA_PASSWORD = _get_required_env("JIRA_PASSWORD")
    JIRA_BASE_URL = _get_optional_env("JIRA_BASE_URL", JIRA_PROD_URL)
    XRAY_USE_TEST_JIRA = _get_bool_env("XRAY_USE_TEST_JIRA", True)
    XRAY_TEST_ISSUETYPE_ID = _get_optional_env("XRAY_TEST_ISSUETYPE_ID", "10800")

    # ── Agent defaults ───────────────────────────────────────
    AGENT1_DEFAULT_MODEL = _get_optional_env("AGENT1_DEFAULT_MODEL", "nova-lite-2")
    AGENT2_DEFAULT_MODEL = _get_optional_env("AGENT2_DEFAULT_MODEL", "nova-lite-2")
    AGENT3_COVERAGE_THRESHOLD = float(
        _get_optional_env("AGENT3_COVERAGE_THRESHOLD", "0.70")
    )
    AGENT3_COVERAGE_SIMILARITY = float(
        _get_optional_env("AGENT3_COVERAGE_SIMILARITY", "0.7")
    )
    AGENT3_DUPLICATE_THRESHOLD = float(
        _get_optional_env("AGENT3_DUPLICATE_THRESHOLD", "0.8")
    )
    AGENT3_EMBEDDING_MODEL = _get_optional_env(
        "AGENT3_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    AGENT3_QUALITY_MODEL = _get_optional_env("AGENT3_QUALITY_MODEL", "nova-lite-2")
    AGENT5_DEFAULT_MODEL = _get_optional_env("AGENT5_DEFAULT_MODEL", "nova-lite-2")
    ORCHESTRATOR_MAX_RETRIES = int(_get_optional_env("ORCHESTRATOR_MAX_RETRIES", "2"))


settings = Settings()

Path("app/data").mkdir(parents=True, exist_ok=True)
