"""Tool for managing order line items (add/update/delete)."""

from typing import Optional

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def manage_order_lines(
    order_id: str,
    action: str,
    line_id: Optional[str] = None,
    product_id: Optional[str] = None,
    quantity: Optional[int] = None,
    unit_price: Optional[float] = None,
) -> dict:
    """
    Manage order line items - add, update, or delete products from an order.

    Use this tool to modify an existing order's line items. The order's total
    amount will be automatically recalculated by the materialized views.

    Args:
        order_id: The order ID (e.g., "order:FM-1001")
        action: The action to perform - "add", "update", or "delete"
        line_id: The line item ID (required for "update" and "delete" actions)
        product_id: The product ID (required for "add" action)
        quantity: The quantity (required for "add" and "update" actions)
        unit_price: The unit price (required for "add" action)

    Returns:
        Success status or error details

    Examples:
        # Add a new item
        manage_order_lines(
            order_id="order:FM-1001",
            action="add",
            product_id="product:MILK-001",
            quantity=2,
            unit_price=3.99
        )

        # Update quantity
        manage_order_lines(
            order_id="order:FM-1001",
            action="update",
            line_id="orderline:FM-1001-001",
            quantity=5
        )

        # Delete an item
        manage_order_lines(
            order_id="order:FM-1001",
            action="delete",
            line_id="orderline:FM-1001-001"
        )
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            if action == "delete":
                if not line_id:
                    return {"success": False, "error": "line_id is required for delete action"}

                response = await client.delete(
                    f"{settings.agent_api_base}/freshmart/orders/{order_id}/line-items/{line_id}",
                    timeout=10.0,
                )

                if response.status_code == 204:
                    return {
                        "success": True,
                        "message": f"Line item {line_id} deleted from order {order_id}",
                        "action": "deleted",
                        "order_id": order_id,
                        "line_id": line_id,
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": "Line item not found or does not belong to this order",
                        "order_id": order_id,
                        "line_id": line_id,
                    }
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Bad request")
                    return {
                        "success": False,
                        "error": error_detail,
                        "order_id": order_id,
                        "line_id": line_id,
                    }

            elif action == "update":
                if not line_id or not quantity:
                    return {"success": False, "error": "line_id and quantity are required for update action"}

                response = await client.put(
                    f"{settings.agent_api_base}/freshmart/orders/{order_id}/line-items/{line_id}",
                    json={"quantity": quantity},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Line item {line_id} updated with quantity {quantity}",
                        "action": "updated",
                        "order_id": order_id,
                        "line_id": line_id,
                        "line_item": response.json(),
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": "Line item not found",
                        "order_id": order_id,
                        "line_id": line_id,
                    }

            elif action == "add":
                if not product_id or not quantity or not unit_price:
                    return {
                        "success": False,
                        "error": "product_id, quantity, and unit_price are required for add action"
                    }

                # Get current line items to determine next sequence number
                list_response = await client.get(
                    f"{settings.agent_api_base}/freshmart/orders/{order_id}/line-items",
                    timeout=10.0,
                )

                if list_response.status_code == 200:
                    existing_items = list_response.json()
                    max_sequence = max([item.get("line_sequence", 0) for item in existing_items], default=0)
                    next_sequence = max_sequence + 1
                else:
                    next_sequence = 1

                # Get product info to determine perishable flag
                product_response = await client.get(
                    f"{settings.agent_api_base}/freshmart/products",
                    timeout=10.0,
                )
                perishable_flag = False
                if product_response.status_code == 200:
                    products = product_response.json()
                    product = next((p for p in products if p.get("product_id") == product_id), None)
                    if product:
                        perishable_flag = product.get("perishable", False)

                # Create new line item using batch endpoint
                response = await client.post(
                    f"{settings.agent_api_base}/freshmart/orders/{order_id}/line-items/batch",
                    json={
                        "line_items": [{
                            "product_id": product_id,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "line_sequence": next_sequence,
                            "perishable_flag": perishable_flag,
                        }]
                    },
                    timeout=10.0,
                )

                if response.status_code == 201:
                    line_items = response.json()
                    return {
                        "success": True,
                        "message": f"Added {quantity}x {product_id} to order {order_id}",
                        "action": "added",
                        "order_id": order_id,
                        "line_item": line_items[0] if line_items else None,
                    }

            else:
                return {
                    "success": False,
                    "error": f"Invalid action: {action}. Must be 'add', 'update', or 'delete'",
                }

            # Generic error handling for non-200/201/204 responses
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "API error") if response.text else "API error"
                return {
                    "success": False,
                    "error": f"API error ({response.status_code}): {error_detail}",
                    "order_id": order_id,
                }

        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "order_id": order_id,
            }
