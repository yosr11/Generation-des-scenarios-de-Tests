"""Initialisation PostgreSQL et seed admin."""

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal, engine
from app.models.pg_models import Base
from app.services.auth_service import seed_admin_user


async def init_postgres() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_admin_user(session)
        print(f"[OK] PostgreSQL ready — admin seed: {settings.ADMIN_EMAIL}")
