"""Materialize client for querying views."""

from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings


class MaterializeClient:
    """Client for querying Materialize views."""

    def __init__(self):
        settings = get_settings()
        self.engine = create_async_engine(
            settings.mz_dsn,
            echo=settings.log_level == "DEBUG",
            pool_size=3,
            max_overflow=5,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self):
        """Close the connection pool."""
        await self.engine.dispose()

    async def query_orders_search_source(
        self,
        after_timestamp: datetime,
        batch_size: int = 100,
    ) -> list[dict]:
        """
        Query orders_search_source for changed documents.

        Args:
            after_timestamp: Only return rows updated after this time
            batch_size: Maximum rows to return

        Returns:
            List of order documents ready for indexing
        """
        async with self.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT
                        order_id,
                        order_number,
                        order_status,
                        store_id,
                        customer_id,
                        delivery_window_start,
                        delivery_window_end,
                        order_total_amount,
                        customer_name,
                        customer_email,
                        customer_address,
                        store_name,
                        store_zone,
                        store_address,
                        assigned_courier_id,
                        delivery_task_status,
                        delivery_eta,
                        effective_updated_at
                    FROM orders_search_source
                    WHERE effective_updated_at > :after_timestamp
                    ORDER BY effective_updated_at
                    LIMIT :batch_size
                """),
                {"after_timestamp": after_timestamp, "batch_size": batch_size},
            )
            rows = result.fetchall()

            return [
                {
                    "order_id": row.order_id,
                    "order_number": row.order_number,
                    "order_status": row.order_status,
                    "store_id": row.store_id,
                    "customer_id": row.customer_id,
                    "delivery_window_start": row.delivery_window_start,
                    "delivery_window_end": row.delivery_window_end,
                    "order_total_amount": float(row.order_total_amount) if row.order_total_amount else None,
                    "customer_name": row.customer_name,
                    "customer_email": row.customer_email,
                    "customer_address": row.customer_address,
                    "store_name": row.store_name,
                    "store_zone": row.store_zone,
                    "store_address": row.store_address,
                    "assigned_courier_id": row.assigned_courier_id,
                    "delivery_task_status": row.delivery_task_status,
                    "delivery_eta": row.delivery_eta,
                    "effective_updated_at": row.effective_updated_at,
                }
                for row in rows
            ]

    async def get_cursor(self, view_name: str) -> Optional[datetime]:
        """Get the last synced timestamp for a view."""
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT last_synced_at FROM sync_cursors WHERE view_name = :view_name"),
                {"view_name": view_name},
            )
            row = result.fetchone()
            return row.last_synced_at if row else None

    async def update_cursor(self, view_name: str, timestamp: datetime):
        """Update the cursor for a view."""
        async with self.session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO sync_cursors (view_name, last_synced_at, updated_at)
                    VALUES (:view_name, :timestamp, NOW())
                    ON CONFLICT (view_name) DO UPDATE
                    SET last_synced_at = :timestamp, updated_at = NOW()
                """),
                {"view_name": view_name, "timestamp": timestamp},
            )
            await session.commit()

    async def refresh_views(self):
        """Trigger refresh of materialized views."""
        async with self.session_factory() as session:
            try:
                await session.execute(text("SELECT refresh_all_views()"))
                await session.commit()
            except Exception:
                # Function may not exist if not using Materialize emulator
                pass
