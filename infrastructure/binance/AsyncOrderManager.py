import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from domain.ports.EventBus import EventBus
from domain.events.MarketEvents import MarketEvents

# Assuming ApprovedTradeOrder is defined elsewhere, e.g., in the RiskManager or a shared events file.
# For now, let's redefine it here for clarity until it's centralized.
@dataclass
class ApprovedTradeOrder:
    symbol: str
    order_type: str
    side: str
    quantity: float
    stop_loss: float | None = None
    take_profit: float | None = None
    decision_details: dict | None = None

@dataclass
class OrderStateChangeEvent:
    order_id: str
    symbol: str
    status: str  # e.g., 'FILLED', 'PARTIALLY_FILLED', 'CANCELED'
    quantity: float
    filled_quantity: float
    avg_fill_price: float | None = None
    timestamp: float = field(default_factory=asyncio.get_event_loop().time)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AsyncOrderManager:
    """Handles the mechanics of placing, tracking, and cancelling orders with the exchange."""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_orders = {}

    async def start_order_processing(self):
        """Starts listening for approved orders and processes them."""
        logger.info("Order Manager started.")
        await self.event_bus.subscribe(MarketEvents.APPROVED_TRADE_ORDER, self._handle_approved_order)
        
        # This loop can be used for other tasks like tracking open orders
        while True:
            await self._track_open_orders()
            await asyncio.sleep(5) # Check order statuses every 5 seconds

    async def _handle_approved_order(self, order: ApprovedTradeOrder):
        """Receives an approved order and proceeds to execute it."""
        logger.info("Order Manager received an approved order for %s: %s %f", 
                    order.symbol, order.side, order.quantity)
        await self._execute_order(order)

    async def _execute_order(self, order: ApprovedTradeOrder):
        """Simulates placing an order with the exchange."""
        order_id = str(uuid.uuid4())
        logger.info("Placing order %s for %s...", order_id, order.symbol)
        
        # --- SIMULATION: In a real system, this would be a Binance API call ---
        await asyncio.sleep(0.2) # Simulate network latency
        
        # Assume the order is filled immediately for this simulation
        self.active_orders[order_id] = {
            'status': 'FILLED',
            'order_details': order
        }
        logger.info("Order %s for %s has been successfully placed and filled (simulated).", order_id, order.symbol)
        # --- END SIMULATION ---

        # Publish an event confirming the order state change
        order_filled_event = OrderStateChangeEvent(
            order_id=order_id,
            symbol=order.symbol,
            status='FILLED',
            quantity=order.quantity,
            filled_quantity=order.quantity,
            avg_fill_price=12345.67 # Simulated fill price
        )
        await self.event_bus.publish(MarketEvents.ORDER_STATE_CHANGE, order_filled_event)
        logger.info("Published OrderStateChangeEvent for order %s.", order_id)

    async def _track_open_orders(self):
        # In a real system, this would periodically query the exchange for the status
        # of all non-finalized orders.
        if self.active_orders:
            # logger.info("Tracking %d active order(s)...", len(self.active_orders))
            pass

    async def cancel_all_orders(self):
        logger.info("Cancelling all open orders...")
        # Logic to fetch and cancel all open orders from the exchange.
        # In this simulation, we just clear our list.
        self.active_orders.clear()
        await asyncio.sleep(0.5)
        logger.info("All open orders cancelled.")
