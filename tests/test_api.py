"""HTTP contracts run without PostgreSQL; SQL metrics are checked in test_marts."""

from decimal import Decimal
from unittest.mock import MagicMock
from urllib.parse import quote

from sqlalchemy.exc import OperationalError

from app import main


def test_business_api_http_contract(http_get, monkeypatch):
    connection = MagicMock()
    monkeypatch.setattr(main, "get_connection", lambda: connection)
    execute = connection.__enter__.return_value.execute
    rows = execute.return_value.mappings.return_value
    seller = {
        "seller_id": "s1", "seller_city": None, "seller_state": "SP",
        "total_orders": 1, "total_items_sold": 2,
        "total_revenue": Decimal("1234567890123456.78"),
        "avg_order_value": Decimal("12.50"), "avg_freight_value": None,
        "avg_review_score": None, "avg_delivery_delay_days": Decimal("-1.25"),
        "late_delivery_rate": Decimal("0.5000"),
    }
    rows.__iter__.side_effect = lambda: iter([seller])
    expected = {key: str(value) if isinstance(value, Decimal) else value for key, value in seller.items()}
    assert http_get("/health") == (200, {"status": "ok"})
    assert http_get("/ready") == (200, {"status": "ok"})
    assert http_get("/sellers/top") == (200, [expected])
    assert execute.call_args.args[1] == {"limit": 10}
    assert http_get("/sellers/s1/performance") == (200, expected)
    assert execute.call_args.args[1] == {"seller_id": "s1"}
    assert ":seller_id" in str(execute.call_args.args[0])

    for path, data in [
        ("/categories/performance", {
            "product_category": "books", "total_orders": 1, "total_items_sold": 2,
            "total_revenue": Decimal("12.50"), "avg_price": Decimal("6.25"),
            "avg_review_score": None, "late_delivery_rate": None,
        }),
        ("/geography/states", {
            "customer_state": None, "total_orders": 1, "total_revenue": Decimal("12.50"),
            "avg_ticket": Decimal("15.00"), "avg_review_score": None,
        }),
    ]:
        rows.__iter__.side_effect = lambda data=data: iter([data])
        assert http_get(path) == (
            200, [{key: str(value) if isinstance(value, Decimal) else value for key, value in data.items()}],
        )
        assert execute.call_args.args[1] == {"limit": 100}

    rows.__iter__.side_effect = lambda: iter([])
    for path in ("/sellers/top", "/categories/performance", "/geography/states"):
        assert http_get(path) == (200, [])
        for limit in (1, 100):
            assert http_get(f"{path}?limit={limit}") == (200, [])
            assert execute.call_args.args[1] == {"limit": limit}
            assert ":limit" in str(execute.call_args.args[0])
        for limit in (0, -1, 101, "abc", "1.5"):
            execute.reset_mock()
            assert http_get(f"{path}?limit={limit}")[0] == 422
            execute.assert_not_called()
    assert http_get("/sellers/missing/performance") == (
        404, {"detail": "No delivered sales found for seller"},
    )
    injection = "' OR 1=1 --"
    assert http_get(f"/sellers/{quote(injection, safe='')}/performance")[0] == 404
    assert execute.call_args.args[1] == {"seller_id": injection}
    assert injection not in str(execute.call_args.args[0])
    assert http_get(f"/sellers/{'x' * 33}/performance")[0] == 422

    status, schema = http_get("/openapi.json")
    assert status == 200
    for path, model in [
        ("/sellers/top", "SellerPerformance"),
        ("/categories/performance", "CategoryPerformance"),
        ("/geography/states", "StatePerformance"),
    ]:
        route = schema["paths"][path]["get"]
        limit_schema = route["parameters"][0]["schema"]
        assert (limit_schema["minimum"], limit_schema["maximum"]) == (1, 100)
        response = route["responses"]["200"]["content"]["application/json"]["schema"]
        assert response["items"]["$ref"].endswith(f"/{model}")
        assert "503" in route["responses"]
    fields = schema["components"]["schemas"]["SellerPerformance"]["properties"]
    assert fields["total_revenue"]["type"] == "string"
    assert {choice["type"] for choice in fields["avg_review_score"]["anyOf"]} == {"string", "null"}
    assert "404" in schema["paths"]["/sellers/{seller_id}/performance"]["get"]["responses"]
    assert "503" in schema["paths"]["/ready"]["get"]["responses"]

    for error in (OperationalError("private SQL", {}, Exception("private credentials")), ValueError("private config")):
        execute.side_effect = error
        for path in ("/ready", "/sellers/top", "/sellers/s1/performance", "/categories/performance", "/geography/states"):
            assert http_get(path) == (503, {"detail": "Database analytics unavailable"})
        assert http_get("/health") == (200, {"status": "ok"})
