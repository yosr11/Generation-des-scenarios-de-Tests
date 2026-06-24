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
            jira_updated                TEXT,          -- Jira "updated" timestamp for versioning
            created_at                  TEXT DEFAULT (datetime('now'))
        );

        -- Analyses LLM
        CREATE TABLE IF NOT EXISTS story_analysis (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id                    TEXT NOT NULL,
            model                       TEXT NOT NULL,
            story_title                 TEXT,          -- Titre de la story (ajouté pour Agent 5)
            story_type                  TEXT,
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
            user_flows                  TEXT,          -- JSON
            resolved_from_references    TEXT,          -- JSON
            created_at                  TEXT DEFAULT (datetime('now')),
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

        -- Résultats de validation Agent 3
        CREATE TABLE IF NOT EXISTS agent3_validations (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id                    TEXT NOT NULL,
            coverage_rate               REAL DEFAULT 0.0,
            uncovered_testable_points   TEXT,          -- JSON array
            duplicate_pairs             TEXT,          -- JSON array
            ambiguity_findings          TEXT,          -- JSON array
            validation_status           TEXT,          -- VALID, PARTIALLY_VALID, INVALID
            llm_quality_feedback        TEXT,          -- JSON
            llm_quality_model_alias     TEXT,
            correction_instructions     TEXT,          -- JSON array
            created_at                  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Classifications d'automatisation (Agent 4)
        CREATE TABLE IF NOT EXISTS automation_classifications (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id            TEXT NOT NULL,
            test_name           TEXT NOT NULL,
            classification      TEXT NOT NULL,        -- AUTOMATISER | MANUEL
            confidence          TEXT NOT NULL,        -- HAUTE | MOYENNE | FAIBLE
            raison              TEXT,
            po_feedback         TEXT DEFAULT 'pending', -- pending | validated | rejected
            model               TEXT,
            error               TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id)
        );

        -- Index utiles
        CREATE INDEX IF NOT EXISTS idx_analysis_story  ON story_analysis(story_id);
        CREATE INDEX IF NOT EXISTS idx_manual_tests_story ON story_manual_tests(story_id);
        CREATE INDEX IF NOT EXISTS idx_agent3_validations_story ON agent3_validations(story_id);
        CREATE INDEX IF NOT EXISTS idx_automation_class_story ON automation_classifications(story_id);

        """)
        conn.commit()

        # Migration : ajouter les colonnes AC si la table existait déjà
        _add_column_if_missing(conn, "stories", "acceptance_criteria_raw", "TEXT")
        _add_column_if_missing(conn, "stories", "acceptance_criteria_clean", "TEXT")

        # Migration : ajouter les colonnes epic
        _add_column_if_missing(conn, "stories", "epic_key", "TEXT")
        _add_column_if_missing(conn, "stories", "epic_summary", "TEXT")
        _add_column_if_missing(conn, "stories", "epic_description", "TEXT")

        # Migration : ajouter story_title à story_analysis (pour Agent 5)
        _add_column_if_missing(conn, "story_analysis", "story_title", "TEXT")

        # Migration : ajouter jira_updated pour le versioning des stories
        _add_column_if_missing(conn, "stories", "jira_updated", "TEXT")

        # Migration : ajouter user_flows et resolved_from_references à story_analysis
        _add_column_if_missing(conn, "story_analysis", "user_flows", "TEXT")
        _add_column_if_missing(conn, "story_analysis", "resolved_from_references", "TEXT")

        # Migration : ajouter correction_instructions à agent3_validations
        _add_column_if_missing(conn, "agent3_validations", "correction_instructions", "TEXT")

        print("[OK] Tables SQLite initialisees")
    finally:
        conn.close()


def _add_column_if_missing(conn, table: str, column: str, col_type: str):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        print(f"[Migration] Adding column {table}.{column}")
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
        print(f"[✓] Column {column} added to {table}")
    else:
        print(f"[✓] Column {column} already exists in {table}")
