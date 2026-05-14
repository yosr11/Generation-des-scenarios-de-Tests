"""
app/db/database.py
──────────────────
Connexion SQLite centralisée.
Fournit get_connection() réutilisable par tous les repositories.
"""

import sqlite3
from pathlib import Path

DB_DIR = Path("app/data")
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "agent.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
