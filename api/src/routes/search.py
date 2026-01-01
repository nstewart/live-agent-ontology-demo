"""Search API routes for OpenSearch queries.

These endpoints proxy search requests to OpenSearch, allowing the frontend
to perform semantic searches across denormalized order documents.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Query, HTTPException

from src.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])

settings = get_settings()

# Constants for search configuration
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20
OPENSEARCH_TIMEOUT = 10.0


@router.get("/orders")
async def search_orders(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="Max results to return"),
) -> dict[str, Any]:
    """
    Search orders in OpenSearch using multi_match query.

    Searches across multiple fields: customer_name, store_name, store_zone,
    order_number, order_status. Uses fuzzy matching for typo tolerance.

    Returns the raw OpenSearch response for educational purposes.
    """
    # Build OpenSearch multi_match query
    search_body = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": [
                    "customer_name^2",
                    "store_name^2",
                    "store_zone",
                    "order_number^3",
                    "order_status",
                ],
                "fuzziness": "AUTO",
                "operator": "or",
            }
        },
        "size": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=OPENSEARCH_TIMEOUT) as client:
            response = await client.post(
                f"{settings.os_url}/orders/_search",
                json=search_body,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 404:
                # Index doesn't exist yet - return empty response structure
                logger.info("OpenSearch index 'orders' does not exist yet, returning empty results")
                return {
                    "took": 0,
                    "timed_out": False,
                    "_shards": {"total": 0, "successful": 0, "skipped": 0, "failed": 0},
                    "hits": {
                        "total": {"value": 0, "relation": "eq"},
                        "max_score": None,
                        "hits": [],
                    },
                }

            response.raise_for_status()
            return response.json()

    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to OpenSearch: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="OpenSearch is not available. Ensure the search-sync service is running.",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenSearch returned error status {e.response.status_code}: {e.response.text}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"OpenSearch error: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )
