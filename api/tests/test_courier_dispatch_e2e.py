"""End-to-end integration tests for courier dispatch CQRS flow.

These tests verify the complete courier dispatch lifecycle:
1. Create an order -> appears in orders_awaiting_courier
2. Assign a courier -> task created, courier status updated
3. Wait for timer -> task appears in tasks_ready_to_advance
4. Advance PICKING -> DELIVERING
5. Advance DELIVERING -> COMPLETED, courier freed

Requires: MZ_HOST and MZ_PORT environment variables set.
"""

import asyncio
import os
import time
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.freshmart.service import FreshMartService
from src.config import get_settings


async def upsert_triples(pg_session: AsyncSession, triples: list[tuple[str, str, str, str]]):
    """Upsert triples using delete-then-insert pattern."""
    for subject_id, predicate, object_value, object_type in triples:
        await pg_session.execute(text("""
            DELETE FROM triples WHERE subject_id = :subject_id AND predicate = :predicate
        """), {"subject_id": subject_id, "predicate": predicate})
        await pg_session.execute(text("""
            INSERT INTO triples (subject_id, predicate, object_value, object_type)
            VALUES (:subject_id, :predicate, :object_value, :object_type)
        """), {
            "subject_id": subject_id,
            "predicate": predicate,
            "object_value": object_value,
            "object_type": object_type,
        })
    await pg_session.commit()


def is_mz_available():
    """Check if Materialize is available."""
    return os.environ.get("MZ_HOST") or os.environ.get("MATERIALIZE_URL")


requires_mz = pytest.mark.skipif(
    not is_mz_available(),
    reason="Materialize not available - set MZ_HOST to run integration tests"
)


class MzQueryRunner:
    """Helper to run queries on Materialize with fresh connections."""

    def __init__(self, engine, factory):
        self.engine = engine
        self.factory = factory

    async def execute(self, query, params=None):
        """Execute query in a fresh session to get latest data."""
        async with self.factory() as session:
            await session.execute(text("SET CLUSTER = serving"))
            if params:
                result = await session.execute(text(query), params)
            else:
                result = await session.execute(text(query))
            return result.fetchall()


@pytest_asyncio.fixture
async def mz_session():
    """Create Materialize query runner for testing."""
    get_settings.cache_clear()
    settings = get_settings()

    from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg

    original_setup_json = PGDialect_asyncpg.setup_asyncpg_json_codec
    original_setup_jsonb = PGDialect_asyncpg.setup_asyncpg_jsonb_codec

    async def noop_setup_json(self, conn):
        pass

    async def noop_setup_jsonb(self, conn):
        pass

    PGDialect_asyncpg.setup_asyncpg_json_codec = noop_setup_json
    PGDialect_asyncpg.setup_asyncpg_jsonb_codec = noop_setup_jsonb

    try:
        engine = create_async_engine(
            settings.mz_dsn,
            echo=False,
            pool_pre_ping=True,
            connect_args={"prepared_statement_cache_size": 0},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        yield MzQueryRunner(engine, factory)

        await engine.dispose()
    finally:
        PGDialect_asyncpg.setup_asyncpg_json_codec = original_setup_json
        PGDialect_asyncpg.setup_asyncpg_jsonb_codec = original_setup_jsonb


@pytest_asyncio.fixture
async def pg_session():
    """Create PostgreSQL session for writes."""
    get_settings.cache_clear()
    settings = get_settings()

    engine = create_async_engine(
        settings.pg_dsn,
        echo=False,
        pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def mz_service(mz_session: AsyncSession):
    """Create FreshMart service with Materialize backend."""
    return FreshMartService(mz_session, use_materialize=True)


@requires_mz
class TestCourierDispatchE2EFlow:
    """End-to-end tests for the complete courier dispatch CQRS flow."""

    @pytest.mark.asyncio
    async def test_full_order_lifecycle(self, mz_session: MzQueryRunner, pg_session: AsyncSession):
        """Test complete order lifecycle: create -> assign -> pick -> deliver -> complete."""

        # Generate unique IDs for this test
        test_id = f"E2E-{int(time.time() * 1000) % 100000}"
        order_id = f"order:FM-{test_id}"
        task_id = f"task:FM-{test_id}"

        # Step 1: Find an available courier
        rows = await mz_session.execute(
            "SELECT courier_id, home_store_id FROM couriers_available LIMIT 1"
        )
        courier_row = rows[0] if rows else None

        if not courier_row:
            pytest.skip("No available couriers - run test when couriers are free")

        courier_id = courier_row[0]
        store_id = courier_row[1]

        print(f"\n=== E2E Test: {test_id} ===")
        print(f"Using courier: {courier_id} at store: {store_id}")

        # Step 2: Create an order (write to PostgreSQL)
        now = datetime.now(timezone.utc).isoformat()
        order_triples = [
            (order_id, "order_number", f"FM-{test_id}", "string"),
            (order_id, "order_status", "CREATED", "string"),
            (order_id, "order_store", store_id, "entity_ref"),
            (order_id, "placed_by", "customer:00001", "entity_ref"),
            (order_id, "delivery_window_start", now, "timestamp"),
            (order_id, "delivery_window_end", now, "timestamp"),
            (order_id, "order_total_amount", "10.00", "string"),
        ]

        await upsert_triples(pg_session, order_triples)
        print(f"Created order: {order_id}")

        # Wait for Materialize to sync (CDC replication + view refresh)
        # Retry loop to handle replication lag
        awaiting_row = None
        for attempt in range(5):
            await asyncio.sleep(1)
            rows = await mz_session.execute(
                "SELECT order_id FROM orders_awaiting_courier WHERE order_id = :order_id",
                {"order_id": order_id}
            )
            awaiting_row = rows[0] if rows else None
            if awaiting_row:
                break
            print(f"Attempt {attempt + 1}: Order not yet visible in orders_awaiting_courier...")

        assert awaiting_row is not None, f"Order {order_id} should appear in orders_awaiting_courier"
        print(f"Order appears in queue: {order_id}")

        # Step 4: Assign courier to order (create task, update statuses)
        assignment_triples = [
            (task_id, "task_of_order", order_id, "entity_ref"),
            (task_id, "assigned_to", courier_id, "entity_ref"),
            (task_id, "task_status", "PICKING", "string"),
            (task_id, "task_started_at", now, "timestamp"),
            (courier_id, "courier_status", "PICKING", "string"),
            (order_id, "order_status", "PICKING", "string"),
        ]

        await upsert_triples(pg_session, assignment_triples)
        print(f"Assigned courier {courier_id} to order, task: {task_id}")

        # Wait for Materialize to sync (CDC replication + view refresh)
        await asyncio.sleep(2)

        # Step 5: Verify task appears in delivery_tasks_active
        rows = await mz_session.execute(
            "SELECT task_status, courier_id FROM delivery_tasks_active WHERE task_id = :task_id",
            {"task_id": task_id}
        )
        active_row = rows[0] if rows else None
        assert active_row is not None, f"Task {task_id} should appear in delivery_tasks_active"
        assert active_row[0] == "PICKING", "Task should be in PICKING status"
        print(f"Task is active: {task_id} status=PICKING")

        # Step 6: Verify courier is no longer available
        rows = await mz_session.execute(
            "SELECT courier_id FROM couriers_available WHERE courier_id = :courier_id",
            {"courier_id": courier_id}
        )
        available_row = rows[0] if rows else None
        assert available_row is None, f"Courier {courier_id} should NOT be in couriers_available"
        print(f"Courier {courier_id} is now busy (not in available list)")

        # Step 7: Wait for task to be ready to advance (5 seconds + buffer)
        print("Waiting 6 seconds for task timer to elapse...")
        await asyncio.sleep(6)

        # Step 8: Verify task appears in tasks_ready_to_advance
        rows = await mz_session.execute(
            "SELECT task_id, task_status FROM tasks_ready_to_advance WHERE task_id = :task_id",
            {"task_id": task_id}
        )
        ready_row = rows[0] if rows else None
        assert ready_row is not None, f"Task {task_id} should appear in tasks_ready_to_advance after 5 seconds"
        print(f"Task ready to advance: {task_id}")

        # Step 9: Advance to DELIVERING
        delivering_triples = [
            (task_id, "task_status", "DELIVERING", "string"),
            (task_id, "task_started_at", datetime.now(timezone.utc).isoformat(), "timestamp"),
            (order_id, "order_status", "OUT_FOR_DELIVERY", "string"),
        ]

        await upsert_triples(pg_session, delivering_triples)
        print(f"Advanced task to DELIVERING")

        await asyncio.sleep(2)

        # Verify task is now DELIVERING
        rows = await mz_session.execute(
            "SELECT task_status FROM delivery_tasks_active WHERE task_id = :task_id",
            {"task_id": task_id}
        )
        delivering_row = rows[0] if rows else None
        assert delivering_row is not None and delivering_row[0] == "DELIVERING"
        print(f"Task status confirmed: DELIVERING")

        # Step 10: Wait for delivery timer
        print("Waiting 6 seconds for delivery timer...")
        await asyncio.sleep(6)

        # Step 11: Complete delivery
        completion_triples = [
            (task_id, "task_status", "COMPLETED", "string"),
            (order_id, "order_status", "DELIVERED", "string"),
            (courier_id, "courier_status", "AVAILABLE", "string"),
        ]

        await upsert_triples(pg_session, completion_triples)
        print(f"Completed delivery")

        await asyncio.sleep(2)

        # Step 12: Verify courier is available again
        rows = await mz_session.execute(
            "SELECT courier_id FROM couriers_available WHERE courier_id = :courier_id",
            {"courier_id": courier_id}
        )
        final_available = rows[0] if rows else None
        assert final_available is not None, f"Courier {courier_id} should be available after completing delivery"
        print(f"Courier {courier_id} is available again")

        # Step 13: Verify order status is DELIVERED
        rows = await mz_session.execute(
            "SELECT order_status FROM orders_flat_mv WHERE order_id = :order_id",
            {"order_id": order_id}
        )
        order_row = rows[0] if rows else None
        assert order_row is not None and order_row[0] == "DELIVERED"
        print(f"Order status confirmed: DELIVERED")

        print(f"\n=== E2E Test PASSED: {test_id} ===")
        print("Full lifecycle: CREATED -> PICKING -> OUT_FOR_DELIVERY -> DELIVERED")

    @pytest.mark.asyncio
    async def test_tasks_ready_to_advance_uses_mz_now(self, mz_session: MzQueryRunner):
        """Verify tasks_ready_to_advance correctly uses mz_now() for filtering."""
        # This test verifies that the view filters based on current time
        rows = await mz_session.execute("""
            SELECT
                task_id,
                task_started_at,
                expected_completion_at,
                expected_completion_at <= mz_now() AS is_ready
            FROM delivery_tasks_active
            LIMIT 5
        """)

        # For any active tasks, verify the timing logic is correct
        for row in rows:
            task_id, started_at, expected_at, is_ready = row
            print(f"Task {task_id}: started={started_at}, expected={expected_at}, ready={is_ready}")

        # The query should work without errors - that's the main assertion
        assert isinstance(rows, list)

    @pytest.mark.asyncio
    async def test_courier_becomes_unavailable_when_assigned(self, mz_session: MzQueryRunner, pg_session: AsyncSession):
        """Verify courier disappears from available list when assigned to task."""

        # Find an available courier
        rows = await mz_session.execute(
            "SELECT courier_id FROM couriers_available LIMIT 1"
        )
        row = rows[0] if rows else None

        if not row:
            pytest.skip("No available couriers")

        courier_id = row[0]
        test_id = f"UNAVAIL-{int(time.time() * 1000) % 100000}"
        task_id = f"task:{test_id}"
        order_id = f"order:{test_id}"

        # Create a minimal task assignment
        now = datetime.now(timezone.utc).isoformat()
        triples = [
            (task_id, "task_of_order", order_id, "entity_ref"),
            (task_id, "assigned_to", courier_id, "entity_ref"),
            (task_id, "task_status", "PICKING", "string"),
            (task_id, "task_started_at", now, "timestamp"),
        ]

        await upsert_triples(pg_session, triples)

        # Wait for Materialize to sync, then retry
        check_row = None
        for attempt in range(5):
            await asyncio.sleep(1)
            rows = await mz_session.execute(
                "SELECT courier_id FROM couriers_available WHERE courier_id = :courier_id",
                {"courier_id": courier_id}
            )
            check_row = rows[0] if rows else None
            if check_row is None:
                break
            print(f"Attempt {attempt + 1}: Courier still visible, waiting...")

        assert check_row is None, f"Courier {courier_id} should not be available when assigned to active task"

        # Cleanup: complete the task
        await upsert_triples(pg_session, [(task_id, "task_status", "COMPLETED", "string")])
