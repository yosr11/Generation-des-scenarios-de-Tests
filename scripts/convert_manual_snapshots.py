"""Script one-shot : convertir les snapshots `story_manual_tests` en `generated_scenarios`.

Usage (venv activé) :
    .\.venv\Scripts\python.exe scripts\convert_manual_snapshots.py

Il lit tous les enregistrements de `story_manual_tests` et insère un `GeneratedScenario`
par test contenu dans `tests_json`. Il saute les doublons basés sur (story_id, title, steps).
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import text

from app.db.postgres import get_sync_session
from app.models.pg_models import GeneratedScenario


def main():
    session = get_sync_session()
    try:
        table_exists = session.execute(
            text("SELECT to_regclass('public.story_manual_tests')")
        ).scalar()
        if not table_exists:
            print("No story_manual_tests table found, nothing to migrate.")
            return

        rows = session.execute(
            text(
                "SELECT story_id, tests_json, generation_model FROM story_manual_tests ORDER BY created_at ASC"
            )
        ).all()

        inserted = 0
        for story_id, tests_json, generation_model in rows:
            tests = tests_json or []
            for t in tests:
                title = t.get("test_name") or t.get("title") or ""
                if not title and not t.get("steps"):
                    continue
                exists = (
                    session.execute(
                        text(
                            "SELECT 1 FROM generated_scenarios WHERE story_id = :story_id AND title = :title LIMIT 1"
                        ),
                        {"story_id": story_id, "title": title},
                    )
                    .first()
                )
                if exists:
                    continue
                obj = GeneratedScenario(
                    story_id=story_id,
                    title=title,
                    scenario_type=t.get("type", ""),
                    priority=t.get("priority", ""),
                    preconditions=t.get("preconditions", []),
                    steps=t.get("steps", []),
                    expected_result=t.get("expected_result", ""),
                )
                session.add(obj)
                inserted += 1

        session.commit()
        print(f"Inserted {inserted} GeneratedScenario rows from {len(rows)} snapshots")
    finally:
        session.close()


if __name__ == "__main__":
    main()
