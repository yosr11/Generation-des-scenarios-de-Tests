"""Initialisation PostgreSQL et seed admin."""

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal, engine
from app.models.pg_models import Base
from app.services.auth_service import seed_admin_user


async def init_postgres() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Automatic migrations for new fields on users table
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS jira_username VARCHAR(255)")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE")
        except Exception as e:
            print(f"[Migration] PostgreSQL columns checks/add skipped: {e}")

    async with AsyncSessionLocal() as session:
        await seed_admin_user(session)
        print(f"[OK] PostgreSQL ready — admin seed: {settings.ADMIN_EMAIL}")
