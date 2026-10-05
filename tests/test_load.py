from unittest.mock import MagicMock

import polars as pl
import pytest

from app.etl import load
from app.etl.config import IngestionConfig


def test_table_identifiers():
    assert load._validated_table_name("raw.orders") == "raw.orders"
    for name in ("orders", "raw; DROP TABLE--", "raw.orders\n"):
        with pytest.raises(ValueError, match="Invalid table identifier"):
            load._validated_table_name(name)

    engine = MagicMock()
    config = IngestionConfig("test.csv", "raw.test", ("a); DROP TABLE raw.test--",))
    df = pl.DataFrame({config.expected_columns[0]: [1]})
    with pytest.raises(ValueError, match="Invalid column identifier"):
        load.load_dataset(df, config, engine)
    engine.begin.assert_not_called()


def test_load_batches_expected_columns_in_one_transaction(monkeypatch):
    engine = MagicMock()
    transaction = engine.begin.return_value
    cursor = transaction.__enter__.return_value.connection.cursor.return_value.__enter__.return_value
    insert = MagicMock()
    monkeypatch.setattr(load, "execute_values", insert)
    config = IngestionConfig("test.csv", "raw.test", ("a",))
    df = pl.DataFrame({"a": [1, 2, 3], "extra": ["x", "y", "z"]})
    assert load.load_dataset(df, config, engine, chunk_size=2) == 3
    cursor.execute.assert_called_once_with("TRUNCATE TABLE raw.test")
    assert [call.args[2] for call in insert.call_args_list] == [[(1,), (2,)], [(3,)]]
    transaction.__exit__.assert_called_once_with(None, None, None)

    insert.reset_mock()
    assert load.load_dataset(df.head(0), config, engine) == 0
    insert.assert_not_called()
    with pytest.raises(ValueError, match="chunk_size"):
        load.load_dataset(df, config, engine, chunk_size=0)

    engine.reset_mock()
    insert.side_effect = RuntimeError("insert failed")
    with pytest.raises(RuntimeError, match="insert failed"):
        load.load_dataset(df, config, engine)
    assert transaction.__exit__.call_args.args[0] is RuntimeError


def test_load_all_reuses_configuration(monkeypatch):
    engine = object()
    monkeypatch.setattr(load, "get_engine", lambda: engine)
    monkeypatch.setattr(load, "load_dataset", lambda df, config, engine: df.height)
    assert load.load_all({
        "olist_orders_dataset.csv": pl.DataFrame({"order_id": ["o1", "o2"]}),
        "olist_customers_dataset.csv": pl.DataFrame({"customer_id": ["c1"]}),
    }) == {"raw.orders": 2, "raw.customers": 1}
