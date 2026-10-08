from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Product(Base):
    """A stock-keeping unit (SKU) held in the warehouse."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_products_quantity_non_negative"),
        CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    supplier: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StockMovement.id.desc()",
    )

    @property
    def stock_status(self) -> str:
        if self.quantity <= 0:
            return "OUT_OF_STOCK"
        if self.quantity <= self.reorder_level:
            return "LOW_STOCK"
        return "IN_STOCK"

    @property
    def stock_value(self) -> float:
        return round(float(self.unit_price) * self.quantity, 2)


class StockMovement(Base):
    """Audit trail entry: every change to a product's quantity is recorded here."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE", name="fk_stock_movements_product_id"), index=True
    )
    change: Mapped[int] = mapped_column(Integer)
    quantity_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    product: Mapped[Product] = relationship(back_populates="movements")

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def product_sku(self) -> str:
        return self.product.sku
