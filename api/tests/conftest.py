"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app


# Use in-memory SQLite for tests (or configure test Postgres)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_ontology_class():
    """Sample ontology class data."""
    return {
        "class_name": "TestEntity",
        "prefix": "test",
        "description": "A test entity class",
    }


@pytest.fixture
def sample_ontology_property():
    """Sample ontology property data."""
    return {
        "prop_name": "test_property",
        "domain_class_id": 1,
        "range_kind": "string",
        "is_multi_valued": False,
        "is_required": True,
        "description": "A test property",
    }


@pytest.fixture
def sample_triple():
    """Sample triple data."""
    return {
        "subject_id": "customer:test-123",
        "predicate": "customer_name",
        "object_value": "Test Customer",
        "object_type": "string",
    }
