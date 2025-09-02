import asyncio
import logging
from typing import List, Dict
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.LiquidityPool import AsyncLiquidityPool, LiquidityType
from domain.events.DataEvents import CandleEvent, CANDLE_EVENT_TYPE
from domain.events.MarketEvents import MarketEvents
from domain.events.LiquidityEvent import LiquidityEvent

logger = logging.getLogger(__name__)

class AsyncLiquidityDetector:
    """Detects liquidity pools and sweeps from real-time candle events."""
    def __init__(self, event_bus: EventBus, symbol: str, tolerance_percent: float = 0.001):
        self.event_bus = event_bus
        self.symbol = symbol
        self.tolerance = tolerance_percent
        # Store recent swing points to detect liquidity levels
        self.swing_highs = deque(maxlen=50)
        self.swing_lows = deque(maxlen=50)

    async def start_detection(self):
        """Subscribes to candle events to start liquidity detection."""
        logger.info("AsyncLiquidityDetector started for %s", self.symbol)
        # This detector needs to operate on multiple timeframes to be effective,
        # but for simplicity, we subscribe to one high-frequency timeframe.
        await self.event_bus.subscribe(CANDLE_EVENT_TYPE, self._handle_candle_event)

    async def _handle_candle_event(self, event: CandleEvent):
        """Processes each candle to identify potential liquidity levels and sweeps."""
        if event.symbol != self.symbol or event.timeframe != '1m':
            return

        if not event.is_closed:
            return

        self._update_swing_points(event)
        await self._detect_liquidity_sweep(event)

    def _update_swing_points(self, candle: CandleEvent):
        """A simplified logic to identify and store swing highs and lows."""
        # In a real system, this would be a more robust swing detection algorithm.
        # For now, let's consider every candle's high/low as a potential point.
        self.swing_highs.append(candle.high)
        self.swing_lows.append(candle.low)

    async def _detect_liquidity_sweep(self, candle: CandleEvent):
        """Detects if the current candle swept a recent liquidity level."""
        # Check for Buy-Side Liquidity (BSL) sweep
        for high in list(self.swing_highs)[:-1]: # Exclude the most recent high
            if candle.low < high < candle.high:
                logger.info("BSL SWEEP DETECTED at %.2f for %s", high, self.symbol)
                sweep_event_data = {
                    "symbol": self.symbol,
                    "price_level": high,
                    "type": LiquidityType.BSL.name,
                    "sweep_candle": candle
                }
                event_to_publish = LiquidityEvent(
                    event_type=MarketEvents.LIQUIDITY_SWEEP_DETECTED.name,
                    symbol=self.symbol,
                    timeframe=candle.timeframe,
                    sweep_data=sweep_event_data
                )
                await self.event_bus.publish(event_to_publish)
                self.swing_highs.remove(high) # Remove the swept level
                break # Process one sweep at a time

        # Check for Sell-Side Liquidity (SSL) sweep
        for low in list(self.swing_lows)[:-1]: # Exclude the most recent low
            if candle.high > low > candle.low:
                logger.info("SSL SWEEP DETECTED at %.2f for %s", low, self.symbol)
                sweep_event_data = {
                    "symbol": self.symbol,
                    "price_level": low,
                    "type": LiquidityType.SSL.name,
                    "sweep_candle": candle
                }
                event_to_publish = LiquidityEvent(
                    event_type=MarketEvents.LIQUIDITY_SWEEP_DETECTED.name,
                    symbol=self.symbol,
                    timeframe=candle.timeframe,
                    sweep_data=sweep_event_data
                )
                await self.event_bus.publish(event_to_publish)
                self.swing_lows.remove(low) # Remove the swept level
                break
