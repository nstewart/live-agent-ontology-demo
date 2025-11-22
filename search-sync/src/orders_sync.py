"""Orders sync worker - syncs orders_search_source to OpenSearch."""

import asyncio
import logging
from datetime import datetime, timezone

from src.config import get_settings
from src.mz_client import MaterializeClient
from src.opensearch_client import OpenSearchClient

logger = logging.getLogger(__name__)


class OrdersSyncWorker:
    """Worker that syncs orders from Materialize to OpenSearch."""

    VIEW_NAME = "orders_search_source"

    def __init__(
        self,
        mz_client: MaterializeClient,
        os_client: OpenSearchClient,
    ):
        self.mz = mz_client
        self.os = os_client
        self.settings = get_settings()
        self._shutdown = asyncio.Event()

    def stop(self):
        """Signal the worker to stop."""
        self._shutdown.set()

    async def run(self):
        """Main sync loop."""
        logger.info("Starting orders sync worker")

        # Ensure OpenSearch index exists
        await self.os.setup_indices()

        while not self._shutdown.is_set():
            try:
                await self._sync_batch()
            except Exception as e:
                logger.error(f"Sync error: {e}")

            # Wait for next poll interval or shutdown
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(),
                    timeout=self.settings.poll_interval,
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue

        logger.info("Orders sync worker stopped")

    async def _sync_batch(self):
        """Sync a batch of orders."""
        # Refresh Materialize views first
        await self.mz.refresh_views()

        # Get cursor
        cursor = await self.mz.get_cursor(self.VIEW_NAME)
        if cursor is None:
            cursor = datetime(1970, 1, 1, tzinfo=timezone.utc)

        # Query for changed documents
        documents = await self.mz.query_orders_search_source(
            after_timestamp=cursor,
            batch_size=self.settings.batch_size,
        )

        if not documents:
            logger.debug("No new documents to sync")
            return

        logger.info(f"Syncing {len(documents)} orders to OpenSearch")

        # Transform documents for OpenSearch
        os_documents = []
        for doc in documents:
            # Convert datetime strings to ISO format for OpenSearch
            os_doc = {**doc}
            for date_field in ["delivery_window_start", "delivery_window_end", "delivery_eta"]:
                if os_doc.get(date_field):
                    # Already a string from the DB, keep as-is
                    pass

            # effective_updated_at is already a datetime
            if os_doc.get("effective_updated_at"):
                os_doc["effective_updated_at"] = os_doc["effective_updated_at"].isoformat()

            os_documents.append(os_doc)

        # Bulk upsert to OpenSearch
        success, errors = await self.os.bulk_upsert(self.os.orders_index, os_documents)
        logger.info(f"Synced {success} documents, {errors} errors")

        # Update cursor to latest timestamp
        if documents:
            latest_timestamp = max(doc["effective_updated_at"] for doc in documents)
            await self.mz.update_cursor(self.VIEW_NAME, latest_timestamp)
            logger.debug(f"Updated cursor to {latest_timestamp}")
