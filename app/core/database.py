"""Database connection and SQL execution helpers for the app."""

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import PROJECT_ROOT, get_settings


SQL_SCRIPTS_DIR = PROJECT_ROOT / "app" / "db"


@lru_cache
def get_engine() -> Engine:
    """Create and cache the shared SQLAlchemy engine.

    Returns:
        Engine: The shared SQLAlchemy engine used for all database access in
            the current process.

    Notes:
        ``pool_pre_ping=True`` is enabled so stale pooled connections are
        checked before use and transparently refreshed when needed.
    """
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker:
    """Create and cache the session factory used by the app.

    Returns:
        sessionmaker: A configured SQLAlchemy session factory bound to the
            shared engine.

    Notes:
        Sessions created by this factory do not autocommit, do not autoflush,
        and keep loaded objects available after commit.
    """
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Yield a SQLAlchemy connection and close it automatically.

    Yields:
        Connection: An open SQLAlchemy connection bound to the shared engine.

    Notes:
        The connection is always closed when the context manager exits, even if
        the caller raises an exception.
    """
    connection = get_engine().connect()
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session that commits or rolls back as needed.

    Yields:
        Session: An active SQLAlchemy session for grouped database work.

    Raises:
        Exception: Re-raises any exception from the caller after rolling back
            the session transaction.

    Notes:
        Successful usage commits once when the context exits. Failures trigger
        a rollback before the session is closed.
    """
    # First call returns a sessionmaker object and the second creates and actual session
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """Yield a session for FastAPI-style dependency injection.

    Yields:
        Session: A SQLAlchemy session that stays open for the dependency scope.

    Notes:
        This generator is intended for frameworks like FastAPI that manage the
        lifecycle of yielded dependencies and finalize them after the request.
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def run_sql_script(script_path: str | Path) -> None:
    """Execute a SQL script file inside a single database transaction.

    Args:
        script_path: Path to the SQL file to execute. This can be an absolute
            path, a project-relative path such as ``app/db/schema.sql``, or a
            filename relative to ``app/db/`` such as ``schema.sql``.

    Returns:
        None: This helper executes the file for its side effects and does not
            return a query result.

    Raises:
        FileNotFoundError: If the SQL file cannot be resolved from the provided
            path.
        Exception: Re-raises any database error raised while executing the
            script after rolling back the transaction.

    Notes:
        The entire file is executed as written using a raw DBAPI connection so
        PostgreSQL-specific multi-statement scripts, including ``DO`` blocks
        and repeated DDL, work correctly.
    """
    resolved_path = _resolve_sql_path(script_path)
    # Defensive encode reading in case of a byte-order mark at the start of sql file
    sql = resolved_path.read_text(encoding="utf-8-sig")

    # Use the DBAPI connection so Postgres can execute the full multi-statement
    # script exactly as written, including DO blocks and repeated DDL.
    raw_connection = get_engine().raw_connection()
    cursor = raw_connection.cursor()
    try:
        cursor.execute(sql)
        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        cursor.close()
        raw_connection.close()


def test_connection() -> int:
    """Run a trivial query to confirm database connectivity.

    Returns:
        int: The scalar result of ``SELECT 1`` when the database connection is
            healthy.

    Raises:
        Exception: Propagates any connection or query execution error raised by
            SQLAlchemy or the database driver.
    """
    with get_connection() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()


def _resolve_sql_path(script_path: str | Path) -> Path:
    """Resolve an absolute or project-relative path to a SQL script file.

    Args:
        script_path: The input path to resolve. This may be absolute,
            project-relative, or relative to ``app/db/``.

    Returns:
        Path: The resolved filesystem path for the SQL script.

    Raises:
        FileNotFoundError: If the script does not exist in any supported
            location.
    """
    path = Path(script_path)

    if path.is_absolute():
        if path.exists():
            return path
        raise FileNotFoundError(f"SQL script does not exist: {path}")

    for candidate in (PROJECT_ROOT / path, SQL_SCRIPTS_DIR / path):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"SQL script does not exist: {script_path}")
