from contextlib import contextmanager
from pathlib import Path

import pytest

from app.core import database


class DummySession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class DummyConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class DummyEngineConnection:
    def __init__(self, scalar_value: int = 1) -> None:
        self.scalar_value = scalar_value
        self.executed_statement = None

    def execute(self, statement):
        self.executed_statement = statement
        return DummyScalarResult(self.scalar_value)


class DummyScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class RecordingCursor:
    def __init__(self, should_fail: bool = False) -> None:
        self.executed_sql: str | None = None
        self.should_fail = should_fail

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str) -> None:
        if self.should_fail:
            raise RuntimeError("script execution failed")
        self.executed_sql = sql

    def close(self) -> None:
        pass


class RecordingRawConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self._cursor = cursor
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def cursor(self) -> RecordingCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class RecordingEngine:
    def __init__(self, raw_connection: RecordingRawConnection | None = None) -> None:
        self._raw_connection = raw_connection
        self.connection = DummyConnection()

    def connect(self) -> DummyConnection:
        return self.connection

    def raw_connection(self) -> RecordingRawConnection:
        if self._raw_connection is None:
            raise AssertionError("raw_connection was not configured")
        return self._raw_connection


def test_resolve_sql_path_supports_absolute_paths(tmp_path: Path) -> None:
    script = tmp_path / "custom.sql"
    script.write_text("SELECT 1;", encoding="utf-8")

    resolved = database._resolve_sql_path(script)

    assert resolved == script


def test_resolve_sql_path_supports_db_relative_filenames() -> None:
    resolved = database._resolve_sql_path("schema.sql")

    assert resolved == database.SQL_SCRIPTS_DIR / "schema.sql"


def test_resolve_sql_path_supports_marts_relative_filenames() -> None:
    resolved = database._resolve_sql_path("marts.sql")

    assert resolved == database.SQL_SCRIPTS_DIR / "marts.sql"


def test_resolve_sql_path_raises_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        database._resolve_sql_path("missing.sql")


def test_get_connection_closes_connection(monkeypatch) -> None:
    engine = RecordingEngine()
    monkeypatch.setattr(database, "get_engine", lambda: engine)

    with database.get_connection() as connection:
        assert connection is engine.connection
        assert connection.closed is False

    assert engine.connection.closed is True


def test_session_scope_commits_and_closes_on_success(monkeypatch) -> None:
    session = DummySession()
    monkeypatch.setattr(database, "get_session_factory", lambda: lambda: session)

    with database.session_scope() as yielded_session:
        assert yielded_session is session

    assert session.commit_calls == 1
    assert session.rollback_calls == 0
    assert session.close_calls == 1


def test_session_scope_rolls_back_and_closes_on_error(monkeypatch) -> None:
    session = DummySession()
    monkeypatch.setattr(database, "get_session_factory", lambda: lambda: session)

    with pytest.raises(RuntimeError, match="boom"):
        with database.session_scope():
            raise RuntimeError("boom")

    assert session.commit_calls == 0
    assert session.rollback_calls == 1
    assert session.close_calls == 1


def test_get_db_session_closes_after_generator_finishes(monkeypatch) -> None:
    session = DummySession()
    monkeypatch.setattr(database, "get_session_factory", lambda: lambda: session)

    generator = database.get_db_session()

    assert next(generator) is session

    with pytest.raises(StopIteration):
        next(generator)

    assert session.close_calls == 1


def test_run_sql_script_executes_contents_and_commits(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "load.sql"
    script.write_text("SELECT 42;", encoding="utf-8")
    cursor = RecordingCursor()
    raw_connection = RecordingRawConnection(cursor)
    monkeypatch.setattr(database, "get_engine", lambda: RecordingEngine(raw_connection))

    database.run_sql_script(script)

    assert cursor.executed_sql == "SELECT 42;"
    assert raw_connection.commit_calls == 1
    assert raw_connection.rollback_calls == 0
    assert raw_connection.close_calls == 1


def test_run_sql_script_rolls_back_and_reraises_on_failure(
    monkeypatch, tmp_path: Path
) -> None:
    script = tmp_path / "broken.sql"
    script.write_text("SELECT broken;", encoding="utf-8")
    raw_connection = RecordingRawConnection(RecordingCursor(should_fail=True))
    monkeypatch.setattr(database, "get_engine", lambda: RecordingEngine(raw_connection))

    with pytest.raises(RuntimeError, match="script execution failed"):
        database.run_sql_script(script)

    assert raw_connection.commit_calls == 0
    assert raw_connection.rollback_calls == 1
    assert raw_connection.close_calls == 1


def test_test_connection_executes_select_one(monkeypatch) -> None:
    connection = DummyEngineConnection(scalar_value=1)

    @contextmanager
    def fake_get_connection():
        yield connection

    monkeypatch.setattr(database, "get_connection", fake_get_connection)

    result = database.test_connection()

    assert result == 1
    assert "SELECT 1" in str(connection.executed_statement)
