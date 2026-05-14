"""
app/db/init_db.py
─────────────────
Création des tables SQLite.
Appelé une seule fois au démarrage de l'application.
"""

from app.db.database import get_connection


def init_tables():
    conn = get_connection()
    try:
        conn.executescript("""

        -- Stories nettoyées / enrichies
        CREATE TABLE IF NOT EXISTS stories (
            id                          TEXT PRIMARY KEY,
            summary                     TEXT,
            description_raw             TEXT,
            description_clean           TEXT,
            description_llm             TEXT,
            acceptance_criteria_raw     TEXT,
            acceptance_criteria_clean   TEXT,
            labels                      TEXT,          -- JSON
            components                  TEXT,          -- JSON
            issuelinks                  TEXT,          -- JSON
            priority                    TEXT,
            status                      TEXT,
            fix_versions                TEXT,          -- JSON
            requirement_status          TEXT,          -- JSON
            references_json             TEXT,          -- JSON
            flags                       TEXT,          -- JSON
            story_context_llm           TEXT,
            epic_key                    TEXT,
            epic_summary                TEXT,
            epic_description            TEXT,
            created_at                  TEXT DEFAULT (datetime('now'))
        );

        -- Analyses LLM
        CREATE TABLE IF NOT EXISTS story_analysis (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id                    TEXT NOT NULL,
            model                       TEXT NOT NULL,
            story_type                  TEXT,
            exploitability              TEXT,
            recommended_test_type       TEXT,
            actors                      TEXT,          -- JSON
            actions                     TEXT,          -- JSON
            business_rules              TEXT,          -- JSON
            technical_scope             TEXT,          -- JSON
            testable_points             TEXT,          -- JSON
            acceptance_criteria_explicit TEXT,         -- JSON
            acceptance_criteria_inferred TEXT,         -- JSON
            clarification_questions     TEXT,          -- JSON
            analysis_reason             TEXT,          -- JSON
            created_at                  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Scénarios de test générés
        CREATE TABLE IF NOT EXISTS generated_scenarios (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id            TEXT NOT NULL,
            title               TEXT,
            type                TEXT,
            priority            TEXT,
            preconditions       TEXT,          -- JSON
            steps               TEXT,          -- JSON
            expected_result     TEXT,
            source_ustype       TEXT,
            model               TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Dernier résultat Agent 2 (tests manuels) par story
        CREATE TABLE IF NOT EXISTS story_manual_tests (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id            TEXT NOT NULL,
            tests_json          TEXT NOT NULL,
            generation_model    TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Scoring / couverture
        CREATE TABLE IF NOT EXISTS story_scoring (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id            TEXT NOT NULL,
            model               TEXT NOT NULL,
            coverage_score      REAL DEFAULT 0,
            quality_score       REAL DEFAULT 0,
            overall_score       REAL DEFAULT 0,
            grade               TEXT,
            coverage_detail     TEXT,          -- JSON
            quality_detail      TEXT,          -- JSON
            risks               TEXT,          -- JSON
            recommendations     TEXT,          -- JSON
            scoring_reason      TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Index utiles
        CREATE INDEX IF NOT EXISTS idx_analysis_story  ON story_analysis(story_id);
        CREATE INDEX IF NOT EXISTS idx_scenario_story  ON generated_scenarios(story_id);
        CREATE INDEX IF NOT EXISTS idx_manual_tests_story ON story_manual_tests(story_id);
        CREATE INDEX IF NOT EXISTS idx_scoring_story   ON story_scoring(story_id);

        """)
        conn.commit()

        # Migration : ajouter les colonnes AC si la table existait déjà
        _add_column_if_missing(conn, "stories", "acceptance_criteria_raw", "TEXT")
        _add_column_if_missing(conn, "stories", "acceptance_criteria_clean", "TEXT")

        # Migration : ajouter les colonnes epic
        _add_column_if_missing(conn, "stories", "epic_key", "TEXT")
        _add_column_if_missing(conn, "stories", "epic_summary", "TEXT")
        _add_column_if_missing(conn, "stories", "epic_description", "TEXT")

        print("[OK] Tables SQLite initialisees")
    finally:
        conn.close()


def _add_column_if_missing(conn, table: str, column: str, col_type: str):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
