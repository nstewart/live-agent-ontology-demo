"""Unit tests for OntologyService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ontology.models import OntologyClass, OntologyClassCreate, OntologyClassUpdate
from src.ontology.service import OntologyService


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    """Create OntologyService with mock session."""
    return OntologyService(mock_session)


class TestListClasses:
    """Tests for OntologyService.list_classes."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_classes(self, service, mock_session):
        """Returns empty list when no classes exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service.list_classes()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_classes_ordered_by_name(self, service, mock_session):
        """Returns classes when they exist."""
        now = datetime.now()
        mock_rows = [
            MagicMock(
                id=1,
                class_name="Customer",
                prefix="customer",
                description="A customer",
                parent_class_id=None,
                created_at=now,
                updated_at=now,
            ),
            MagicMock(
                id=2,
                class_name="Order",
                prefix="order",
                description="An order",
                parent_class_id=None,
                created_at=now,
                updated_at=now,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await service.list_classes()

        assert len(result) == 2
        assert result[0].class_name == "Customer"
        assert result[1].class_name == "Order"


class TestGetClass:
    """Tests for OntologyService.get_class."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_session):
        """Returns None when class doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get_class(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_class_when_found(self, service, mock_session):
        """Returns class when it exists."""
        now = datetime.now()
        mock_row = MagicMock(
            id=1,
            class_name="Customer",
            prefix="customer",
            description="A customer",
            parent_class_id=None,
            created_at=now,
            updated_at=now,
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await service.get_class(1)

        assert result is not None
        assert result.id == 1
        assert result.class_name == "Customer"


class TestGetClassByPrefix:
    """Tests for OntologyService.get_class_by_prefix."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_session):
        """Returns None when prefix doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get_class_by_prefix("unknown")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_class_when_found(self, service, mock_session):
        """Returns class when prefix exists."""
        now = datetime.now()
        mock_row = MagicMock(
            id=1,
            class_name="Customer",
            prefix="customer",
            description="A customer",
            parent_class_id=None,
            created_at=now,
            updated_at=now,
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await service.get_class_by_prefix("customer")

        assert result is not None
        assert result.prefix == "customer"


class TestCreateClass:
    """Tests for OntologyService.create_class."""

    @pytest.mark.asyncio
    async def test_creates_class_and_returns_it(self, service, mock_session):
        """Creates class and returns created object."""
        now = datetime.now()
        mock_row = MagicMock(
            id=1,
            class_name="TestEntity",
            prefix="test_entity",
            description="A test entity",
            parent_class_id=None,
            created_at=now,
            updated_at=now,
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = OntologyClassCreate(
            class_name="TestEntity",
            prefix="test_entity",
            description="A test entity",
        )
        result = await service.create_class(data)

        assert result.class_name == "TestEntity"
        assert result.prefix == "test_entity"
        mock_session.execute.assert_called_once()


class TestUpdateClass:
    """Tests for OntologyService.update_class."""

    @pytest.mark.asyncio
    async def test_returns_none_when_class_not_found(self, service, mock_session):
        """Returns None when class doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        data = OntologyClassUpdate(description="Updated description")
        result = await service.update_class(999, data)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_unchanged_when_no_updates(self, service, mock_session):
        """Returns existing class when no fields to update."""
        now = datetime.now()
        mock_row = MagicMock(
            id=1,
            class_name="Customer",
            prefix="customer",
            description="A customer",
            parent_class_id=None,
            created_at=now,
            updated_at=now,
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = OntologyClassUpdate()  # No updates
        result = await service.update_class(1, data)

        assert result is not None


class TestDeleteClass:
    """Tests for OntologyService.delete_class."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self, service, mock_session):
        """Returns True when class is deleted."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await service.delete_class(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, service, mock_session):
        """Returns False when class doesn't exist."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await service.delete_class(999)

        assert result is False


class TestGetFullSchema:
    """Tests for OntologyService.get_full_schema."""

    @pytest.mark.asyncio
    async def test_returns_schema_with_classes_and_properties(self, service, mock_session):
        """Returns complete schema."""
        now = datetime.now()

        # Mock for classes query
        class_rows = [
            MagicMock(
                id=1,
                class_name="Customer",
                prefix="customer",
                description="A customer",
                parent_class_id=None,
                created_at=now,
                updated_at=now,
            )
        ]
        # Mock for properties query
        prop_rows = [
            MagicMock(
                id=1,
                prop_name="customer_name",
                domain_class_id=1,
                range_kind="string",
                range_class_id=None,
                is_multi_valued=False,
                is_required=True,
                description="Customer name",
                created_at=now,
                updated_at=now,
                domain_class_name="Customer",
                range_class_name=None,
            )
        ]

        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.fetchall.return_value = class_rows
            else:
                mock_result.fetchall.return_value = prop_rows
            return mock_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        result = await service.get_full_schema()

        assert len(result.classes) == 1
        assert len(result.properties) == 1
        assert result.classes[0].class_name == "Customer"
        assert result.properties[0].prop_name == "customer_name"
