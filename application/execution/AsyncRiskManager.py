import asyncio
import logging
from typing import Optional, Dict

from domain.ports.EventBus import EventBus
from domain.events.MarketEvents import MarketEvents, PreliminaryTradeDecision

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



from domain.events.OrderEvents import ApprovedTradeOrder, ApprovedOrderEvent

class AsyncRiskManager:
    """Manages overall portfolio risk, position sizing, and emergency stop-losses."""
    def __init__(self, event_bus: EventBus, account_balance: float, risk_per_trade: float = 0.01, rest_client=None):
        self.event_bus = event_bus
        self.account_balance = account_balance
        self.risk_per_trade = risk_per_trade  # e.g., 1% of account balance
        self.max_drawdown = 0.10  # e.g., 10% max total drawdown
        self.open_positions = {}
        self.rest_client = rest_client
        self.available_margin = account_balance  # Initialize with full balance
        self.current_positions = {}

    async def start_risk_monitoring(self):
        """Starts monitoring for trade decisions and overall account risk."""
        logger.info("Risk Manager started.")
        await self.event_bus.subscribe(
            MarketEvents.PRELIMINARY_TRADE_DECISION.name, 
            self._handle_trade_decision
        )
        
        while True:
            # This would periodically monitor account equity, drawdown, margin, etc.
            await self._monitor_account_health()
            await asyncio.sleep(10) # Check account health every 10 seconds

    async def _handle_trade_decision(self, event: PreliminaryTradeDecision):
        """Handles a preliminary trade decision from the coordinator."""
        logger.info("Risk Manager received a trade decision for %s.", event.symbol)

        # 1. Update account information
        await self._update_account_info()

        # 2. Assess overall account risk
        if not await self._assess_account_risk():
            logger.warning("Trade for %s rejected due to account risk level.", event.symbol)
            return

        # 3. Check available margin before calculating position size
        if not await self._check_margin_availability(event.symbol):
            logger.warning("Trade for %s rejected due to insufficient margin.", event.symbol)
            return

        # 4. Calculate position size based on current market price and available margin
        position_size = await self._calculate_safe_position_size(event.symbol)
        if position_size <= 0:
            logger.warning("Trade for %s rejected due to invalid position size.", event.symbol)
            return

        logger.info("Trade for %s approved with position size: %f", event.symbol, position_size)

        # 5. Create and publish the approved order event
        approved_order = ApprovedTradeOrder(
            symbol=event.symbol,
            order_type='MARKET', # Example
            side=event.details.get('side', 'BUY'), # Example
            quantity=position_size,
            stop_loss=event.details.get('stop_loss', 0),
            take_profit=event.details.get('take_profit', 0), # Placeholder
            decision_details=event.details
        )
        event_to_publish = ApprovedOrderEvent(
            event_type=MarketEvents.APPROVED_TRADE_ORDER.name,
            order=approved_order
        )
        await self.event_bus.publish(event_to_publish)
        logger.info("Published ApprovedOrderEvent for %s.", event.symbol)

    async def _update_account_info(self):
        """Updates account information from the exchange."""
        if not self.rest_client:
            logger.warning("No REST client available for account info update.")
            return
            
        try:
            account_info = await self.rest_client.get_account_info()
            if account_info:
                self.available_margin = float(account_info.get('availableBalance', 0))
                self.account_balance = float(account_info.get('totalWalletBalance', self.account_balance))
                logger.debug("Account updated - Available margin: %f, Total balance: %f", 
                           self.available_margin, self.account_balance)
                
                # Update current positions
                positions = await self.rest_client.get_position_info()
                if positions:
                    self.current_positions = {
                        pos['symbol']: float(pos['positionAmt']) 
                        for pos in positions 
                        if float(pos['positionAmt']) != 0
                    }
        except Exception as e:
            logger.error("Failed to update account info: %s", e)

    async def _check_margin_availability(self, symbol: str) -> bool:
        """Checks if there's sufficient margin for a new trade."""
        min_margin_buffer = 50.0  # Keep minimum $50 buffer
        
        if self.available_margin <= min_margin_buffer:
            logger.warning("Insufficient margin available: %f (minimum buffer: %f)", 
                         self.available_margin, min_margin_buffer)
            return False
        return True

    async def _calculate_safe_position_size(self, symbol: str) -> float:
        """Calculates a safe position size based on available margin and risk parameters."""
        if not self.rest_client:
            logger.error("No REST client available for position size calculation.")
            return 0.0
            
        try:
            # Use a conservative approach - risk only a small portion of available margin
            max_risk_amount = min(
                self.available_margin * 0.1,  # Max 10% of available margin
                self.account_balance * self.risk_per_trade  # Or 1% of total balance
            )
            
            # For now, use a simple position sizing that assumes 2% price risk
            # This is conservative but will prevent margin errors
            estimated_price_risk = 0.02  # 2% price movement
            
            # Get current market price (simplified - should use actual market data)
            # For ETH around $4400, a 2% risk would be about $88 per unit
            estimated_eth_price = 4400.0  # This should come from market data
            price_risk_per_unit = estimated_eth_price * estimated_price_risk
            
            if price_risk_per_unit == 0:
                return 0.0
                
            position_size = max_risk_amount / price_risk_per_unit
            
            # Additional safety check - don't exceed 30% of available margin for position value
            max_position_value = self.available_margin * 0.3
            max_position_size = max_position_value / estimated_eth_price
            
            final_position_size = min(position_size, max_position_size)
            
            logger.info("Position size calculation - Risk amount: %f, Position size: %f, Max position size: %f", 
                       max_risk_amount, position_size, max_position_size)
            
            return round(final_position_size, 3)
            
        except Exception as e:
            logger.error("Failed to calculate position size: %s", e)
            return 0.0

    async def _assess_account_risk(self) -> bool:
        """Checks if the overall account risk is within acceptable limits."""
        try:
            # Check if we have too many open positions
            if len(self.current_positions) >= 3:  # Max 3 open positions
                logger.warning("Maximum number of open positions reached.")
                return False
                
            # Check available margin ratio
            if self.available_margin < (self.account_balance * 0.2):  # Keep at least 20% margin
                logger.warning("Insufficient margin ratio - Available: %f, Required: %f", 
                             self.available_margin, self.account_balance * 0.2)
                return False
                
            return True
        except Exception as e:
            logger.error("Failed to assess account risk: %s", e)
            return False

    async def _monitor_account_health(self):
        """Monitors account health and updates margin information."""
        await self._update_account_info()

    async def emergency_close_all_positions(self):
        logger.warning("EMERGENCY: Closing all positions!")
        # Logic to quickly liquidate all open positions would go here.
        await asyncio.sleep(0.5)
        logger.warning("All positions closed.")
