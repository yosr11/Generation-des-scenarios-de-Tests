"""Connexion PostgreSQL async (SQLAlchemy 2.x) + session synchrone pour les repositories."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# ── Moteur async (routes FastAPI auth/admin) ──────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ── Moteur synchrone (repositories métier) ───────────────────────────────────
# Convertit l'URL asyncpg → psycopg2 pour permettre l'usage synchrone
# sans modifier la totalité des repositories d'un seul coup.

_sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

sync_engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
)


def get_sync_session() -> Session:
    """Retourne une session SQLAlchemy synchrone.

    À utiliser dans les repositories qui ne sont pas encore convertis en async.
    Pensez à appeler session.close() dans un bloc finally.
    """
    return SyncSessionLocal()
