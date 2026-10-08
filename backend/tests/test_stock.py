import pytest


def adjust(client, product_id, change, reason, note=""):
    return client.post(
        f"/api/products/{product_id}/adjustments", json={"change": change, "reason": reason, "note": note}
    )


def test_restock_increases_quantity_and_records_movement(client, make_product):
    product = make_product(quantity=10)
    response = adjust(client, product["id"], 40, "RESTOCK", "PO-1001")
    assert response.status_code == 201
    body = response.json()
    assert body["product"]["quantity"] == 50
    assert body["movement"]["change"] == 40
    assert body["movement"]["quantity_after"] == 50
    assert body["movement"]["note"] == "PO-1001"
    assert body["movement"]["product_sku"] == product["sku"]


def test_sale_decreases_quantity_and_updates_status(client, make_product):
    product = make_product(quantity=12, reorder_level=10)
    body = adjust(client, product["id"], -3, "SALE").json()
    assert body["product"]["quantity"] == 9
    assert body["product"]["stock_status"] == "LOW_STOCK"

    body = adjust(client, product["id"], -9, "SALE").json()
    assert body["product"]["quantity"] == 0
    assert body["product"]["stock_status"] == "OUT_OF_STOCK"


def test_cannot_remove_more_stock_than_available(client, make_product):
    product = make_product(quantity=5)
    response = adjust(client, product["id"], -6, "SALE")
    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["detail"]
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 5


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (0, "ADJUSTMENT"),  # no-op change
        (-5, "RESTOCK"),  # restock must add stock
        (5, "SALE"),  # sale must remove stock
        (5, "DAMAGE"),  # write-off must remove stock
        (-5, "RETURN"),  # return must add stock
        (5, "INITIAL"),  # system-only reason
        (5, "THEFT"),  # unknown reason
    ],
)
def test_adjustment_validation(client, make_product, change, reason):
    product = make_product()
    assert adjust(client, product["id"], change, reason).status_code == 422


def test_manual_adjustment_can_go_either_way(client, make_product):
    product = make_product(quantity=20)
    assert adjust(client, product["id"], -2, "ADJUSTMENT", "cycle count").json()["product"]["quantity"] == 18
    assert adjust(client, product["id"], 4, "ADJUSTMENT", "found in aisle").json()["product"]["quantity"] == 22


def test_adjust_missing_product_returns_404(client):
    assert adjust(client, 9999, 1, "RESTOCK").status_code == 404


def test_product_movement_history_is_newest_first(client, make_product):
    product = make_product(quantity=10)
    adjust(client, product["id"], 5, "RESTOCK")
    adjust(client, product["id"], -2, "SALE")

    history = client.get(f"/api/products/{product['id']}/movements").json()
    assert [m["reason"] for m in history] == ["SALE", "RESTOCK", "INITIAL"]
    assert [m["quantity_after"] for m in history] == [13, 15, 10]


def test_recent_movements_across_products_respects_limit(client, make_product):
    first = make_product(quantity=1)
    second = make_product(quantity=2)
    adjust(client, first["id"], 3, "RESTOCK")

    recent = client.get("/api/movements?limit=2").json()
    assert len(recent) == 2
    assert recent[0]["product_id"] == first["id"] and recent[0]["reason"] == "RESTOCK"
    assert recent[1]["product_id"] == second["id"] and recent[1]["reason"] == "INITIAL"
    assert client.get("/api/movements?limit=0").status_code == 422


def test_movements_for_missing_product_returns_404(client):
    assert client.get("/api/products/9999/movements").status_code == 404
