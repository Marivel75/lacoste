from src.services.collection_run_service import log_run

WEEK = "2026-W21"


def test_log_success(db):
    run = log_run(db, WEEK, articles_fetched=10, articles_new=5, status="success")
    assert run.id is not None
    assert run.week == WEEK
    assert run.articles_fetched == 10
    assert run.articles_new == 5
    assert run.status == "success"
    assert run.error_message is None


def test_log_error(db):
    run = log_run(db, WEEK, 0, 0, "error", "Connection timeout")
    assert run.status == "error"
    assert run.error_message == "Connection timeout"


def test_multiple_runs_same_week(db):
    log_run(db, WEEK, 10, 10, "success")
    log_run(db, WEEK, 0, 0, "error", "Timeout")

    from src.models.collection_run import CollectionRun
    runs = db.query(CollectionRun).filter_by(week=WEEK).all()
    assert len(runs) == 2
