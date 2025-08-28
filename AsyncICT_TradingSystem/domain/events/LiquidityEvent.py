from dataclasses import dataclass, field
import time
from typing import Any

@dataclass
class LiquidityEvent:
    event_type: str
    pool: Any = None
    correlation_data: Any = None
    sweep_data: Any = None
    timestamp: float = field(default_factory=time.time)
