from app.seed import DEMO_PRODUCTS, seed_demo_data


def test_seed_populates_empty_database_with_consistent_history(client):
    assert seed_demo_data() == len(DEMO_PRODUCTS)

    products = client.get("/api/products").json()
    assert len(products) == len(DEMO_PRODUCTS)
    for product in products:
        history = client.get(f"/api/products/{product['id']}/movements").json()
        # The newest movement's running total must equal the stored quantity.
        assert history[0]["quantity_after"] == product["quantity"]
        assert history[-1]["reason"] == "INITIAL"

    stats = client.get("/api/stats").json()
    assert stats["low_stock"] > 0 and stats["out_of_stock"] > 0  # demo shows reorder alerts


def test_seed_is_idempotent(client, make_product):
    make_product()
    assert seed_demo_data() == 0
    assert len(client.get("/api/products").json()) == 1
