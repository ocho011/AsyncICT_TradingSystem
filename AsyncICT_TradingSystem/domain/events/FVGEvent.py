from dataclasses import dataclass, field
import time
from typing import Any

@dataclass
class FVGEvent:
    event_type: str
    gap: Any
    symbol: str = ""
    timeframe: str = ""
    fill_percentage: float = 0.0
    timestamp: float = field(default_factory=time.time)
