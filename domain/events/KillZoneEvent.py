from dataclasses import dataclass, field
import datetime
from typing import Any

@dataclass
class KillZoneEvent:
    event_type: str # e.g., "ZONE_STATE_CHANGE"
    zone_name: str
    new_state: Any # Could be a simple string or a state object
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
