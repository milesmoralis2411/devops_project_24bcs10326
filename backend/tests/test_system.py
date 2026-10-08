def test_health_is_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_ready_returns_503_when_database_is_down(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    def broken_execute(*_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(Session, "execute", broken_execute)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


def test_root_describes_service(client):
    body = client.get("/").json()
    assert body["service"] == "StockPilot API"
    assert body["docs"] == "/docs"


def test_info_exposes_build_metadata(client):
    body = client.get("/api/info").json()
    assert set(body) == {"service", "version", "environment", "git_sha"}


def test_openapi_lists_inventory_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/products" in paths
    assert "/api/products/{product_id}/adjustments" in paths
    assert "/api/stats" in paths


def test_metrics_endpoint_exposes_prometheus_format(client, make_product):
    make_product(quantity=5, reorder_level=10)
    client.get("/api/products")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert "stockpilot_products " in body
    assert "stockpilot_products_low_stock 1.0" in body
    assert 'stockpilot_stock_movements_total{reason="INITIAL"}' in body
