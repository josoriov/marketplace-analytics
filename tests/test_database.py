import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core import database


def test_sql_paths(tmp_path):
    script = tmp_path / "custom.sql"
    script.write_text("SELECT 1;")
    assert database._resolve_sql_path(script) == script
    assert database._resolve_sql_path("schema.sql") == database.SQL_SCRIPTS_DIR / "schema.sql"
    assert database._resolve_sql_path("app/db/schema.sql") == database.SQL_SCRIPTS_DIR / "schema.sql"
    with pytest.raises(FileNotFoundError):
        database._resolve_sql_path("missing.sql")


def test_sql_scripts_commit_rollback_and_close(monkeypatch, tmp_path):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(database, "get_engine", lambda: engine)
    script = tmp_path / "script.sql"
    try:
        script.write_text("\ufeffCREATE TABLE example (value INTEGER CHECK (value > 0));")
        database.run_sql_script(script)
        script.write_text("INSERT INTO example VALUES (42);")
        database.run_sql_script(script)
        script.write_text("INSERT INTO example VALUES (-1);")
        with pytest.raises(IntegrityError):
            database.run_sql_script(script)
        with database.get_connection() as connection:
            assert connection.execute(text("SELECT value FROM example")).all() == [(42,)]
        assert connection.closed
        assert database.test_connection() == 1
    finally:
        engine.dispose()
