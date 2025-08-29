from dataclasses import dataclass, field
import time
from typing import Any

@dataclass
class MarketStructureEvent:
    symbol: str
    timeframe: str
    event_type: str  # e.g., "BOS_DETECTED", "CHOCH_DETECTED"
    data: Any
    timestamp: float = field(default_factory=time.time)
