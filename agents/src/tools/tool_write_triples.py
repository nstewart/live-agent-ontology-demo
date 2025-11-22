"""Tool for writing triples to the knowledge graph."""

from typing import Literal

import httpx
from langchain_core.tools import tool

from src.config import get_settings


@tool
async def write_triples(
    triples: list[dict],
    validate: bool = True,
) -> list[dict]:
    """
    Write one or more triples to the FreshMart knowledge graph.

    Use this tool to:
    - Update order status (e.g., mark as DELIVERED)
    - Assign couriers to tasks
    - Create new entities

    Each triple must have:
    - subject_id: Entity ID (e.g., "order:FM-1001", "task:T1001")
    - predicate: Property name (e.g., "order_status", "assigned_to")
    - object_value: The value to set
    - object_type: One of "string", "int", "float", "bool", "timestamp", "entity_ref"

    Args:
        triples: List of triples to create/update
        validate: Whether to validate against ontology (default True)

    Returns:
        List of created/updated triples or error details

    Example:
        write_triples([{
            "subject_id": "order:FM-1001",
            "predicate": "order_status",
            "object_value": "DELIVERED",
            "object_type": "string"
        }])
    """
    settings = get_settings()
    results = []

    async with httpx.AsyncClient() as client:
        for triple in triples:
            try:
                # Validate triple structure
                required_fields = ["subject_id", "predicate", "object_value", "object_type"]
                missing = [f for f in required_fields if f not in triple]
                if missing:
                    results.append({
                        "error": f"Missing required fields: {missing}",
                        "triple": triple,
                    })
                    continue

                # Post to API
                response = await client.post(
                    f"{settings.agent_api_base}/triples",
                    json=triple,
                    params={"validate": validate},
                    timeout=10.0,
                )

                if response.status_code == 201:
                    results.append({
                        "success": True,
                        "triple": response.json(),
                    })
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", {})
                    results.append({
                        "success": False,
                        "error": "Validation failed",
                        "details": error_detail,
                        "triple": triple,
                    })
                else:
                    results.append({
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "triple": triple,
                    })

            except httpx.HTTPError as e:
                results.append({
                    "success": False,
                    "error": f"Request failed: {str(e)}",
                    "triple": triple,
                })

    return results
