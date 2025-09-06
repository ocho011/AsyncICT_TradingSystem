import asyncio
import logging
from typing import Dict
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.MarketStructure import AsyncMarketStructureAnalyzer
from domain.events.DataEvents import CandleEvent, CANDLE_EVENT_TYPE
from domain.events.MarketEvents import MarketEvents, MarketStructureEvent

logger = logging.getLogger(__name__)

class AsyncStructureBreakDetector:
    """Detects Break of Structure (BOS) and Change of Character (CHoCH) from candle events."""
    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframes = timeframes
        # For each timeframe, maintain a MarketStructure instance
        self.analyzers: Dict[str, AsyncMarketStructureAnalyzer] = {tf: AsyncMarketStructureAnalyzer() for tf in timeframes}

    async def start_detection(self):
        """Subscribes to candle events to start structure detection."""
        logger.info("AsyncStructureBreakDetector started for %s on timeframes: %s", self.symbol, self.timeframes)
        await self.event_bus.subscribe(CANDLE_EVENT_TYPE, self._handle_candle_event)

    async def _handle_candle_event(self, event: CandleEvent):
        """Processes each incoming candle to detect structure changes."""
        if event.symbol != self.symbol or event.timeframe not in self.timeframes:
            return

        if not event.is_closed:
            return # Process only closed candles

        analyzer = self.analyzers[event.timeframe]
        
        # 1. Detect Break of Structure (BOS)
        bos_result = await analyzer._detect_break_of_structure_async(event)
        if bos_result:
            logger.info("BOS Detected: %s", bos_result)
            bos_event = MarketStructureEvent(
                symbol=event.symbol,
                timeframe=event.timeframe,
                event_type=MarketEvents.BOS_DETECTED.name,
                data=bos_result
            )
            await self.event_bus.publish(bos_event)

        # 2. Detect Change of Character (CHoCH)
        choch_result = await analyzer._detect_change_of_character_async(event)
        if choch_result:
            logger.info("CHoCH Detected: %s", choch_result)
            choch_event = MarketStructureEvent(
                symbol=event.symbol,
                timeframe=event.timeframe,
                event_type=MarketEvents.CHOCH_DETECTED.name,
                data=choch_result
            )
            await self.event_bus.publish(choch_event)
