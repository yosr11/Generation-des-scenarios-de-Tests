from app.db.postgres import Base, SyncSessionLocal, sync_engine
from app.repositories import report_repository


def test_save_and_fetch_report(monkeypatch):
    Base.metadata.create_all(bind=sync_engine)
    monkeypatch.setattr(report_repository, "get_sync_session", SyncSessionLocal)

    report_data = {
        "story_id": "ABC-123",
        "report_title": "Rapport de test",
        "report_version": "1.0",
        "generated_timestamp": "2026-08-07T00:00:00Z",
        "executive_summary": {"overall_status": "APPROVED"},
    }

    row_id = report_repository.save_report(report_data)
    saved = report_repository.get_latest_report("ABC-123")

    assert row_id > 0
    assert saved is not None
    assert saved["story_id"] == "ABC-123"
    assert saved["report_title"] == "Rapport de test"
    assert saved["report_data"]["executive_summary"]["overall_status"] == "APPROVED"