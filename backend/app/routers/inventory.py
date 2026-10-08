from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Product, StockMovement
from ..schemas import CategoryStats, InventoryStats, MovementOut

router = APIRouter(prefix="/api", tags=["inventory"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/stats", response_model=InventoryStats, summary="Dashboard KPIs")
def inventory_stats(db: DbSession):
    is_out = case((Product.quantity <= 0, 1), else_=0)
    is_low = case(((Product.quantity > 0) & (Product.quantity <= Product.reorder_level), 1), else_=0)
    value = Product.quantity * Product.unit_price

    total, units, inventory_value, low, out = db.execute(
        select(
            func.count(Product.id),
            func.coalesce(func.sum(Product.quantity), 0),
            func.coalesce(func.sum(value), 0),
            func.coalesce(func.sum(is_low), 0),
            func.coalesce(func.sum(is_out), 0),
        )
    ).one()

    category_rows = db.execute(
        select(
            Product.category,
            func.count(Product.id),
            func.coalesce(func.sum(Product.quantity), 0),
            func.coalesce(func.sum(value), 0),
        )
        .group_by(Product.category)
        .order_by(Product.category)
    ).all()

    return InventoryStats(
        total_products=total,
        total_units=units,
        inventory_value=round(float(inventory_value), 2),
        in_stock=total - low - out,
        low_stock=low,
        out_of_stock=out,
        categories=[
            CategoryStats(category=name, products=count, units=qty, value=round(float(val), 2))
            for name, count, qty, val in category_rows
        ],
    )


@router.get("/categories", response_model=list[str], summary="Distinct product categories")
def categories(db: DbSession):
    return db.scalars(select(Product.category).distinct().order_by(Product.category)).all()


@router.get("/movements", response_model=list[MovementOut], summary="Most recent stock movements across all products")
def recent_movements(db: DbSession, limit: Annotated[int, Query(ge=1, le=200)] = 20):
    stmt = (
        select(StockMovement).options(joinedload(StockMovement.product)).order_by(StockMovement.id.desc()).limit(limit)
    )
    return db.scalars(stmt).all()
