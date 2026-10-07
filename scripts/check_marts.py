"""Quick script to validate analytics view row counts."""
from sqlalchemy import text

from app.core.database import get_connection

views = [
    "analytics.fact_orders",
    "analytics.fact_order_items",
    "analytics.mart_seller_performance",
    "analytics.mart_category_performance",
    "analytics.mart_geography_sales",
]

with get_connection() as conn:
    for view in views:
        count = conn.execute(text(f"select count(*) from {view}")).scalar()
        print(f"{view}: {count} rows")
