import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict

from domain.ports.EventBus import EventBus
from domain.events.MarketEvents import MarketEvents
from infrastructure.binance.AsyncBinanceRestClient import AsyncBinanceRestClient

from domain.events.OrderEvents import ApprovedTradeOrder, ApprovedOrderEvent

@dataclass
class OrderStateChangeEvent:
    event_type: str
    order_id: str
    symbol: str
    status: str
    quantity: float
    filled_quantity: float
    avg_fill_price: Optional[float] = None
    timestamp: float = field(default_factory=asyncio.get_event_loop().time)

logger = logging.getLogger(__name__)

class AsyncOrderManager:
    """Handles the mechanics of placing, tracking, and cancelling orders with the exchange."""
    def __init__(self, event_bus: EventBus, rest_client: AsyncBinanceRestClient):
        self.event_bus = event_bus
        self.rest_client = rest_client
        self.active_orders = {}

    async def start_order_processing(self):
        """Starts listening for approved orders and processes them."""
        logger.info("Order Manager started.")
        await self.event_bus.subscribe(MarketEvents.APPROVED_TRADE_ORDER.name, self._handle_approved_order)
        
        while True:
            await self._track_open_orders()
            await asyncio.sleep(15) # Check order statuses every 15 seconds

    async def _handle_approved_order(self, event: ApprovedOrderEvent):
        """Receives an approved order and proceeds to execute it."""
        order = event.order
        logger.info("Order Manager received an approved order for %s: %s %f", 
                    order.symbol, order.side, order.quantity)
        await self._execute_order(order)

    async def _execute_order(self, order: ApprovedTradeOrder):
        """Places an order using the REST API client."""
        params = {
            'symbol': order.symbol,
            'side': order.side,
            'type': order.order_type,
            'quantity': order.quantity
        }
        logger.info("Placing order with params: %s", params)
        
        try:
            result = await self.rest_client.place_order(params)
            if result:
                logger.info("Successfully placed order, response: %s", result)
                self.active_orders[result['orderId']] = result
                # Publish an event confirming the order state change
                order_event = OrderStateChangeEvent(
                    event_type=MarketEvents.ORDER_STATE_CHANGE.name,
                    order_id=result['orderId'],
                    symbol=result['symbol'],
                    status=result['status'],
                    quantity=float(result['origQty']),
                    filled_quantity=float(result['executedQty']),
                    avg_fill_price=float(result.get('avgPrice', 0.0))
                )
                await self.event_bus.publish(order_event)
            else:
                logger.error("Failed to place order for %s. No result from API.", order.symbol)
        except Exception as e:
            logger.error("Exception placing order for %s: %s", order.symbol, e, exc_info=True)

    async def _track_open_orders(self):
        """Periodically checks the status of open orders."""
        if not self.active_orders:
            return
        
        logger.debug("Tracking %d active order(s)...", len(self.active_orders))
        for order_id, order_data in list(self.active_orders.items()):
            try:
                status = await self.rest_client.get_order(order_data['symbol'], order_id)
                if status and status['status'] != order_data['status']:
                    logger.info("Order %s status changed: %s -> %s", order_id, order_data['status'], status['status'])
                    self.active_orders[order_id] = status # Update status
                    # Publish change event
                    order_event = OrderStateChangeEvent(
                        event_type=MarketEvents.ORDER_STATE_CHANGE.name,
                        order_id=status['orderId'],
                        symbol=status['symbol'],
                        status=status['status'],
                        quantity=float(status['origQty']),
                        filled_quantity=float(status['executedQty']),
                        avg_fill_price=float(status.get('avgPrice', 0.0))
                    )
                    await self.event_bus.publish(order_event)

                    if status['status'] in ['FILLED', 'CANCELED', 'EXPIRED']:
                        del self.active_orders[order_id]
            except Exception as e:
                logger.error("Failed to track order %s: %s", order_id, e)

    async def cancel_all_orders(self):
        logger.warning("Cancelling all open orders...")
        # In a real scenario, you might want to fetch all open orders first
        for order_id, order_data in list(self.active_orders.items()):
            try:
                await self.rest_client.cancel_order(order_data['symbol'], order_id)
                logger.info("Cancelled order %s for %s", order_id, order_data['symbol'])
            except Exception as e:
                logger.error("Failed to cancel order %s: %s", order_id, e)
        self.active_orders.clear()
