import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection


class SellerPerformance(BaseModel):
    seller_id: str
    seller_city: str | None
    seller_state: str | None
    total_orders: int
    total_items_sold: int
    total_revenue: Decimal
    avg_order_value: Decimal | None
    avg_freight_value: Decimal | None
    avg_review_score: Decimal | None
    avg_delivery_delay_days: Decimal | None
    late_delivery_rate: Decimal | None


class CategoryPerformance(BaseModel):
    product_category: str
    total_orders: int
    total_items_sold: int
    total_revenue: Decimal
    avg_price: Decimal | None
    avg_review_score: Decimal | None
    late_delivery_rate: Decimal | None


class StatePerformance(BaseModel):
    customer_state: str | None
    total_orders: int
    total_revenue: Decimal
    avg_ticket: Decimal | None
    avg_review_score: Decimal | None


class APIError(BaseModel):
    detail: str


UNAVAILABLE: dict[int | str, dict[str, Any]] = {
    503: {"model": APIError, "description": "Database analytics unavailable"},
}
ListLimit = Annotated[int, Query(ge=1, le=100)]

app = FastAPI(title="Marketplace Seller Analytics API")


def query(sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            result = connection.execute(text(sql), parameters or {})
            return [dict(row) for row in result.mappings()]
    except (SQLAlchemyError, ValueError):
        logging.getLogger(__name__).exception("Database analytics query failed")
        raise HTTPException(status_code=503, detail="Database analytics unavailable") from None


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Application liveness, independent of PostgreSQL."""
    return {"status": "ok"}


@app.get("/ready", responses=UNAVAILABLE)
def readiness() -> dict[str, str]:
    """Check database connectivity and access to every business query source."""
    query("""
        select 1
        from analytics.mart_seller_performance,
             analytics.mart_category_performance,
             analytics.dim_customers,
             analytics.fact_orders,
             silver.order_item_summary
        limit 0
    """)
    return {"status": "ok"}


@app.get("/sellers/top", responses=UNAVAILABLE)
def top_sellers(limit: ListLimit = 10) -> list[SellerPerformance]:
    """Rank sellers by delivered item revenue, breaking ties by seller ID."""
    return [SellerPerformance(**row) for row in query("""
        select * from analytics.mart_seller_performance
        order by total_revenue desc, seller_id
        limit :limit
    """, {"limit": limit})]


@app.get("/sellers/{seller_id}/performance", responses={
    **UNAVAILABLE, 404: {"model": APIError, "description": "No delivered sales for seller"},
})
def seller_performance(
    seller_id: Annotated[str, Path(min_length=1, max_length=32)],
) -> SellerPerformance:
    """Return a seller's delivered-sales metrics; absent performance returns 404."""
    rows = query("""
        select * from analytics.mart_seller_performance
        where seller_id = :seller_id
    """, {"seller_id": seller_id})
    if not rows:
        raise HTTPException(status_code=404, detail="No delivered sales found for seller")
    return SellerPerformance(**rows[0])


@app.get("/categories/performance", responses=UNAVAILABLE)
def category_performance(limit: ListLimit = 100) -> list[CategoryPerformance]:
    """Rank categories by delivered item revenue, breaking ties by category."""
    return [CategoryPerformance(**row) for row in query("""
        select * from analytics.mart_category_performance
        order by total_revenue desc, product_category
        limit :limit
    """, {"limit": limit})]


@app.get("/geography/states", responses=UNAVAILABLE)
def state_performance(limit: ListLimit = 100) -> list[StatePerformance]:
    """Aggregate delivered orders directly, weighting tickets and reviews by order."""
    return [StatePerformance(**row) for row in query("""
        select
            c.customer_state,
            count(*) as total_orders,
            coalesce(sum(ot.revenue), 0) as total_revenue,
            round(avg(ot.revenue + ot.freight), 2) as avg_ticket,
            round(avg(fo.avg_review_score), 2) as avg_review_score
        from analytics.dim_customers as c
        inner join analytics.fact_orders as fo on c.customer_id = fo.customer_id
        inner join silver.order_item_summary as ot on fo.order_id = ot.order_id
        where fo.is_delivered
        group by c.customer_state
        order by total_revenue desc, c.customer_state nulls last
        limit :limit
    """, {"limit": limit})]
