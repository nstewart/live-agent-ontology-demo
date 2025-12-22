"""Order lifecycle transition scenarios."""

import logging
import random
from datetime import datetime
from typing import Any

from loadgen.api_client import FreshMartAPIClient
from loadgen.data_generators import DataGenerator

logger = logging.getLogger(__name__)


class OrderLifecycleScenario:
    """Execute order status transition scenarios."""

    def __init__(
        self,
        api_client: FreshMartAPIClient,
        data_generator: DataGenerator,
    ):
        """Initialize order lifecycle scenario.

        Args:
            api_client: FreshMart API client
            data_generator: Data generator instance
        """
        self.api_client = api_client
        self.data_generator = data_generator

    async def execute(self, force_cancellation: bool = False) -> dict[str, Any]:
        """Execute order lifecycle scenario.

        With courier dispatch enabled, this scenario only handles cancellations.
        Orders can only be cancelled while in CREATED status (before courier pickup).
        Status transitions (PICKING -> DELIVERING -> COMPLETED) are handled by
        the courier dispatch system automatically.

        Args:
            force_cancellation: If True, attempt to cancel an order

        Returns:
            Result dictionary with action details
        """
        # With courier dispatch, we only cancel orders in CREATED status
        # (before they're picked up by a courier)
        if force_cancellation:
            try:
                # Only get orders in CREATED status - these can be cancelled
                orders = await self.api_client.get_orders(status="CREATED", limit=100)

                if not orders:
                    return {
                        "success": False,
                        "error": "No orders in CREATED status to cancel",
                    }

                # Select a random order to cancel
                order = random.choice(orders)
                order_id = order["order_id"]

                # Cancel the order
                await self.api_client.update_order_status(order_id, "CANCELLED")
                logger.debug(f"Cancelled order {order_id} (was CREATED)")
                return {
                    "success": True,
                    "order_id": order_id,
                    "old_status": "CREATED",
                    "new_status": "CANCELLED",
                    "action": "cancelled",
                }

            except Exception as e:
                logger.error(f"Failed to cancel order: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }
        else:
            # Without force_cancellation, this is a no-op since courier dispatch
            # handles all status transitions automatically
            return {
                "success": True,
                "action": "noop",
                "message": "Status transitions handled by courier dispatch",
            }
