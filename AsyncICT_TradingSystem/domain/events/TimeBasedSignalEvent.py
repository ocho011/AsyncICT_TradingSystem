from dataclasses import dataclass, field
import datetime
from typing import Any

@dataclass
class TimeBasedSignalEvent:
    event_type: str # e.g., "HIGH_PROBABILITY_TIME"
    signal: Any
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
