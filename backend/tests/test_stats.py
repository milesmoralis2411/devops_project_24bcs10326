import pytest


def test_stats_on_empty_inventory(client):
    assert client.get("/api/stats").json() == {
        "total_products": 0,
        "total_units": 0,
        "inventory_value": 0.0,
        "in_stock": 0,
        "low_stock": 0,
        "out_of_stock": 0,
        "categories": [],
    }


def test_stats_aggregate_kpis_and_categories(client, make_product):
    make_product(category="Electronics", quantity=100, reorder_level=10, unit_price=2.5)  # in stock, 250
    make_product(category="Electronics", quantity=4, reorder_level=10, unit_price=100)  # low, 400
    make_product(category="Safety", quantity=0, reorder_level=5, unit_price=999)  # out, 0

    stats = client.get("/api/stats").json()
    assert stats["total_products"] == 3
    assert stats["total_units"] == 104
    assert stats["inventory_value"] == pytest.approx(650.0)
    assert (stats["in_stock"], stats["low_stock"], stats["out_of_stock"]) == (1, 1, 1)
    assert stats["categories"] == [
        {"category": "Electronics", "products": 2, "units": 104, "value": 650.0},
        {"category": "Safety", "products": 1, "units": 0, "value": 0.0},
    ]


def test_stats_reflect_stock_adjustments(client, make_product):
    product = make_product(quantity=10, reorder_level=5, unit_price=10)
    client.post(f"/api/products/{product['id']}/adjustments", json={"change": -10, "reason": "SALE"})
    stats = client.get("/api/stats").json()
    assert stats["out_of_stock"] == 1
    assert stats["inventory_value"] == 0


def test_categories_are_distinct_and_sorted(client, make_product):
    make_product(category="Safety")
    make_product(category="Electronics")
    make_product(category="Safety")
    assert client.get("/api/categories").json() == ["Electronics", "Safety"]
