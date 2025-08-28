from dataclasses import dataclass, field
import datetime
from typing import Any

@dataclass
class MacroTimeEvent:
    event_type: str # e.g., "MACRO_CYCLE_UPDATE"
    cycle_position: Any
    analysis: Any
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
