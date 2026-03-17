import pytest

from app.core.config import get_settings


def test_get_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "analytics")
    monkeypatch.setenv("POSTGRES_USER", "etl_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    settings = get_settings()

    assert settings.postgres_host == "db.internal"
    assert settings.postgres_port == 6543
    assert settings.postgres_db == "analytics"
    assert settings.postgres_user == "etl_user"
    assert settings.postgres_password == "secret"
    assert settings.database_url == (
        "postgresql+psycopg2://etl_user:secret@db.internal:6543/analytics"
    )


def test_get_settings_raises_when_environment_is_missing(monkeypatch) -> None:
    for key in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError) as exc_info:
        get_settings()

    assert str(exc_info.value) == (
        "Missing required environment variables: "
        "POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, "
        "POSTGRES_USER, POSTGRES_PASSWORD"
    )


def test_get_settings_raises_when_port_is_not_an_integer(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "not-a-number")
    monkeypatch.setenv("POSTGRES_DB", "analytics")
    monkeypatch.setenv("POSTGRES_USER", "etl_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    with pytest.raises(ValueError) as exc_info:
        get_settings()

    assert str(exc_info.value) == "POSTGRES_PORT must be a valid integer"
