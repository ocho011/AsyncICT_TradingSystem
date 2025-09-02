import asyncio
import json
import logging
import websockets

from domain.ports.EventBus import EventBus
from domain.events.DataEvents import CandleEvent, CANDLE_EVENT_TYPE

logger = logging.getLogger(__name__)

class AsyncBinanceWebSocketClient:
    """Connects to Binance WebSocket streams and publishes market data events."""
    BASE_URL = "wss://fstream.binance.com/stream?streams="

    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str]):
        self.event_bus = event_bus
        self.symbol = symbol.lower()
        self.timeframes = timeframes
        self.connection = None
        self._is_running = False

    def _get_stream_url(self) -> str:
        """Constructs the URL for multiple kline streams."""
        streams = [f"{self.symbol}@kline_{tf}" for tf in self.timeframes]
        return self.BASE_URL + "/".join(streams)

    async def start(self):
        """Starts the WebSocket client and handles reconnection."""
        self._is_running = True
        url = self._get_stream_url()
        logger.info("Connecting to Binance WebSocket: %s", url)
        
        while self._is_running:
            try:
                async with websockets.connect(url) as websocket:
                    self.connection = websocket
                    logger.info("Successfully connected to Binance WebSocket.")
                    await self._listen_for_messages()
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning("WebSocket connection closed: %s. Reconnecting in 5 seconds...", e)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("An unexpected WebSocket error occurred: %s. Reconnecting in 10 seconds...", e, exc_info=True)
                await asyncio.sleep(10)

    def stop(self):
        """Stops the WebSocket client."""
        self._is_running = False
        if self.connection:
            asyncio.create_task(self.connection.close())
        logger.info("WebSocket client stopped.")

    async def _listen_for_messages(self):
        """Listens for incoming messages and passes them to the handler."""
        async for message in self.connection:
            await self._handle_message(message)

    async def _handle_message(self, message: str):
        """Parses a raw message and publishes a corresponding event."""
        try:
            data = json.loads(message)
            
            if 'stream' not in data or 'data' not in data:
                return

            stream_name = data['stream']
            kline_data = data['data']['k']

            if kline_data:
                timeframe = kline_data['i']
                candle_event = CandleEvent(
                    event_type=CANDLE_EVENT_TYPE,
                    symbol=kline_data['s'],
                    timeframe=timeframe,
                    open_time=int(kline_data['t']),
                    open=float(kline_data['o']),
                    high=float(kline_data['h']),
                    low=float(kline_data['l']),
                    close=float(kline_data['c']),
                    volume=float(kline_data['v']),
                    is_closed=bool(kline_data['x'])
                )
                await self.event_bus.publish(candle_event)
                # logger.debug("Published CandleEvent: %s", candle_event)

        except json.JSONDecodeError:
            logger.warning("Failed to decode WebSocket message: %s", message)
        except Exception as e:
            logger.error("Error handling WebSocket message: %s", e, exc_info=True)
