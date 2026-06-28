# Gère les variables d'environnement (.env).
# Centralise les chemins JSON, credentials API, seuils et paramètres agents.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuration centralisée pour tous les agents."""

    # ── Paths ────────────────────────────────────────────────
    STORIES_PATH = os.getenv("STORIES_PATH", "app/data/stories.json")
    DB_PATH = os.getenv("DB_PATH", "app/data/agent.db")

    # ── PostgreSQL ───────────────────────────────────────────
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_test",
    )

    # ── Auth / JWT ───────────────────────────────────────────
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-long-random-string")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    COOKIE_NAME = os.getenv("COOKIE_NAME", "access_token")
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
    MICROSOFT_REDIRECT_URI = os.getenv(
        "MICROSOFT_REDIRECT_URI",
        "http://localhost:8000/auth/microsoft/callback",
    )
    MICROSOFT_SCOPES = os.getenv(
        "MICROSOFT_SCOPES",
        "openid profile email User.Read offline_access",
    )
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "yomahfoudh@soprahr.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "soprahr2026")

    # ── LLM / Groq ──────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    LLM_DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "qwen3")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "6"))
    LLM_RETRY_SLEEP = float(os.getenv("LLM_RETRY_SLEEP", "1.5"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

    # ── AWS / Bedrock ────────────────────────────────────────
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")

    # ── Jira ─────────────────────────────────────────────────
    JIRA_PROD_URL = os.getenv("JIRA_PROD_URL", "https://hra-jira.ptx.fr.sopra")
    JIRA_TEST_URL = os.getenv("JIRA_TEST_URL", "https://hra-test-jira.ptx.fr.sopra")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
    JIRA_PASSWORD = os.getenv("JIRA_PASSWORD", "")
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", JIRA_PROD_URL)

    # ── Agent 1 — Analysis ───────────────────────────────────
    AGENT1_DEFAULT_MODEL = os.getenv("AGENT1_DEFAULT_MODEL", "llama4")

    # ── Agent 2 — Test Generation ────────────────────────────
    AGENT2_DEFAULT_MODEL = os.getenv("AGENT2_DEFAULT_MODEL", "llama4")

    # ── Agent 3 — Validation ─────────────────────────────────
    AGENT3_COVERAGE_THRESHOLD = float(os.getenv("AGENT3_COVERAGE_THRESHOLD", "0.70"))
    AGENT3_COVERAGE_SIMILARITY = float(os.getenv("AGENT3_COVERAGE_SIMILARITY", "0.7"))
    AGENT3_DUPLICATE_THRESHOLD = float(os.getenv("AGENT3_DUPLICATE_THRESHOLD", "0.8"))
    AGENT3_EMBEDDING_MODEL = os.getenv(
        "AGENT3_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    AGENT3_QUALITY_MODEL = os.getenv("AGENT3_QUALITY_MODEL", "qwen3")

    # ── Agent 5 — Reporting ──────────────────────────────────
    AGENT5_DEFAULT_MODEL = os.getenv("AGENT5_DEFAULT_MODEL", "qwen3")

    # ── Orchestrator ─────────────────────────────────────────
    ORCHESTRATOR_MAX_RETRIES = int(os.getenv("ORCHESTRATOR_MAX_RETRIES", "2"))


settings = Settings()

Path("app/data").mkdir(parents=True, exist_ok=True)
