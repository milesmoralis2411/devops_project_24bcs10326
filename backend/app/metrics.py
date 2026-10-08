"""Business metrics exported on /metrics next to the HTTP metrics from the instrumentator.

HTTP metrics answer "is the service healthy?"; these answer "is the warehouse healthy?"
and give Grafana something domain-specific to chart.
"""

import logging

from prometheus_client import REGISTRY, Counter
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import case, func, select

from . import db
from .models import Product

log = logging.getLogger(__name__)

STOCK_MOVEMENTS = Counter(
    "stockpilot_stock_movements_total",
    "Stock movements recorded, by reason",
    ["reason"],
)
STOCK_UNITS_MOVED = Counter(
    "stockpilot_stock_units_moved_total",
    "Units moved in or out of the warehouse",
    ["direction"],
)


def record_movement(reason: str, change: int) -> None:
    STOCK_MOVEMENTS.labels(reason=reason).inc()
    STOCK_UNITS_MOVED.labels(direction="in" if change > 0 else "out").inc(abs(change))


class InventoryCollector(Collector):
    """Reads inventory gauges from the database at scrape time, so every replica
    reports the current truth rather than a value cached in its own memory."""

    def collect(self):
        stmt = select(
            func.count(Product.id),
            func.coalesce(func.sum(Product.quantity * Product.unit_price), 0),
            func.coalesce(func.sum(case((Product.quantity <= 0, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case(((Product.quantity > 0) & (Product.quantity <= Product.reorder_level), 1), else_=0)),
                0,
            ),
        )
        try:
            with db.SessionLocal() as session:
                total, value, out_of_stock, low_stock = session.execute(stmt).one()
        except Exception as exc:  # never let a DB hiccup break the whole /metrics page
            log.warning("inventory metrics unavailable: %s", exc.__class__.__name__)
            return

        yield GaugeMetricFamily("stockpilot_products", "Products in the catalogue", value=total)
        yield GaugeMetricFamily("stockpilot_products_low_stock", "Products at or below reorder level", value=low_stock)
        yield GaugeMetricFamily("stockpilot_products_out_of_stock", "Products with zero units", value=out_of_stock)
        yield GaugeMetricFamily("stockpilot_inventory_value", "Total stock value", value=float(value))


_collector: InventoryCollector | None = None


def register_inventory_collector() -> None:
    global _collector
    if _collector is None:
        _collector = InventoryCollector()
        REGISTRY.register(_collector)
