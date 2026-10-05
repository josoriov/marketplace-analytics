"""Quick script to validate analytics view row counts."""
from app.core.database import get_connection
from sqlalchemy import text

views = [
    "analytics.fact_orders",
    "analytics.fact_order_items",
    "analytics.mart_seller_performance",
    "analytics.mart_category_performance",
    "analytics.mart_geography_sales",
]

with get_connection() as conn:
    for view in views:
        count = conn.execute(text(f"SELECT count(*) FROM {view}")).scalar()
        print(f"{view}: {count} rows")
