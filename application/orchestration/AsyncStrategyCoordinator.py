import asyncio
import logging
from collections import deque
from typing import Dict, Any

from domain.ports.EventBus import EventBus
from domain.events.FVGEvent import FVGEvent
from domain.events.OrderBlockEvent import OrderBlockEvent
from domain.events.LiquidityEvent import LiquidityEvent
from domain.events.MarketEvents import MarketEvents, PreliminaryTradeDecision

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AsyncStrategyCoordinator:
    """Coordinates signals from various analysis components to generate a final trading decision."""
    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframes = timeframes
        
        # Store recent events for correlation
        self.recent_fvg: Dict[str, deque] = {tf: deque(maxlen=10) for tf in timeframes}
        self.recent_ob: Dict[str, deque] = {tf: deque(maxlen=10) for tf in timeframes}
        self.recent_liquidity: Dict[str, deque] = {tf: deque(maxlen=10) for tf in timeframes}

    async def start_strategy_coordination(self):
        """Starts the process of listening to events and coordinating strategies."""
        logger.info("Strategy Coordinator started for symbol %s.", self.symbol)
        await self.event_bus.subscribe(MarketEvents.FVG_DETECTED.name, self._handle_fvg)
        await self.event_bus.subscribe(MarketEvents.ORDER_BLOCK_DETECTED.name, self._handle_order_block)
        await self.event_bus.subscribe(MarketEvents.LIQUIDITY_SWEEP_DETECTED.name, self._handle_liquidity_sweep)
        
        # The main loop can be used for periodic checks or can be removed if purely event-driven
        while True:
            await asyncio.sleep(5) # Example: check for combined scenarios every 5 seconds

    async def _handle_fvg(self, event: FVGEvent):
        """Handles newly detected Fair Value Gaps."""
        if event.symbol == self.symbol:
            logger.info("Coordinator received FVG event for %s on %s timeframe.", event.symbol, event.timeframe)
            self.recent_fvg[event.timeframe].append(event)
            await self._check_trade_scenario(event.timeframe)

    async def _handle_order_block(self, event: OrderBlockEvent):
        """Handles newly detected Order Blocks."""
        if event.symbol == self.symbol:
            logger.info("Coordinator received Order Block event for %s on %s timeframe.", event.symbol, event.timeframe)
            self.recent_ob[event.timeframe].append(event)
            await self._check_trade_scenario(event.timeframe)

    async def _handle_liquidity_sweep(self, event: LiquidityEvent):
        """Handles liquidity sweep events."""
        if event.symbol == self.symbol:
            logger.info("Coordinator received Liquidity Sweep event for %s on %s timeframe.", event.symbol, event.timeframe)
            self.recent_liquidity[event.timeframe].append(event)
            await self._check_trade_scenario(event.timeframe)

    async def _check_trade_scenario(self, timeframe: str):
        """
        Checks if a combination of recent events meets a predefined trading scenario.
        This is a simplified example scenario.
        Scenario: After a liquidity sweep on a higher timeframe (e.g., 15m), 
                  an FVG appears on a lower timeframe (e.g., 5m) near a recent order block.
        """
        # This logic is highly simplified and for demonstration purposes.
        # A real system would have complex, configurable scenarios.
        
        if not self.recent_liquidity[timeframe] or not self.recent_fvg[timeframe] or not self.recent_ob[timeframe]:
            return

        # Example: Get the latest events
        last_liquidity_event = self.recent_liquidity[timeframe][-1]
        last_fvg_event = self.recent_fvg[timeframe][-1]
        last_ob_event = self.recent_ob[timeframe][-1]

        # A simple time-based check: events occurred within the last minute
        current_time = asyncio.get_event_loop().time()
        time_window = 60  # 60 seconds

        if (current_time - last_liquidity_event.timestamp < time_window and
            current_time - last_fvg_event.timestamp < time_window and
            current_time - last_ob_event.timestamp < time_window):
            
            logger.info("TRADE SCENARIO MET on %s for %s!", timeframe, self.symbol)
            
            # Create a preliminary trade decision
            decision_event = PreliminaryTradeDecision(
                event_type=MarketEvents.PRELIMINARY_TRADE_DECISION.name,
                symbol=self.symbol,
                timeframe=timeframe,
                decision_time=current_time,
                scenario_name="LiquiditySweep_OB_FVG_Confirmation",
                details={
                    "liquidity_event": last_liquidity_event,
                    "fvg_event": last_fvg_event,
                    "ob_event": last_ob_event
                }
            )
            
            # Publish the decision for the Risk Manager
            await self.event_bus.publish(decision_event)
            logger.info("Published PreliminaryTradeDecision event for %s.", self.symbol)

            # Clear the events that formed the scenario to avoid re-triggering
            self.recent_liquidity[timeframe].clear()
            self.recent_fvg[timeframe].clear()
            self.recent_ob[timeframe].clear()
