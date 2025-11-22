"""Tool for fetching detailed order context from the API."""

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def fetch_order_context(order_ids: list[str]) -> list[dict]:
    """
    Fetch detailed context for one or more orders.

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
        for order_id in order_ids:
            try:
                # Get order details from FreshMart API
                response = await client.get(
                    f"{settings.agent_api_base}/freshmart/orders/{order_id}",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    order = response.json()
                    results.append(order)
                elif response.status_code == 404:
                    results.append({"order_id": order_id, "error": "Order not found"})
                else:
                    results.append({"order_id": order_id, "error": f"API error: {response.status_code}"})

            except httpx.HTTPError as e:
                results.append({"order_id": order_id, "error": f"Request failed: {str(e)}"})

    return results
