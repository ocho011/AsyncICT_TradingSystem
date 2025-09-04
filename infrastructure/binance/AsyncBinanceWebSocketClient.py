import asyncio
import json
import logging
import websockets

from domain.ports.EventBus import EventBus
from domain.events.DataEvents import CandleEvent, CANDLE_EVENT_TYPE
from domain.events.AccountEvents import AccountUpdateEvent, BalanceUpdate, PositionUpdate, ACCOUNT_UPDATE_EVENT_TYPE
from infrastructure.binance.AsyncBinanceRestClient import AsyncBinanceRestClient


logger = logging.getLogger(__name__)

class AsyncBinanceWebSocketClient:
    """Connects to Binance WebSocket streams and publishes market data and user data events."""
    BASE_URL = "wss://fstream.binance.com/stream?streams="

    def __init__(self, event_bus: EventBus, symbol: str, timeframes: list[str], rest_client: AsyncBinanceRestClient):
        self.event_bus = event_bus
        self.symbol = symbol.lower()
        self.timeframes = timeframes
        self.rest_client = rest_client
        self.connection = None
        self._is_running = False

    async def _get_stream_url(self) -> str:
        """Constructs the URL for multiple kline streams and the user data stream."""
        kline_streams = [f"{self.symbol}@kline_{tf}" for tf in self.timeframes]
        
        # Get listen key for user data stream
        listen_key_data = await self.rest_client.get_listen_key()
        if not listen_key_data or 'listenKey' not in listen_key_data:
            logger.error("Could not get listen key for user data stream.")
            # Fallback to only kline streams if listen key fails
            return self.BASE_URL + "/".join(kline_streams)
            
        listen_key = listen_key_data['listenKey']
        all_streams = kline_streams + [listen_key]
        
        return self.BASE_URL + "/".join(all_streams)

    async def start(self):
        """Starts the WebSocket client and handles reconnection."""
        self._is_running = True
        
        while self._is_running:
            try:
                url = await self._get_stream_url()
                logger.info("Connecting to Binance WebSocket: %s", url)
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
            
            if 'stream' in data: # It's a multi-stream message
                await self._handle_kline_event(data)
            elif 'e' in data: # It's a single-stream message (likely user data)
                await self._handle_user_data_event(data)

        except json.JSONDecodeError:
            logger.warning("Failed to decode WebSocket message: %s", message)
        except Exception as e:
            logger.error("Error handling WebSocket message: %s", e, exc_info=True)

    async def _handle_kline_event(self, data: dict):
        """Handles kline data events."""
        if 'data' not in data:
            return
        kline_data = data['data'].get('k')

        if kline_data:
            candle_event = CandleEvent(
                event_type=CANDLE_EVENT_TYPE,
                symbol=kline_data['s'],
                timeframe=kline_data['i'],
                open_time=int(kline_data['t']),
                open=float(kline_data['o']),
                high=float(kline_data['h']),
                low=float(kline_data['l']),
                close=float(kline_data['c']),
                volume=float(kline_data['v']),
                is_closed=bool(kline_data['x'])
            )
            await self.event_bus.publish(candle_event)

    async def _handle_user_data_event(self, data: dict):
        """Handles user data events like ACCOUNT_UPDATE."""
        event_type = data.get('e')
        if event_type == 'ACCOUNT_UPDATE':
            update_data = data.get('a', {})
            balances = [
                BalanceUpdate(
                    asset=b['a'],
                    wallet_balance=float(b['wb']),
                    cross_wallet_balance=float(b['cw'])
                ) for b in update_data.get('B', [])
            ]
            positions = [
                PositionUpdate(
                    symbol=p['s'],
                    position_amount=float(p['pa']),
                    entry_price=float(p['ep']),
                    unrealized_pnl=float(p['up'])
                ) for p in update_data.get('P', [])
            ]
            
            if balances or positions:
                account_event = AccountUpdateEvent(
                    event_type=ACCOUNT_UPDATE_EVENT_TYPE,
                    balances=balances,
                    positions=positions
                )
                await self.event_bus.publish(account_event)
                logger.info("Published AccountUpdateEvent.")
