"""Tool for fetching detailed order context from OpenSearch."""

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def fetch_order_context(order_ids: list[str]) -> list[dict]:
    """
    Fetch detailed context for one or more orders from OpenSearch.

    Use this tool after searching to get full order details including:
    - Customer information
    - Store information
    - Delivery task status
    - Order line items

    Args:
        order_ids: List of order IDs to fetch (e.g., ["order:FM-1001", "order:FM-1002"])

    Returns:
        List of detailed order records with customer, store, and delivery info
    """
    settings = get_settings()
    results = []

    async with httpx.AsyncClient() as client:
        try:
            # Query OpenSearch for multiple orders at once
            search_body = {
                "query": {
                    "terms": {
                        "order_id": order_ids
                    }
                },
                "size": len(order_ids),
            }

            response = await client.post(
                f"{settings.agent_os_base}/orders/_search",
                json=search_body,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Extract order details from hits
            found_orders = {}
            for hit in data.get("hits", {}).get("hits", []):
                source = hit["_source"]
                order_id = source.get("order_id")
                if order_id:
                    found_orders[order_id] = {
                        "order_id": order_id,
                        "order_number": source.get("order_number"),
                        "order_status": source.get("order_status"),
                        "customer_id": source.get("customer_id"),
                        "customer_name": source.get("customer_name"),
                        "customer_email": source.get("customer_email"),
                        "customer_address": source.get("customer_address"),
                        "store_id": source.get("store_id"),
                        "store_name": source.get("store_name"),
                        "store_zone": source.get("store_zone"),
                        "store_address": source.get("store_address"),
                        "delivery_window_start": source.get("delivery_window_start"),
                        "delivery_window_end": source.get("delivery_window_end"),
                        "order_total_amount": source.get("order_total_amount"),
                        "assigned_courier_id": source.get("assigned_courier_id"),
                        "delivery_task_status": source.get("delivery_task_status"),
                        "delivery_eta": source.get("delivery_eta"),
                        "line_items": source.get("line_items", []),
                        "line_item_count": source.get("line_item_count", 0),
                        "has_perishable_items": source.get("has_perishable_items"),
                        "effective_updated_at": source.get("effective_updated_at"),
                    }

            # Return results in the same order as requested, with errors for missing orders
            for order_id in order_ids:
                if order_id in found_orders:
                    results.append(found_orders[order_id])
                else:
                    results.append({"order_id": order_id, "error": "Order not found"})

        except httpx.HTTPError as e:
            # If OpenSearch query fails, return errors for all orders
            for order_id in order_ids:
                results.append({"order_id": order_id, "error": f"Search failed: {str(e)}"})

    return results
