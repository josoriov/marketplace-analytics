import subprocess

import pytest

from app.etl import pipeline
from app.etl.validators import ValidationReport


class TestRunPipeline:
    def test_executes_all_steps_in_order(self, monkeypatch) -> None:
        call_order: list[str] = []

        monkeypatch.setattr(
            pipeline, "test_connection", lambda: call_order.append("connect"),
        )
        monkeypatch.setattr(pipeline, "run_sql_script", lambda s: call_order.append(s))
        monkeypatch.setattr(
            pipeline, "extract_datasets",
            lambda **kw: (call_order.append("extract") or {}),
        )
        report = ValidationReport()
        monkeypatch.setattr(
            pipeline, "validate_all",
            lambda ds: (call_order.append("validate") or report),
        )
        monkeypatch.setattr(
            pipeline, "load_all",
            lambda ds: (call_order.append("load") or {}),
        )
        monkeypatch.setattr(pipeline, "run_dbt", lambda *args: call_order.append("dbt build"))

        pipeline.run_pipeline()

        assert call_order == [
            "connect",
            "schema.sql",
            "extract",
            "validate",
            "load",
            "indexes.sql",
            "dbt build",
        ]

    def test_aborts_on_validation_failure(self, monkeypatch) -> None:
        script_calls: list[str] = []

        monkeypatch.setattr(pipeline, "test_connection", lambda: None)
        monkeypatch.setattr(
            pipeline, "run_sql_script", lambda s: script_calls.append(s),
        )
        monkeypatch.setattr(pipeline, "extract_datasets", lambda **kw: {})

        report = ValidationReport()
        report.add_error("raw.test", "bad_data", "broken")
        monkeypatch.setattr(pipeline, "validate_all", lambda ds: report)

        with pytest.raises(SystemExit) as exc_info:
            pipeline.run_pipeline()

        assert exc_info.value.code == 1
        assert script_calls == ["schema.sql"]

    def test_propagates_dbt_failure(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "test_connection", lambda: None)
        monkeypatch.setattr(pipeline, "run_sql_script", lambda s: None)
        monkeypatch.setattr(pipeline, "extract_datasets", lambda: {})
        monkeypatch.setattr(pipeline, "validate_all", lambda ds: ValidationReport())
        monkeypatch.setattr(pipeline, "load_all", lambda ds: None)

        def fail(*args):
            raise subprocess.CalledProcessError(1, ["dbt", *args])

        monkeypatch.setattr(pipeline, "run_dbt", fail)
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            pipeline.run_pipeline()
        assert exc_info.value.returncode == 1
