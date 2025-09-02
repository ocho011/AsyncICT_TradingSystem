import asyncio
import logging
from typing import List, Dict
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.OrderBlock import AsyncOrderBlock, OrderBlockType
from domain.events.DataEvents import CandleEvent, CANDLE_EVENT_TYPE
from domain.events.MarketEvents import MarketEvents
from domain.events.OrderBlockEvent import OrderBlockEvent

logger = logging.getLogger(__name__)

class AsyncOrderBlockDetector:
    """Detects Order Blocks from real-time candle events."""
    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframes = timeframes
        self.candle_buffers: Dict[str, deque] = {tf: deque(maxlen=50) for tf in timeframes}

    async def start_detection(self):
        """Subscribes to candle events to start Order Block detection."""
        logger.info("AsyncOrderBlockDetector started for %s on timeframes: %s", self.symbol, self.timeframes)
        await self.event_bus.subscribe(CANDLE_EVENT_TYPE, self._handle_candle_event)

    async def _handle_candle_event(self, event: CandleEvent):
        """Processes each incoming candle to detect Order Blocks."""
        if event.symbol != self.symbol or event.timeframe not in self.timeframes:
            return

        if not event.is_closed:
            return

        buffer = self.candle_buffers[event.timeframe]
        buffer.append(event)

        # A simple placeholder logic for detecting an order block
        # e.g., a down candle followed by a large up candle
        if len(buffer) < 3:
            return

        ob_result = self._detect_order_block(list(buffer))
        if ob_result:
            logger.info("Order Block Detected: %s", ob_result)
            event_to_publish = OrderBlockEvent(
                event_type=MarketEvents.ORDER_BLOCK_DETECTED.name,
                symbol=event.symbol,
                timeframe=event.timeframe,
                order_block=ob_result
            )
            await self.event_bus.publish(event_to_publish)

    def _detect_order_block(self, candles: List[CandleEvent]) -> Dict:
        """A simplified logic to find a bullish order block."""
        # This is a placeholder. Real logic would be much more complex.
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]

        # Bullish OB: A down candle (c2) followed by a strong up candle (c3)
        # that breaks the high of the down candle.
        is_down_candle = c2.close < c2.open
        is_strong_up_candle = c3.close > c3.open and (c3.close - c3.open) > (c2.open - c2.close) * 1.5
        breaks_high = c3.close > c2.high

        if is_down_candle and is_strong_up_candle and breaks_high:
            return {
                "symbol": c2.symbol,
                "timeframe": c2.timeframe,
                "type": OrderBlockType.BULLISH.name,
                "high": c2.high,
                "low": c2.low,
                "timestamp": c2.open_time
            }
        return None
