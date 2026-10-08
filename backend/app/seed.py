"""Demo data so a fresh environment shows a populated dashboard.

Only runs when SEED_DEMO_DATA=true and the products table is empty, so it never
touches real data and is safe to run on every container start.
"""

import logging
from datetime import timedelta

from sqlalchemy import func, select, text

from .db import SessionLocal
from .models import Product, StockMovement, utcnow

log = logging.getLogger("stockpilot.seed")
SEED_LOCK_ID = 727_002

# sku, name, category, supplier, location, reorder_level, unit_price, movement history
DEMO_PRODUCTS = [
    (
        "ELEC-USBC-1M",
        "USB-C charging cable (1 m)",
        "Electronics",
        "Volt Distributors",
        "A-01-02",
        40,
        249.00,
        [(150, "INITIAL"), (-62, "SALE"), (-14, "SALE")],
    ),
    (
        "ELEC-MOUSE-WL",
        "Wireless optical mouse",
        "Electronics",
        "Volt Distributors",
        "A-01-05",
        25,
        699.00,
        [(60, "INITIAL"), (-41, "SALE")],
    ),
    (
        "ELEC-HDMI-2M",
        "HDMI 2.1 cable (2 m)",
        "Electronics",
        "Volt Distributors",
        "A-02-01",
        20,
        449.00,
        [(30, "INITIAL"), (-30, "SALE")],
    ),
    (
        "ELEC-PB-20K",
        "20,000 mAh power bank",
        "Electronics",
        "Ampere Supply Co.",
        "A-02-04",
        15,
        1899.00,
        [(45, "INITIAL"), (-12, "SALE"), (2, "RETURN")],
    ),
    (
        "OFF-A4-500",
        "A4 copier paper (500 sheets)",
        "Office Supplies",
        "PaperTrail Traders",
        "B-01-01",
        50,
        329.00,
        [(300, "INITIAL"), (-120, "SALE"), (100, "RESTOCK")],
    ),
    (
        "OFF-PEN-BL12",
        "Blue gel pens (pack of 12)",
        "Office Supplies",
        "PaperTrail Traders",
        "B-01-04",
        30,
        180.00,
        [(80, "INITIAL"), (-58, "SALE")],
    ),
    (
        "OFF-STAPLER",
        "Heavy-duty stapler",
        "Office Supplies",
        "PaperTrail Traders",
        "B-02-02",
        10,
        540.00,
        [(25, "INITIAL"), (-3, "DAMAGE")],
    ),
    (
        "PKG-BOX-M",
        "Corrugated shipping box (medium)",
        "Packaging",
        "BoxCraft Industries",
        "C-01-01",
        200,
        38.50,
        [(1200, "INITIAL"), (-950, "SALE")],
    ),
    (
        "PKG-TAPE-48",
        "Packing tape 48 mm x 65 m",
        "Packaging",
        "BoxCraft Industries",
        "C-01-03",
        60,
        95.00,
        [(240, "INITIAL"), (-90, "SALE")],
    ),
    (
        "PKG-BUBBLE",
        "Bubble wrap roll (50 m)",
        "Packaging",
        "BoxCraft Industries",
        "C-02-01",
        12,
        799.00,
        [(10, "INITIAL"), (-10, "SALE")],
    ),
    (
        "FUR-CHAIR-ERG",
        "Ergonomic office chair",
        "Furniture",
        "Comfort Works",
        "D-01-01",
        5,
        8999.00,
        [(12, "INITIAL"), (-4, "SALE")],
    ),
    (
        "SAFE-GLOVE-L",
        "Cut-resistant gloves (L)",
        "Safety",
        "SafeHands Ltd.",
        "E-01-02",
        40,
        210.00,
        [(90, "INITIAL"), (-55, "SALE"), (-4, "DAMAGE")],
    ),
    (
        "SAFE-HELMET",
        "Safety helmet with chin strap",
        "Safety",
        "SafeHands Ltd.",
        "E-01-05",
        15,
        650.00,
        [(35, "INITIAL"), (-6, "SALE")],
    ),
]


def seed_demo_data() -> int:
    with SessionLocal() as session:
        if session.get_bind().dialect.name == "postgresql":
            # Transaction-scoped lock: replicas starting together won't seed twice.
            session.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": SEED_LOCK_ID})
        if session.scalar(select(func.count(Product.id))):
            log.info("products already present, skipping demo seed")
            return 0

        start = utcnow() - timedelta(days=6)
        step = 0
        for sku, name, category, supplier, location, reorder, price, history in DEMO_PRODUCTS:
            product = Product(
                sku=sku,
                name=name,
                category=category,
                supplier=supplier,
                location=location,
                reorder_level=reorder,
                unit_price=price,
                quantity=0,
                description=f"{name} supplied by {supplier}.",
            )
            for change, reason in history:
                product.quantity += change
                step += 1
                product.movements.append(
                    StockMovement(
                        change=change,
                        quantity_after=product.quantity,
                        reason=reason,
                        note="Opening stock" if reason == "INITIAL" else "Demo data",
                        created_at=start + timedelta(hours=3 * step),
                    )
                )
            session.add(product)
        session.commit()
        log.info("seeded %d demo products", len(DEMO_PRODUCTS))
        return len(DEMO_PRODUCTS)
