import asyncio
import logging
from typing import Dict
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.MarketStructure import MarketStructure
from domain.events.DataEvents import CandleEvent
from domain.events.MarketEvents import MarketEvents

logger = logging.getLogger(__name__)

class AsyncStructureBreakDetector:
    """Detects Break of Structure (BOS) and Change of Character (CHoCH) from candle events."""
    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframes = timeframes
        # For each timeframe, maintain a MarketStructure instance
        self.analyzers: Dict[str, MarketStructure] = {tf: MarketStructure() for tf in timeframes}

    async def start_detection(self):
        """Subscribes to candle events to start structure detection."""
        logger.info("AsyncStructureBreakDetector started for %s on timeframes: %s", self.symbol, self.timeframes)
        for tf in self.timeframes:
            topic = f"candle:{self.symbol}:{tf}"
            await self.event_bus.subscribe(topic, self._handle_candle_event)

    async def _handle_candle_event(self, event: CandleEvent):
        """Processes each incoming candle to detect structure changes."""
        if not event.is_closed:
            return # Process only closed candles

        analyzer = self.analyzers[event.timeframe]
        
        # 1. Detect Break of Structure (BOS)
        bos_result = analyzer.detect_break_of_structure(event)
        if bos_result:
            logger.info("BOS Detected: %s", bos_result)
            await self.event_bus.publish(MarketEvents.BOS_DETECTED, bos_result)

        # 2. Detect Change of Character (CHoCH)
        choch_result = analyzer.detect_change_of_character(event)
        if choch_result:
            logger.info("CHoCH Detected: %s", choch_result)
            await self.event_bus.publish(MarketEvents.CHOCH_DETECTED, choch_result)
