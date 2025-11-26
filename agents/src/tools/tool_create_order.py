"""Tool for creating orders."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def create_order(
    customer_id: str,
    store_id: str = "store:BK-01",
    items: list[dict] = None,
    delivery_window_hours: int = 2,
) -> dict:
    """
    Create a new order for a customer in FreshMart.

    IMPORTANT: Orders are ALWAYS created in the CREATED state initially.

    Use this tool after:
    1. Customer has been created (or exists)
    2. Items have been confirmed via search_inventory
    3. Customer has approved the order

    Args:
        customer_id: The customer placing the order (e.g., "customer:abc123")
        store_id: The store fulfilling the order (default: store:BK-01)
        items: List of items with product_id, quantity, and unit_price
               Example: [{"product_id": "product:PROD-001", "quantity": 2, "unit_price": 4.99}]
        delivery_window_hours: Hours from now for delivery window (default: 2)

    Returns:
        Order information including order_id, order_number, and total_amount

    Example:
        create_order(
            customer_id="customer:abc123",
            store_id="store:BK-01",
            items=[
                {"product_id": "product:PROD-001", "quantity": 2, "unit_price": 4.99},
                {"product_id": "product:PROD-002", "quantity": 1, "unit_price": 3.49}
            ]
        )
    """
    settings = get_settings()

    if not items:
        return {
            "success": False,
            "error": "Cannot create order without items",
        }

    # Generate unique order ID and number
    order_uuid = uuid4().hex[:8]
    order_id = f"order:FM-{order_uuid}"
    order_number = f"FM-{order_uuid.upper()}"

    # Calculate total
    total_amount = sum(item["quantity"] * item["unit_price"] for item in items)

    # Calculate delivery window
    now = datetime.utcnow()
    window_start = now + timedelta(hours=1)
    window_end = window_start + timedelta(hours=delivery_window_hours)

    # Build triples for order
    # IMPORTANT: order_status is ALWAYS set to "CREATED" initially
    order_triples = [
        {
            "subject_id": order_id,
            "predicate": "order_number",
            "object_value": order_number,
            "object_type": "string",
        },
        {
            "subject_id": order_id,
            "predicate": "placed_by",
            "object_value": customer_id,
            "object_type": "entity_ref",
        },
        {
            "subject_id": order_id,
            "predicate": "order_store",
            "object_value": store_id,
            "object_type": "entity_ref",
        },
        {
            "subject_id": order_id,
            "predicate": "order_status",
            "object_value": "CREATED",  # Always CREATED initially
            "object_type": "string",
        },
        {
            "subject_id": order_id,
            "predicate": "delivery_window_start",
            "object_value": window_start.isoformat() + "Z",
            "object_type": "timestamp",
        },
        {
            "subject_id": order_id,
            "predicate": "delivery_window_end",
            "object_value": window_end.isoformat() + "Z",
            "object_type": "timestamp",
        },
        {
            "subject_id": order_id,
            "predicate": "order_total_amount",
            "object_value": str(round(total_amount, 2)),
            "object_type": "float",
        },
    ]

    # Add line items as triples
    for idx, item in enumerate(items, start=1):
        line_item_id = f"orderline:{order_uuid}-{idx}"
        line_amount = item["quantity"] * item["unit_price"]

        order_triples.extend(
            [
                {
                    "subject_id": line_item_id,
                    "predicate": "line_of_order",
                    "object_value": order_id,
                    "object_type": "entity_ref",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "line_product",
                    "object_value": item["product_id"],
                    "object_type": "entity_ref",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "quantity",
                    "object_value": str(item["quantity"]),
                    "object_type": "int",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "order_line_unit_price",
                    "object_value": str(item["unit_price"]),
                    "object_type": "float",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "line_amount",
                    "object_value": str(round(line_amount, 2)),
                    "object_type": "float",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "line_sequence",
                    "object_value": str(idx),
                    "object_type": "int",
                },
                {
                    "subject_id": line_item_id,
                    "predicate": "perishable_flag",
                    "object_value": str(item.get("is_perishable", False)).lower(),
                    "object_type": "bool",
                },
            ]
        )

    # Create order via batch API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.agent_api_base}/triples/batch",
                json=order_triples,
                params={"validate": True},
                timeout=15.0,
            )
            response.raise_for_status()

            return {
                "success": True,
                "order_id": order_id,
                "order_number": order_number,
                "order_status": "CREATED",  # Always CREATED
                "customer_id": customer_id,
                "store_id": store_id,
                "total_amount": round(total_amount, 2),
                "item_count": len(items),
                "delivery_window_start": window_start.isoformat() + "Z",
                "delivery_window_end": window_end.isoformat() + "Z",
            }

        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Failed to create order: {str(e)}",
            }
