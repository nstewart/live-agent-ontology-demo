"""Pytest fixtures for agent tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_settings():
    """Mock settings for agent tools."""
    settings = MagicMock()
    settings.agent_api_base = "http://api:8000"
    settings.agent_os_base = "http://opensearch:9200"
    return settings


@pytest.fixture
def sample_search_response():
    """Sample OpenSearch response for order search."""
    return {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "order_id": "order:FM-1001",
                        "order_number": "FM-1001",
                        "order_status": "OUT_FOR_DELIVERY",
                        "customer_name": "Alex Thompson",
                        "customer_address": "123 Main St, Brooklyn",
                        "store_name": "FreshMart Brooklyn Heights",
                        "store_zone": "Brooklyn",
                        "delivery_window_start": "2024-01-15T14:00:00",
                        "delivery_window_end": "2024-01-15T16:00:00",
                        "order_total_amount": 45.99,
                    },
                    "_score": 5.2,
                },
                {
                    "_source": {
                        "order_id": "order:FM-1002",
                        "order_number": "FM-1002",
                        "order_status": "DELIVERED",
                        "customer_name": "Alexander Smith",
                        "customer_address": "456 Oak Ave, Manhattan",
                        "store_name": "FreshMart Manhattan",
                        "store_zone": "Manhattan",
                        "delivery_window_start": "2024-01-15T10:00:00",
                        "delivery_window_end": "2024-01-15T12:00:00",
                        "order_total_amount": 32.50,
                    },
                    "_score": 4.8,
                },
            ]
        }
    }


@pytest.fixture
def sample_order_detail():
    """Sample order detail from API."""
    return {
        "order_id": "order:FM-1001",
        "order_status": "OUT_FOR_DELIVERY",
        "customer_id": "customer:101",
        "customer_name": "Alex Thompson",
        "customer_email": "alex@example.com",
        "customer_address": "123 Main St, Brooklyn",
        "store_id": "store:BK-01",
        "store_name": "FreshMart Brooklyn Heights",
        "delivery_window_start": "2024-01-15T14:00:00",
        "delivery_window_end": "2024-01-15T16:00:00",
        "order_total_amount": 45.99,
        "assigned_courier_id": "courier:C-101",
        "delivery_task_status": "IN_PROGRESS",
    }


@pytest.fixture
def sample_ontology_schema():
    """Sample ontology schema from API."""
    return {
        "classes": [
            {"class_name": "Customer", "prefix": "customer", "description": "A customer"},
            {"class_name": "Order", "prefix": "order", "description": "An order"},
            {"class_name": "Store", "prefix": "store", "description": "A store"},
        ],
        "properties": [
            {
                "prop_name": "customer_name",
                "domain_class_name": "Customer",
                "range_kind": "string",
                "range_class_name": None,
                "is_required": True,
            },
            {
                "prop_name": "order_status",
                "domain_class_name": "Order",
                "range_kind": "string",
                "range_class_name": None,
                "is_required": True,
            },
            {
                "prop_name": "placed_by",
                "domain_class_name": "Order",
                "range_kind": "entity_ref",
                "range_class_name": "Customer",
                "is_required": True,
            },
        ],
    }


@pytest.fixture
def sample_created_triple():
    """Sample created triple from API."""
    return {
        "id": 1,
        "subject_id": "order:FM-1001",
        "predicate": "order_status",
        "object_value": "DELIVERED",
        "object_type": "string",
        "created_at": "2024-01-15T15:00:00Z",
        "updated_at": "2024-01-15T15:00:00Z",
    }
