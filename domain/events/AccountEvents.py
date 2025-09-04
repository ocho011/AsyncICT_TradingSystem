from dataclasses import dataclass, field
from typing import List

# A unique type identifier for this event
ACCOUNT_UPDATE_EVENT_TYPE = "ACCOUNT_UPDATE_EVENT"

@dataclass
class BalanceUpdate:
    asset: str
    wallet_balance: float
    cross_wallet_balance: float

@dataclass
class PositionUpdate:
    symbol: str
    position_amount: float
    entry_price: float
    unrealized_pnl: float

@dataclass
class AccountUpdateEvent:
    event_type: str = ACCOUNT_UPDATE_EVENT_TYPE
    balances: List[BalanceUpdate] = field(default_factory=list)
    positions: List[PositionUpdate] = field(default_factory=list)
