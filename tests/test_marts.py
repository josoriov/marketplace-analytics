"""PostgreSQL regression check; requires an empty disposable database.

METRICS_TEST_DATABASE_URL=postgresql://... uv run pytest tests/test_marts.py -q
Fixtures are committed for dbt connections; owned schemas are dropped on exit.
"""

import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.etl.transform import run_dbt

SQL_DIR = Path(__file__).resolve().parents[1] / "app" / "db"


def test_mart_metrics_use_their_documented_grains(monkeypatch, tmp_path) -> None:
    url = os.environ.get("METRICS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set METRICS_TEST_DATABASE_URL to an empty disposable PostgreSQL database")

    parsed = make_url(url)
    for key, value in {
        "POSTGRES_HOST": parsed.host or "localhost",
        "POSTGRES_PORT": str(parsed.port or 5432),
        "POSTGRES_DB": parsed.database,
        "POSTGRES_USER": parsed.username,
        "POSTGRES_PASSWORD": parsed.password or "",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    dbt_args = ["--target-path", str(tmp_path / "target"), "--log-path", str(tmp_path / "logs")]

    connection = psycopg2.connect(url)
    connection.autocommit = True
    owns_schemas = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regnamespace('raw'), to_regnamespace('silver'), to_regnamespace('analytics')")
            assert cursor.fetchone() == (None, None, None), "Use an empty disposable database"
            owns_schemas = True
            cursor.execute((SQL_DIR / "schema.sql").read_text())
            cursor.execute("""
                INSERT INTO raw.customers (customer_id, customer_city, customer_state)
                VALUES ('c1', 'sao paulo', 'SP'), ('c2', 'rio', 'RJ');
                INSERT INTO raw.sellers (seller_id, seller_city, seller_state)
                VALUES ('s1', 'sao paulo', 'SP'), ('s2', 'rio', 'RJ'), ('s3', 'santos', 'SP');
                INSERT INTO raw.products (product_id, product_category_name)
                VALUES ('p1', 'livros'), ('p2', ' artesanal '), ('p3', '');
                INSERT INTO raw.category_translation
                VALUES ('livros', 'books');
                INSERT INTO raw.orders (
                    order_id, customer_id, order_status,
                    order_delivered_customer_date, order_estimated_delivery_date
                ) VALUES
                    ('o1', 'c1', 'delivered', '2020-01-12', '2020-01-10'),
                    ('o2', 'c1', 'delivered', '2020-01-08', '2020-01-10'),
                    ('o3', 'c1', 'delivered', NULL, '2020-01-10'),
                    ('o4', 'c1', 'canceled', '2020-01-12', '2020-01-10'),
                    ('o5', 'c1', 'shipped', '2020-01-12', '2020-01-10'),
                    ('o6', 'c1', 'delivered', '2020-01-10', '2020-01-10'),
                    ('o7', 'c1', 'delivered', '2020-01-12', NULL),
                    ('o8', 'missing', 'delivered', '2020-01-12', '2020-01-10'),
                    ('o9', 'c2', 'delivered', NULL, '2020-01-10');
                INSERT INTO raw.order_items (
                    order_id, order_item_id, product_id, seller_id, price, freight_value
                ) VALUES
                    ('o1', 1, 'p1', 's1', 100, 10),
                    ('o1', 2, 'p1', 's1', 50, 5),
                    ('o1', 3, 'p2', 's2', 25, 2.5),
                    ('o2', 1, 'p1', 's1', 30, 3),
                    ('o3', 1, 'p3', 's1', 40, 4),
                    ('o4', 1, 'p1', 's1', 999, 99),
                    ('o5', 1, 'p1', 's1', 888, 88),
                    ('o6', 1, 'p2', 's2', 20, 2),
                    ('o7', 1, 'missing', 's1', 15, 1.5),
                    ('o8', 1, 'missing', 'missing', 80, 8),
                    ('o9', 1, 'p3', 's3', 10, 1);
                INSERT INTO raw.order_reviews (review_id, order_id, review_score)
                VALUES ('r1', 'o1', 1), ('r2', 'o1', 5), ('r3', 'o2', 5),
                       ('r1', 'o6', 4), ('r5', 'o7', 2), ('r6', 'o8', 1),
                       ('r7', 'o9', NULL);
                INSERT INTO raw.order_payments (order_id, payment_value)
                VALUES ('o1', 100), ('o1', 92.5);
                INSERT INTO raw.customers (customer_id, customer_city, customer_state)
                VALUES ('c1', 'zzz', 'SP');
                INSERT INTO raw.sellers (seller_id, seller_city, seller_state)
                VALUES ('s1', 'zzz', 'SP');
                INSERT INTO raw.products (product_id, product_category_name)
                VALUES ('p1', 'zzz');
                INSERT INTO raw.category_translation VALUES ('livros', 'zzz');
            """)

            # Separate dbt connections must see fixtures; repeated builds stay stable.
            run_dbt("build", *dbt_args)
            run_dbt("build", *dbt_args)
            cursor.execute("""
                SELECT table_schema, COUNT(*) FROM information_schema.views
                WHERE table_schema IN ('silver', 'analytics') GROUP BY table_schema
                ORDER BY table_schema
            """)
            assert cursor.fetchall() == [('analytics', 8), ('silver', 6)]
            manifest = json.loads((tmp_path / "target" / "manifest.json").read_text())
            assert len(manifest["sources"]) == 9
            assert set(manifest["nodes"]["model.marketplace_analytics.fact_orders"]["depends_on"]["nodes"]) == {
                "model.marketplace_analytics.orders", "model.marketplace_analytics.order_review_summary",
            }

            cursor.execute("""
                SELECT seller_id, total_orders, total_items_sold, total_revenue,
                       avg_order_value, avg_freight_value, avg_review_score,
                       avg_delivery_delay_days, late_delivery_rate
                FROM analytics.mart_seller_performance ORDER BY seller_id
            """)
            assert cursor.fetchall() == [
                ('s1', 4, 5, Decimal(235), Decimal('58.75'), Decimal('5.88'),
                 Decimal('3.33'), Decimal(0), Decimal('0.5')),
                ('s2', 2, 2, Decimal(45), Decimal('22.50'), Decimal('2.25'),
                 Decimal('3.50'), Decimal(1), Decimal('0.5')),
                ('s3', 1, 1, Decimal(10), Decimal(10), Decimal(1), None, None, None),
            ]
            cursor.execute("""
                SELECT product_category, total_orders, total_items_sold, total_revenue,
                       avg_price, avg_review_score, late_delivery_rate
                FROM analytics.mart_category_performance ORDER BY product_category
            """)
            assert cursor.fetchall() == [
                ('artesanal', 2, 2, Decimal(45), Decimal('22.50'), Decimal('3.50'), Decimal('0.5')),
                ('books', 2, 3, Decimal(180), Decimal(60), Decimal(4), Decimal('0.5')),
                ('unknown', 4, 4, Decimal(145), Decimal('36.25'), Decimal('1.5'), Decimal(1)),
            ]
            cursor.execute("""
                SELECT customer_state, customer_city, total_orders, total_revenue,
                       avg_ticket, avg_review_score
                FROM analytics.mart_geography_sales ORDER BY customer_state
            """)
            assert cursor.fetchall() == [
                ('RJ', 'rio', 1, Decimal(10), Decimal(11), None),
                ('SP', 'sao paulo', 5, Decimal(280), Decimal('61.60'), Decimal('3.50')),
            ]
            cursor.execute("""
                SELECT COUNT(*), MIN(order_total_payment_value)
                FROM analytics.fact_order_items WHERE order_id = 'o1'
            """)
            assert cursor.fetchone() == (3, Decimal('192.5'))

            # No-review orders stay in sales, and an extra review cannot create sales.
            cursor.execute("""
                INSERT INTO raw.order_reviews (review_id, order_id, review_score)
                VALUES ('r8', 'o1', 3)
            """)
            run_dbt("test", *dbt_args)
            cursor.execute("""
                SELECT SUM(total_revenue), SUM(total_items_sold)
                FROM analytics.mart_category_performance
            """)
            assert cursor.fetchone() == (Decimal(370), Decimal(9))

            cursor.execute("""
                INSERT INTO raw.order_items
                SELECT * FROM raw.order_items WHERE order_id = 'o1' AND order_item_id = 1
            """)
            with pytest.raises(subprocess.CalledProcessError):
                run_dbt("build", *dbt_args)
            results = json.loads((tmp_path / "target" / "run_results.json").read_text())["results"]
            assert any(r["status"] == "fail" and "unique_columns_order_items" in r["unique_id"] for r in results)
    finally:
        if owns_schemas:
            with connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA IF EXISTS analytics CASCADE; DROP SCHEMA IF EXISTS silver CASCADE; DROP SCHEMA IF EXISTS raw CASCADE")
        connection.close()
