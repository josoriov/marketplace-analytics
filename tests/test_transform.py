import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.etl import transform


def test_dbt_uses_locked_binary_and_environment_and_propagates_failure(monkeypatch):
    values = {
        "POSTGRES_HOST": "db.internal", "POSTGRES_PORT": "6543",
        "POSTGRES_DB": "metrics", "POSTGRES_USER": "user", "POSTGRES_PASSWORD": "pass@$word",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setenv("DBT_ALLOW_EXPERIMENTAL_ADAPTERS", "true")

    def fail(command, *, cwd, check):
        assert command == [
            str(Path(sys.executable).with_name("dbt")), "build",
            "--project-dir", str(transform.PROJECT_ROOT / "dbt"),
            "--profiles-dir", str(transform.PROJECT_ROOT / "dbt"),
        ]
        assert {key: os.environ[key] for key in values} == values
        assert os.environ["DBT_ALLOW_EXPERIMENTAL_ADAPTERS"] == "true"
        assert cwd == transform.PROJECT_ROOT
        assert check is True
        raise subprocess.CalledProcessError(2, command)

    monkeypatch.setattr(transform.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        transform.run_dbt("build")
    assert exc_info.value.returncode == 2
