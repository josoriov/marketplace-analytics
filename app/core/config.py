"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Load local development variables once when the config module is imported.
load_dotenv(ENV_FILE, override=False)

REQUIRED_ENV_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


@dataclass(frozen=True)
class Settings:
    """Typed database settings used across the application."""

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy connection URL for PostgreSQL.

        Returns:
            str: A SQLAlchemy-compatible PostgreSQL URL including the configured
                host, port, database name, and credentials.
        """
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object built from environment variables.
    Use `get_settings.cache_clear()` if the environment variables have changes.

    Returns:
        Settings: The database configuration assembled from the current
            environment.

    Raises:
        ValueError: If one or more required environment variables are missing
            or if ``POSTGRES_PORT`` is not a valid integer.

    Notes:
        The result is cached for the lifetime of the Python process. Tests that
        modify environment variables should clear the function cache before
        calling this again.
    """
    missing_vars = [
        variable_name
        for variable_name in REQUIRED_ENV_VARS
        if os.getenv(variable_name) in (None, "")
    ]
    if missing_vars:
        # missing_list = ", ".join(missing_vars)
        raise ValueError(
            f"Missing required environment variables: {missing_vars}"
        )

    postgres_port = os.environ["POSTGRES_PORT"]
    try:
        parsed_port = int(postgres_port)
    except ValueError as exc:
        raise ValueError(
            "POSTGRES_PORT must be a valid integer"
        ) from exc

    return Settings(
        postgres_host=os.environ["POSTGRES_HOST"],
        postgres_port=parsed_port,
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
    )
