from dataclasses import dataclass

@dataclass
class CandleEvent:
    """Represents a single candlestick data point received from the exchange."""
    symbol: str
    timeframe: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool
