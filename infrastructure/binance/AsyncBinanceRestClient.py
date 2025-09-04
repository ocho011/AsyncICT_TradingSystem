import asyncio
import hmac
import hashlib
import time
import logging
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

class AsyncBinanceRestClient:
    """Handles signed REST API requests to Binance Futures."""
    BASE_URL = "https://fapi.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = aiohttp.ClientSession()

    def _generate_signature(self, query_string: str) -> str:
        """Generates the HMAC SHA256 signature for a request."""
        return hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    async def _signed_request(self, method: str, endpoint: str, params: dict = None):
        """Makes a signed HTTP request to the Binance API."""
        if params is None:
            params = {}

        # Store original params for logging, before adding signature
        original_params = params.copy()

        params['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = self._generate_signature(query_string)
        params['signature'] = signature
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key
        }

        request_kwargs = {'headers': headers}
        
        # For GET/DELETE, signature is in query params.
        # For POST/PUT, signature is in the body.
        if method.upper() in ['GET', 'DELETE']:
            request_kwargs['params'] = params
        else:
            request_kwargs['data'] = params

        try:
            logger.info("Sending API request to '%s' with params: %s", url, original_params)
            async with self.session.request(method, url, **request_kwargs) as response:
                if response.status >= 400:
                    error_details = await response.json()
                    logger.error(
                        "API request failed: %s, message='%s', url='%s', params=%s",
                        response.status, error_details.get('msg', ''), response.url, original_params
                    )
                    response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error("API request failed: %s, %s, params=%s", e.__class__.__name__, e, original_params)
            return None

    async def place_order(self, params: dict):
        """Places a new order."""
        # Example params: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '0.001'}
        return await self._signed_request("POST", "/fapi/v1/order", params)

    async def get_order(self, symbol: str, order_id: str):
        """Retrieves the status of an order."""
        params = {'symbol': symbol, 'orderId': order_id}
        return await self._signed_request("GET", "/fapi/v1/order", params)

    async def cancel_order(self, symbol: str, order_id: str):
        """Cancels an active order."""
        params = {'symbol': symbol, 'orderId': order_id}
        return await self._signed_request("DELETE", "/fapi/v1/order", params)

    async def get_open_orders(self, symbol: str):
        """Gets all open orders for a symbol."""
        params = {'symbol': symbol}
        return await self._signed_request("GET", "/fapi/v1/openOrders", params)

    async def get_account_info(self):
        """Gets account information including balance and available margin."""
        return await self._signed_request("GET", "/fapi/v2/account")

    async def get_position_info(self, symbol: str = None):
        """Gets position information. If symbol is None, returns all positions."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._signed_request("GET", "/fapi/v2/positionRisk", params)

    async def get_listen_key(self):
        """Requests a listen key for the user data stream."""
        return await self._signed_request("POST", "/fapi/v1/listenKey")

    async def close_session(self):
        """Closes the aiohttp client session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("REST client session closed.")
