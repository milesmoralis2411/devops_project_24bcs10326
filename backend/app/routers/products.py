from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..metrics import record_movement
from ..models import Product, StockMovement
from ..schemas import (
    AdjustmentResult,
    MovementOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StockAdjustment,
    StockStatus,
)

router = APIRouter(prefix="/api/products", tags=["products"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_product_or_404(db: Session, product_id: int, *, for_update: bool = False) -> Product:
    product = db.get(Product, product_id, with_for_update=for_update)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _commit_or_conflict(db: Session, sku: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"A product with SKU '{sku}' already exists"
        ) from None


@router.get("", response_model=list[ProductOut], summary="List products with optional filters")
def list_products(
    db: DbSession,
    search: Annotated[str | None, Query(max_length=100, description="Matches SKU, name or supplier")] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    stock_status: Annotated[StockStatus | None, Query(alias="status")] = None,
):
    stmt = select(Product)
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.sku).like(pattern),
                func.lower(Product.name).like(pattern),
                func.lower(Product.supplier).like(pattern),
            )
        )
    if category:
        stmt = stmt.where(Product.category == category)
    if stock_status == "OUT_OF_STOCK":
        stmt = stmt.where(Product.quantity <= 0)
    elif stock_status == "LOW_STOCK":
        stmt = stmt.where(Product.quantity > 0, Product.quantity <= Product.reorder_level)
    elif stock_status == "IN_STOCK":
        stmt = stmt.where(Product.quantity > Product.reorder_level)
    return db.scalars(stmt.order_by(Product.name, Product.id)).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DbSession):
    return _get_product_or_404(db, product_id)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession):
    product = Product(**payload.model_dump())
    db.add(product)
    if payload.quantity:
        product.movements.append(
            StockMovement(
                change=payload.quantity, quantity_after=payload.quantity, reason="INITIAL", note="Opening stock"
            )
        )
    _commit_or_conflict(db, payload.sku)
    if payload.quantity:
        record_movement("INITIAL", payload.quantity)
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: DbSession):
    product = _get_product_or_404(db, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} cannot be null")
        setattr(product, field, value)
    _commit_or_conflict(db, product.sku)
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession):
    product = _get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{product_id}/adjustments",
    response_model=AdjustmentResult,
    status_code=status.HTTP_201_CREATED,
    summary="Receive, sell or write off stock",
)
def adjust_stock(product_id: int, payload: StockAdjustment, db: DbSession):
    # Row lock (SELECT ... FOR UPDATE on PostgreSQL) so two concurrent sales
    # cannot both read the same quantity and oversell.
    product = _get_product_or_404(db, product_id, for_update=True)
    new_quantity = product.quantity + payload.change
    if new_quantity < 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient stock: {product.quantity} units available, tried to remove {-payload.change}",
        )
    product.quantity = new_quantity
    movement = StockMovement(
        product=product, change=payload.change, quantity_after=new_quantity, reason=payload.reason, note=payload.note
    )
    db.add(movement)
    db.commit()
    record_movement(payload.reason, payload.change)
    db.refresh(product)
    return AdjustmentResult(product=ProductOut.model_validate(product), movement=MovementOut.model_validate(movement))


@router.get("/{product_id}/movements", response_model=list[MovementOut], summary="Stock history for one product")
def product_movements(product_id: int, db: DbSession, limit: Annotated[int, Query(ge=1, le=500)] = 100):
    _get_product_or_404(db, product_id)
    stmt = (
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.id.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()
