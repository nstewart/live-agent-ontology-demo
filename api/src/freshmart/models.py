"""FreshMart domain models for flattened views."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class OrderFlat(BaseModel):
    """Flattened order view."""

    order_id: str
    order_number: Optional[str] = None
    order_status: Optional[str] = None
    store_id: Optional[str] = None
    customer_id: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    order_total_amount: Optional[Decimal] = None
    effective_updated_at: Optional[datetime] = None

    # Enriched fields (from search source)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    store_name: Optional[str] = None
    store_zone: Optional[str] = None
    store_address: Optional[str] = None
    assigned_courier_id: Optional[str] = None
    delivery_task_status: Optional[str] = None
    delivery_eta: Optional[str] = None


class StoreInventory(BaseModel):
    """Store inventory view."""

    inventory_id: str
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    stock_level: Optional[int] = None
    replenishment_eta: Optional[str] = None
    effective_updated_at: Optional[datetime] = None

    # Enriched fields
    store_name: Optional[str] = None
    product_name: Optional[str] = None


class CourierSchedule(BaseModel):
    """Courier schedule view."""

    courier_id: str
    courier_name: Optional[str] = None
    home_store_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    courier_status: Optional[str] = None
    tasks: list[dict] = Field(default_factory=list)
    effective_updated_at: Optional[datetime] = None

    # Enriched fields
    home_store_name: Optional[str] = None


class OrderFilter(BaseModel):
    """Filter options for orders."""

    status: Optional[str] = None
    store_id: Optional[str] = None
    customer_id: Optional[str] = None
    window_start_before: Optional[datetime] = None
    window_end_after: Optional[datetime] = None


class StoreInfo(BaseModel):
    """Store information with inventory summary."""

    store_id: str
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_zone: Optional[str] = None
    store_status: Optional[str] = None
    store_capacity_orders_per_hour: Optional[int] = None
    inventory_items: list[StoreInventory] = Field(default_factory=list)


class CourierInfo(BaseModel):
    """Courier information with tasks."""

    courier_id: str
    courier_name: Optional[str] = None
    home_store_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    courier_status: Optional[str] = None
    tasks: list[dict] = Field(default_factory=list)


class CustomerInfo(BaseModel):
    """Customer information."""

    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None


class ProductInfo(BaseModel):
    """Product information."""

    product_id: str
    product_name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = None
    perishable: Optional[bool] = None


class OrderLineFlat(BaseModel):
    """Flattened order line item view."""

    line_id: str
    order_id: Optional[str] = None
    product_id: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    line_amount: Optional[Decimal] = None
    line_sequence: Optional[int] = None
    perishable_flag: Optional[bool] = None
    effective_updated_at: Optional[datetime] = None

    # Enriched fields from product
    product_name: Optional[str] = None
    category: Optional[str] = None


class OrderLineCreate(BaseModel):
    """Request model for creating an order line item."""

    product_id: str = Field(..., description="Product ID (e.g., product:PROD-001)")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    unit_price: Decimal = Field(..., gt=0, description="Unit price at order time")
    line_sequence: int = Field(..., gt=0, description="Display sequence within order")
    perishable_flag: bool = Field(..., description="Perishable flag from product")


class OrderLineUpdate(BaseModel):
    """Request model for updating an order line item."""

    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    unit_price: Optional[Decimal] = Field(None, gt=0, description="New unit price")
    line_sequence: Optional[int] = Field(None, gt=0, description="New sequence")


class OrderLineBatchCreate(BaseModel):
    """Request model for batch creating order line items."""

    line_items: list[OrderLineCreate] = Field(..., min_length=1, max_length=100, description="Line items to create")


class OrderWithLinesFlat(OrderFlat):
    """Order with aggregated line items."""

    line_items: list[dict] = Field(default_factory=list, description="Line items as JSONB array")
    line_item_count: Optional[int] = Field(None, description="Number of line items")
    computed_total: Optional[Decimal] = Field(None, description="Computed total from line items")
    has_perishable_items: Optional[bool] = Field(None, description="Whether order contains perishable items")
    total_weight_kg: Optional[Decimal] = Field(None, description="Total weight in kg")
