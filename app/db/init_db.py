"""Compatibility shim for older imports.

PostgreSQL is the only supported database backend.
Use app.db.init_postgres.init_postgres() for initialization.
"""


def init_tables() -> None:
    """Backward-compatible no-op kept for legacy imports."""
    return None
