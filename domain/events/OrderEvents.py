from dataclasses import dataclass
from typing import Optional, Dict

from .MarketEvents import MarketEvents

@dataclass
class ApprovedTradeOrder:
    symbol: str
    order_type: str # e.g., 'MARKET', 'LIMIT'
    side: str # e.g., 'BUY', 'SELL'
    quantity: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    decision_details: Optional[Dict] = None

@dataclass
class ApprovedOrderEvent:
    event_type: str
    order: ApprovedTradeOrder