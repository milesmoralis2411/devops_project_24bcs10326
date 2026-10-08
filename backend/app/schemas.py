from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

StockStatus = Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"]
# INITIAL is written automatically when a product is created with opening stock.
MovementReason = Literal["INITIAL", "RESTOCK", "SALE", "RETURN", "DAMAGE", "ADJUSTMENT"]
AdjustmentReason = Literal["RESTOCK", "SALE", "RETURN", "DAMAGE", "ADJUSTMENT"]

INBOUND_REASONS = {"RESTOCK", "RETURN"}
OUTBOUND_REASONS = {"SALE", "DAMAGE"}

SKU_PATTERN = r"^[A-Z0-9][A-Z0-9-]{2,39}$"


class _ProductFields(BaseModel):
    @field_validator("sku", mode="before", check_fields=False)
    @classmethod
    def normalise_sku(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name", "category", "supplier", "location", "description", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("unit_price", check_fields=False)
    @classmethod
    def round_price(cls, value):
        return round(value, 2) if value is not None else value


class ProductCreate(_ProductFields):
    model_config = ConfigDict(extra="forbid")

    sku: str = Field(pattern=SKU_PATTERN, examples=["ELEC-USB-C-001"])
    name: str = Field(min_length=1, max_length=160, examples=["USB-C charging cable (1m)"])
    category: str = Field(min_length=1, max_length=60, examples=["Electronics"])
    description: str = Field(default="", max_length=2000)
    supplier: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=60, examples=["A-01-03"])
    quantity: int = Field(default=0, ge=0, le=1_000_000, description="Opening stock level")
    reorder_level: int = Field(default=10, ge=0, le=1_000_000)
    unit_price: float = Field(default=0, ge=0, le=10_000_000)


class ProductUpdate(_ProductFields):
    """Partial update. Quantity is deliberately absent: stock only changes through
    stock adjustments so that every change is captured in the movement audit trail."""

    model_config = ConfigDict(extra="forbid")

    sku: str | None = Field(default=None, pattern=SKU_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    supplier: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=60)
    reorder_level: int | None = Field(default=None, ge=0, le=1_000_000)
    unit_price: float | None = Field(default=None, ge=0, le=10_000_000)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str
    description: str
    supplier: str
    location: str
    quantity: int
    reorder_level: int
    unit_price: float
    stock_status: StockStatus
    stock_value: float
    created_at: datetime
    updated_at: datetime


class StockAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change: int = Field(ge=-1_000_000, le=1_000_000, description="Positive adds stock, negative removes it")
    reason: AdjustmentReason
    note: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def check_direction(self):
        if self.change == 0:
            raise ValueError("change must not be zero")
        if self.reason in INBOUND_REASONS and self.change < 0:
            raise ValueError(f"{self.reason} must increase stock (use a positive change)")
        if self.reason in OUTBOUND_REASONS and self.change > 0:
            raise ValueError(f"{self.reason} must decrease stock (use a negative change)")
        return self


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_sku: str
    change: int
    quantity_after: int
    reason: MovementReason
    note: str
    created_at: datetime


class AdjustmentResult(BaseModel):
    product: ProductOut
    movement: MovementOut


class CategoryStats(BaseModel):
    category: str
    products: int
    units: int
    value: float


class InventoryStats(BaseModel):
    total_products: int
    total_units: int
    inventory_value: float
    in_stock: int
    low_stock: int
    out_of_stock: int
    categories: list[CategoryStats]


class AppInfo(BaseModel):
    service: str
    version: str
    environment: str
    git_sha: str
