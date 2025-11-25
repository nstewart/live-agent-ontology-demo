"""Unit tests for OrderLineService."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.freshmart.models import OrderLineCreate, OrderLineFlat, OrderLineUpdate
from src.freshmart.order_line_service import OrderLineService
from src.triples.models import TripleCreate


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    """Create OrderLineService with mock session."""
    return OrderLineService(mock_session)


class TestGenerateLineId:
    """Tests for _generate_line_id helper method."""

    def test_generates_correct_format(self, service):
        """Generates line ID in correct format."""
        line_id = service._generate_line_id("order:FM-1001", 1)
        assert line_id == "orderline:FM-1001-001"

    def test_pads_sequence_with_zeros(self, service):
        """Pads sequence number with leading zeros."""
        line_id = service._generate_line_id("order:FM-1001", 5)
        assert line_id == "orderline:FM-1001-005"

        line_id = service._generate_line_id("order:FM-1001", 99)
        assert line_id == "orderline:FM-1001-099"


class TestCreateLineItemTriples:
    """Tests for _create_line_item_triples helper method."""

    def test_creates_all_required_triples(self, service):
        """Creates all 7 required triples for a line item."""
        line_item = OrderLineCreate(
            product_id="product:PROD-001",
            quantity=2,
            unit_price=Decimal("12.50"),
            line_sequence=1,
            perishable_flag=True,
        )

        triples = service._create_line_item_triples("order:FM-1001", 1, line_item)

        assert len(triples) == 7
        predicates = {t.predicate for t in triples}
        assert predicates == {
            "line_of_order",
            "line_product",
            "quantity",
            "unit_price",
            "line_amount",
            "line_sequence",
            "perishable_flag",
        }

    def test_calculates_line_amount_correctly(self, service):
        """Calculates line_amount as quantity * unit_price."""
        line_item = OrderLineCreate(
            product_id="product:PROD-001",
            quantity=3,
            unit_price=Decimal("10.00"),
            line_sequence=1,
            perishable_flag=False,
        )

        triples = service._create_line_item_triples("order:FM-1001", 1, line_item)

        line_amount_triple = next(t for t in triples if t.predicate == "line_amount")
        assert line_amount_triple.object_value == "30.00"

    def test_sets_correct_line_id(self, service):
        """Sets correct line_id for all triples."""
        line_item = OrderLineCreate(
            product_id="product:PROD-001",
            quantity=1,
            unit_price=Decimal("5.00"),
            line_sequence=2,
            perishable_flag=True,
        )

        triples = service._create_line_item_triples("order:FM-1001", 2, line_item)

        assert all(t.subject_id == "orderline:FM-1001-002" for t in triples)


class TestCreateLineItemsBatch:
    """Tests for create_line_items_batch method."""

    @pytest.mark.asyncio
    async def test_validates_unique_sequences(self, service):
        """Raises ValueError if line_sequence values are not unique."""
        line_items = [
            OrderLineCreate(
                product_id="product:PROD-001",
                quantity=1,
                unit_price=Decimal("10.00"),
                line_sequence=1,
                perishable_flag=False,
            ),
            OrderLineCreate(
                product_id="product:PROD-002",
                quantity=2,
                unit_price=Decimal("20.00"),
                line_sequence=1,  # Duplicate sequence
                perishable_flag=True,
            ),
        ]

        with pytest.raises(ValueError, match="line_sequence values must be unique"):
            await service.create_line_items_batch("order:FM-1001", line_items)

    @pytest.mark.asyncio
    async def test_sorts_by_sequence_before_creating(self, service, mock_session):
        """Sorts line items by sequence before creating triples."""
        line_items = [
            OrderLineCreate(
                product_id="product:PROD-002",
                quantity=2,
                unit_price=Decimal("20.00"),
                line_sequence=2,
                perishable_flag=True,
            ),
            OrderLineCreate(
                product_id="product:PROD-001",
                quantity=1,
                unit_price=Decimal("10.00"),
                line_sequence=1,
                perishable_flag=False,
            ),
        ]

        # Mock triple service and list method
        with patch.object(service.triple_service, "create_triples_batch", new_callable=AsyncMock) as mock_create:
            with patch.object(service, "list_order_lines", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = []
                await service.create_line_items_batch("order:FM-1001", line_items)

                # Verify create was called with triples in correct order
                assert mock_create.called
                call_args = mock_create.call_args[0][0]

                # First triple should be for sequence 1
                assert call_args[0].subject_id == "orderline:FM-1001-001"


class TestListOrderLines:
    """Tests for list_order_lines method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_lines(self, service, mock_session):
        """Returns empty list when order has no line items."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service.list_order_lines("order:FM-1001")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_sorted_by_sequence(self, service, mock_session):
        """Returns line items sorted by line_sequence."""
        now = datetime.now()
        mock_rows = [
            MagicMock(
                line_id="orderline:FM-1001-001",
                order_id="order:FM-1001",
                product_id="product:PROD-001",
                quantity=2,
                unit_price=Decimal("10.00"),
                line_amount=Decimal("20.00"),
                line_sequence=1,
                perishable_flag=True,
                effective_updated_at=now,
            ),
            MagicMock(
                line_id="orderline:FM-1001-002",
                order_id="order:FM-1001",
                product_id="product:PROD-002",
                quantity=1,
                unit_price=Decimal("30.00"),
                line_amount=Decimal("30.00"),
                line_sequence=2,
                perishable_flag=False,
                effective_updated_at=now,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await service.list_order_lines("order:FM-1001")

        assert len(result) == 2
        assert result[0].line_sequence == 1
        assert result[1].line_sequence == 2


class TestUpdateLineItem:
    """Tests for update_line_item method."""

    @pytest.mark.asyncio
    async def test_raises_error_if_not_found(self, service, mock_session):
        """Raises ValueError if line item does not exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        update = OrderLineUpdate(quantity=5)

        with pytest.raises(ValueError, match="Line item .* not found"):
            await service.update_line_item("orderline:FM-1001-001", update)

    @pytest.mark.asyncio
    async def test_recalculates_line_amount_on_quantity_change(self, service, mock_session):
        """Recalculates line_amount when quantity changes."""
        now = datetime.now()
        current_line = MagicMock(
            line_id="orderline:FM-1001-001",
            order_id="order:FM-1001",
            product_id="product:PROD-001",
            quantity=2,
            unit_price=Decimal("10.00"),
            line_amount=Decimal("20.00"),
            line_sequence=1,
            perishable_flag=True,
            effective_updated_at=now,
        )

        # Mock get_line_item to return current state twice
        with patch.object(service, "get_line_item", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                OrderLineFlat(**current_line.__dict__),
                OrderLineFlat(
                    line_id="orderline:FM-1001-001",
                    order_id="order:FM-1001",
                    product_id="product:PROD-001",
                    quantity=5,
                    unit_price=Decimal("10.00"),
                    line_amount=Decimal("50.00"),  # Updated
                    line_sequence=1,
                    perishable_flag=True,
                    effective_updated_at=now,
                ),
            ]

            update = OrderLineUpdate(quantity=5)
            result = await service.update_line_item("orderline:FM-1001-001", update)

            assert result.quantity == 5
            assert result.line_amount == Decimal("50.00")


class TestDeleteLineItem:
    """Tests for delete_line_item method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self, service, mock_session):
        """Returns True when line item is successfully deleted."""
        mock_result = MagicMock()
        mock_result.rowcount = 7  # 7 triples deleted
        mock_session.execute.return_value = mock_result

        result = await service.delete_line_item("orderline:FM-1001-001")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, service, mock_session):
        """Returns False when line item does not exist."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await service.delete_line_item("orderline:FM-1001-999")

        assert result is False


class TestDeleteOrderLines:
    """Tests for delete_order_lines (cascade delete) method."""

    @pytest.mark.asyncio
    async def test_returns_count_of_deleted_lines(self, service, mock_session):
        """Returns count of deleted line items."""
        mock_result = MagicMock()
        mock_result.rowcount = 21  # 3 line items * 7 triples each
        mock_session.execute.return_value = mock_result

        count = await service.delete_order_lines("order:FM-1001")

        assert count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_lines(self, service, mock_session):
        """Returns 0 when order has no line items."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        count = await service.delete_order_lines("order:FM-9999")

        assert count == 0
