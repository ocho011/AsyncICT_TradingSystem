import asyncio
import logging
from typing import List, Dict, Optional
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.FairValueGap import AsyncFairValueGap, FVGData
from domain.events.DataEvents import CandleEvent
from domain.events.MarketEvents import MarketEvents

logger = logging.getLogger(__name__)

class AsyncFVGDetector:
    """Detects Fair Value Gaps from real-time candle events."""
    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframes = timeframes
        self.active_gaps: Dict[str, List[AsyncFairValueGap]] = {tf: [] for tf in timeframes}
        self.candle_buffers: Dict[str, deque] = {tf: deque(maxlen=3) for tf in timeframes}

    async def start_detection(self):
        """Subscribes to candle events to start FVG detection."""
        logger.info("AsyncFVGDetector started for %s on timeframes: %s", self.symbol, self.timeframes)
        for tf in self.timeframes:
            topic = f"candle:{self.symbol}:{tf}"
            await self.event_bus.subscribe(topic, self._handle_candle_event)

    async def _handle_candle_event(self, event: CandleEvent):
        """Processes each incoming candle to detect FVGs."""
        if not event.is_closed:
            return # Process only closed candles to avoid detecting premature FVGs

        buffer = self.candle_buffers[event.timeframe]
        buffer.append(event)

        if len(buffer) == 3:
            fvg_data = self._detect_three_candle_fvg(list(buffer))

            if fvg_data:
                # In a real system, you might want to manage gap instances differently
                # For now, we just publish an event upon detection.
                logger.info("FVG Detected on %s %s: High=%.2f, Low=%.2f", 
                            event.symbol, event.timeframe, fvg_data.high, fvg_data.low)
                
                fvg_event = {
                    "symbol": event.symbol,
                    "timeframe": event.timeframe,
                    "gap_high": fvg_data.high,
                    "gap_low": fvg_data.low,
                    "timestamp": fvg_data.timestamp
                }
                await self.event_bus.publish(MarketEvents.FVG_DETECTED, fvg_event)

    def _detect_three_candle_fvg(self, last_three_candles: List[CandleEvent]) -> Optional[FVGData]:
        """Detects an FVG from the last three closed candles."""
        first_candle, _, third_candle = last_three_candles

        # Bullish FVG: first candle's high is lower than third candle's low
        if first_candle.high < third_candle.low:
            return FVGData(high=third_candle.low, low=first_candle.high, timestamp=third_candle.open_time)

        # Bearish FVG: first candle's low is higher than third candle's high
        if first_candle.low > third_candle.high:
            return FVGData(high=first_candle.low, low=third_candle.high, timestamp=third_candle.open_time)

        return None
