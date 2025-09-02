from dataclasses import dataclass, field
import time
from typing import Any

@dataclass
class OrderBlockEvent:
    event_type: str
    symbol: str
    timeframe: str
    order_block: Any
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
