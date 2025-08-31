from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any
import time

class MarketEvents(Enum):
    """Enum for all market-related events."""
    # Analysis Events
    FVG_DETECTED = auto()
    ORDER_BLOCK_DETECTED = auto()
    LIQUIDITY_SWEEP_DETECTED = auto()
    BOS_DETECTED = auto()
    CHOCH_DETECTED = auto()

    # Decision Events
    PRELIMINARY_TRADE_DECISION = auto()
    APPROVED_TRADE_ORDER = auto()

    # Execution Events
    ORDER_STATE_CHANGE = auto()


@dataclass
class MarketStructureEvent:
    symbol: str
    timeframe: str
    event_type: str  # e.g., "BOS_DETECTED", "CHOCH_DETECTED"
    data: Any
    timestamp: float = field(default_factory=time.time)


@dataclass
class PreliminaryTradeDecision:
    """Represents a potential trade identified by the Strategy Coordinator."""
    symbol: str
    timeframe: str
    decision_time: float
    scenario_name: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
