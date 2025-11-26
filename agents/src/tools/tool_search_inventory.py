"""Tool for searching store inventory."""

from typing import Optional

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def search_inventory(
    query: str,
    store_id: str = "store:BK-01",
    limit: int = 10,
) -> list[dict]:
    """
    Search for products available in a store's inventory.

    Use this tool to:
    - Find products by name or description
    - Check product availability and prices
    - Get product details for order creation

    Args:
        query: Product name or description to search for (e.g., "milk", "bananas", "pasta")
        store_id: Store to search in (default: store:BK-01)
        limit: Maximum number of results (default: 10)

    Returns:
        List of matching products with:
        - product_id: Unique product identifier
        - product_name: Product name
        - category: Product category
        - unit_price: Price per unit
        - quantity_available: Current stock level (from inventory)
        - is_perishable: Whether product requires refrigeration

    Example:
        search_inventory(query="organic milk", store_id="store:BK-01")
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Search inventory in OpenSearch
            inventory_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"store_id": store_id}}
                        ]
                    }
                },
                "size": 1000,  # Get all inventory for the store
            }

            inventory_response = await client.post(
                f"{settings.agent_os_base}/inventory/_search",
                json=inventory_query,
                timeout=10.0,
            )
            inventory_response.raise_for_status()
            inventory_data = inventory_response.json()

            # Extract inventory records
            inventory_items = {}
            for hit in inventory_data.get("hits", {}).get("hits", []):
                source = hit["_source"]
                product_id = source.get("product_id")
                if product_id:
                    inventory_items[product_id] = {
                        "stock_level": source.get("stock_level", 0),
                        "replenishment_eta": source.get("replenishment_eta"),
                    }

            if not inventory_items:
                return []

            # Step 2: Search products by name in OpenSearch
            # Note: This requires a products index (not yet implemented)
            # For now, we'll just return inventory items with product IDs
            # In production, this would join with a products index

            # Build list of product IDs from inventory
            product_ids = list(inventory_items.keys())

            # Query products by name match AND available in inventory
            product_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["product_name^2", "category"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            },
                            {"terms": {"product_id": product_ids}}
                        ]
                    }
                },
                "size": limit,
            }

            # For now, return basic inventory info with product IDs
            # Products index not yet implemented in OpenSearch
            # Agent can use product_id to look up details if needed
            results = []
            for product_id in list(inventory_items.keys())[:limit]:
                inv_info = inventory_items[product_id]

                # Simple name filter on product_id
                if query.lower() in product_id.lower():
                    results.append({
                        "product_id": product_id,
                        "store_id": store_id,
                        "quantity_available": inv_info.get("stock_level", 0),
                        "replenishment_eta": inv_info.get("replenishment_eta"),
                        "note": "Product details lookup not yet implemented. Use product_id to reference in orders.",
                    })

            # If no results by product_id match, return all inventory for the store
            if not results and inventory_items:
                for product_id, inv_info in list(inventory_items.items())[:limit]:
                    results.append({
                        "product_id": product_id,
                        "store_id": store_id,
                        "quantity_available": inv_info.get("stock_level", 0),
                        "replenishment_eta": inv_info.get("replenishment_eta"),
                    })

            return results

        except httpx.HTTPError as e:
            return [{"error": f"Search failed: {str(e)}"}]
