import polars as pl
import pytest

from app.etl import load
from app.etl.config import IngestionConfig


def _make_config(
    table: str = "raw.test_table",
    columns: tuple[str, ...] = ("col_a", "col_b"),
) -> IngestionConfig:
    return IngestionConfig(
        csv_filename="test.csv",
        destination_table=table,
        expected_columns=columns,
    )


class RecordingCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, sql: str, *args: object) -> None:
        self.executed.append(sql)


class RecordingRawConnection:
    def __init__(self) -> None:
        self.cursor_obj = RecordingCursor()
        self.committed = 0
        self.rolled_back = 0
        self.closed = 0

    def cursor(self) -> RecordingCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def close(self) -> None:
        self.closed += 1


class FakeEngine:
    def __init__(self, raw_conn: RecordingRawConnection) -> None:
        self._raw_conn = raw_conn

    def raw_connection(self) -> RecordingRawConnection:
        return self._raw_conn


# ── _validated_table_name ────────────────────────────────────────────


class TestValidatedTableName:
    def test_accepts_valid_qualified_name(self) -> None:
        assert load._validated_table_name("raw.orders") == "raw.orders"

    def test_rejects_sql_injection_attempt(self) -> None:
        with pytest.raises(ValueError, match="Invalid table identifier"):
            load._validated_table_name("raw; DROP TABLE--")

    def test_rejects_unqualified_name(self) -> None:
        with pytest.raises(ValueError, match="Invalid table identifier"):
            load._validated_table_name("orders")


# ── load_dataset ─────────────────────────────────────────────────────


class TestLoadDataset:
    def test_truncates_and_inserts(self, monkeypatch) -> None:
        raw_conn = RecordingRawConnection()
        engine = FakeEngine(raw_conn)
        config = _make_config(columns=("a", "b"))
        df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})

        inserted: list[tuple[object, ...]] = []

        def fake_execute_values(cursor, sql, rows, page_size=None):
            inserted.extend(rows)

        monkeypatch.setattr(load, "execute_values", fake_execute_values)

        count = load.load_dataset(df, config, engine)

        assert count == 2
        assert raw_conn.committed == 1
        assert raw_conn.closed == 1
        assert "TRUNCATE" in raw_conn.cursor_obj.executed[0]
        assert len(inserted) == 2

    def test_skips_empty_dataframe(self, monkeypatch) -> None:
        raw_conn = RecordingRawConnection()
        engine = FakeEngine(raw_conn)
        config = _make_config(columns=("a",))
        df = pl.DataFrame({"a": pl.Series([], dtype=pl.Int64)})

        count = load.load_dataset(df, config, engine)

        assert count == 0
        assert raw_conn.committed == 1
        assert raw_conn.closed == 1

    def test_rolls_back_on_error(self, monkeypatch) -> None:
        raw_conn = RecordingRawConnection()
        engine = FakeEngine(raw_conn)
        config = _make_config(columns=("a",))
        df = pl.DataFrame({"a": [1]})

        def boom(cursor, sql, rows, page_size=None):
            raise RuntimeError("insert failed")

        monkeypatch.setattr(load, "execute_values", boom)

        with pytest.raises(RuntimeError, match="insert failed"):
            load.load_dataset(df, config, engine)

        assert raw_conn.rolled_back == 1
        assert raw_conn.closed == 1

    def test_selects_only_expected_columns(self, monkeypatch) -> None:
        raw_conn = RecordingRawConnection()
        engine = FakeEngine(raw_conn)
        config = _make_config(columns=("a",))
        df = pl.DataFrame({"a": [1], "extra": ["ignore_me"]})

        inserted: list[tuple[object, ...]] = []

        def fake_execute_values(cursor, sql, rows, page_size=None):
            inserted.extend(rows)

        monkeypatch.setattr(load, "execute_values", fake_execute_values)

        load.load_dataset(df, config, engine)

        assert inserted == [(1,)]


# ── load_all ─────────────────────────────────────────────────────────


class TestLoadAll:
    def test_loads_every_dataset(self, monkeypatch) -> None:
        call_log: list[str] = []

        def fake_load(df, config, engine, *, chunk_size=5_000):
            call_log.append(config.destination_table)
            return df.height

        monkeypatch.setattr(load, "load_dataset", fake_load)
        monkeypatch.setattr(load, "get_engine", lambda: "fake_engine")

        datasets = {
            "olist_orders_dataset.csv": pl.DataFrame({"order_id": ["o1", "o2"]}),
            "olist_customers_dataset.csv": pl.DataFrame({"customer_id": ["c1"]}),
        }

        counts = load.load_all(datasets)

        assert counts == {"raw.orders": 2, "raw.customers": 1}
        assert set(call_log) == {"raw.orders", "raw.customers"}
