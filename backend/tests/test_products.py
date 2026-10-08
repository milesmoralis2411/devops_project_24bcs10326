import pytest


def test_create_product_returns_201_and_computed_fields(client):
    response = client.post(
        "/api/products",
        json={
            "sku": "elec-usbc-1m",
            "name": "  USB-C cable  ",
            "category": "Electronics",
            "quantity": 120,
            "reorder_level": 40,
            "unit_price": 249.499,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["sku"] == "ELEC-USBC-1M"  # normalised to upper case
    assert body["name"] == "USB-C cable"  # whitespace trimmed
    assert body["unit_price"] == 249.5
    assert body["stock_status"] == "IN_STOCK"
    assert body["stock_value"] == pytest.approx(120 * 249.5)


def test_create_product_records_opening_stock_movement(client, make_product):
    product = make_product(quantity=25)
    history = client.get(f"/api/products/{product['id']}/movements").json()
    assert len(history) == 1
    assert history[0]["reason"] == "INITIAL"
    assert history[0]["change"] == 25
    assert history[0]["quantity_after"] == 25


def test_create_product_with_duplicate_sku_returns_409(client, make_product):
    make_product(sku="DUP-001")
    response = client.post("/api/products", json={"sku": "dup-001", "name": "Copy", "category": "Misc"})
    assert response.status_code == 409
    assert "DUP-001" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"sku": "OK-001", "name": "", "category": "Misc"},  # empty name
        {"sku": "x", "name": "Bad SKU", "category": "Misc"},  # SKU too short
        {"sku": "BAD SKU!", "name": "Bad SKU", "category": "Misc"},  # illegal characters
        {"sku": "NEG-001", "name": "Negative", "category": "Misc", "quantity": -1},
        {"sku": "NEG-002", "name": "Negative", "category": "Misc", "unit_price": -5},
        {"sku": "EXTRA-01", "name": "Extra", "category": "Misc", "colour": "red"},  # unknown field
    ],
)
def test_create_product_rejects_invalid_payloads(client, payload):
    assert client.post("/api/products", json=payload).status_code == 422


def test_list_products_sorted_by_name(client, make_product):
    make_product(name="Zebra stapler")
    make_product(name="Apple keyboard")
    names = [p["name"] for p in client.get("/api/products").json()]
    assert names == ["Apple keyboard", "Zebra stapler"]


def test_list_products_search_matches_sku_name_and_supplier(client, make_product):
    make_product(sku="CHAIR-01", name="Office chair", supplier="Comfort Works")
    make_product(sku="DESK-01", name="Standing desk", supplier="Ergo Ltd")

    assert [p["sku"] for p in client.get("/api/products?search=chair").json()] == ["CHAIR-01"]
    assert [p["sku"] for p in client.get("/api/products?search=desk-0").json()] == ["DESK-01"]
    assert [p["sku"] for p in client.get("/api/products?search=ERGO").json()] == ["DESK-01"]


def test_list_products_filters_by_category_and_status(client, make_product):
    make_product(sku="IN-01", category="Safety", quantity=100, reorder_level=10)
    make_product(sku="LOW-01", category="Safety", quantity=5, reorder_level=10)
    make_product(sku="OUT-01", category="Packaging", quantity=0, reorder_level=10)

    assert [p["sku"] for p in client.get("/api/products?category=Packaging").json()] == ["OUT-01"]
    assert [p["sku"] for p in client.get("/api/products?status=LOW_STOCK").json()] == ["LOW-01"]
    assert [p["sku"] for p in client.get("/api/products?status=OUT_OF_STOCK").json()] == ["OUT-01"]
    assert [p["sku"] for p in client.get("/api/products?status=IN_STOCK").json()] == ["IN-01"]
    assert client.get("/api/products?status=BOGUS").status_code == 422


def test_get_product_by_id(client, make_product):
    product = make_product()
    response = client.get(f"/api/products/{product['id']}")
    assert response.status_code == 200
    assert response.json()["sku"] == product["sku"]


def test_get_missing_product_returns_404(client):
    response = client.get("/api/products/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_product_changes_only_supplied_fields(client, make_product):
    product = make_product(name="Old name", unit_price=10)
    response = client.put(f"/api/products/{product['id']}", json={"name": "New name", "reorder_level": 99})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New name"
    assert body["reorder_level"] == 99
    assert body["unit_price"] == 10  # untouched
    assert body["stock_status"] == "LOW_STOCK"  # 50 units <= new reorder level of 99


def test_update_product_cannot_change_quantity_directly(client, make_product):
    product = make_product()
    response = client.put(f"/api/products/{product['id']}", json={"quantity": 1})
    assert response.status_code == 422


def test_update_product_rejects_null_fields(client, make_product):
    product = make_product()
    response = client.put(f"/api/products/{product['id']}", json={"name": None})
    assert response.status_code == 422


def test_update_product_to_existing_sku_returns_409(client, make_product):
    make_product(sku="TAKEN-01")
    other = make_product(sku="FREE-01")
    response = client.put(f"/api/products/{other['id']}", json={"sku": "TAKEN-01"})
    assert response.status_code == 409


def test_update_missing_product_returns_404(client):
    assert client.put("/api/products/9999", json={"name": "Ghost"}).status_code == 404


def test_delete_product_removes_it_and_its_history(client, make_product):
    product = make_product(quantity=10)
    response = client.delete(f"/api/products/{product['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/products/{product['id']}").status_code == 404
    assert client.get("/api/movements").json() == []


def test_delete_missing_product_returns_404(client):
    assert client.delete("/api/products/9999").status_code == 404
