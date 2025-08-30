import asyncio
import logging
from typing import List, Set, Dict
from collections import deque

from domain.ports.EventBus import EventBus
from domain.entities.LiquidityPool import AsyncLiquidityPool, LiquidityType
from domain.events.LiquidityEvent import LiquidityEvent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AsyncLiquidityDetector:
    def __init__(self, event_bus: EventBus, tolerance_percent: float = 0.1):
        self.tolerance = tolerance_percent
        self.event_bus = event_bus
        self.active_pools: Dict[str, List[AsyncLiquidityPool]] = {}
        self._detection_tasks: Set[asyncio.Task] = set()

    async def start_multi_symbol_detection(self, symbols: List[str]):
        """다중 심볼 유동성 탐지 시작"""
        for symbol in symbols:
            task = asyncio.create_task(self._detect_liquidity_continuously(symbol))
            self._detection_tasks.add(task)

        # 심볼 간 유동성 상관관계 분석 태스크 (as per prompt)
        if "BTCUSDT" in symbols and "ETHUSDT" in symbols:
             correlation_task = asyncio.create_task(self._analyze_cross_symbol_liquidity())
             self._detection_tasks.add(correlation_task)

    async def _get_price_stream(self, symbol: str):
        # Placeholder for a real-time price update stream
        price = 100.0
        while True:
            # Simulate some price movement
            price += 0.1 * (-1 if asyncio.get_event_loop().time() % 2 > 1 else 1)
            yield {'price': price, 'timestamp': asyncio.get_event_loop().time()}
            await asyncio.sleep(0.1)

    async def _find_equal_highs_async(self, price_history: List[dict]) -> List[float]:
        # Placeholder for complex logic to find equal highs
        # This would typically involve looking for multiple tops at similar price levels
        if len(price_history) > 20 and price_history[-1]['price'] > 105:
             return [105.0]
        return []

    async def _find_equal_lows_async(self, price_history: List[dict]) -> List[float]:
        # Placeholder for complex logic to find equal lows
        if len(price_history) > 20 and price_history[-1]['price'] < 95:
            return [95.0]
        return []

    def _pool_exists(self, symbol: str, price_level: float, pool_type: LiquidityType) -> bool:
        if key := self.active_pools.get(symbol):
            for pool in key:
                if pool.price_level == price_level and pool.pool_type == pool_type and not pool.is_swept:
                    return True
        return False

    async def _add_pool(self, symbol: str, pool: AsyncLiquidityPool):
        if symbol not in self.active_pools:
            self.active_pools[symbol] = []
        self.active_pools[symbol].append(pool)
        logger.info(f"New liquidity pool added for {symbol} at {pool.price_level} ({pool.pool_type})")
        await self.event_bus.publish(LiquidityEvent(event_type="NEW_POOL_DETECTED", pool=pool))


    async def _detect_liquidity_continuously(self, symbol: str):
        """지속적인 유동성 탐지"""
        price_history = deque(maxlen=200)  # 최근 200개 가격 포인트

        async for price_update in self._get_price_stream(symbol):
            price_history.append(price_update)

            if len(price_history) >= 50:  # 최소 50개 데이터 점이 있을 때
                # 비동기로 Equal Highs/Lows 탐지
                equal_highs = await self._find_equal_highs_async(list(price_history))
                equal_lows = await self._find_equal_lows_async(list(price_history))

                # 새로운 유동성 풀 생성 및 모니터링 시작
                for high_level in equal_highs:
                    if not self._pool_exists(symbol, high_level, LiquidityType.BSL):
                        pool = AsyncLiquidityPool(high_level, LiquidityType.BSL, self.event_bus)
                        await pool.start_monitoring()
                        await self._add_pool(symbol, pool)

                for low_level in equal_lows:
                    if not self._pool_exists(symbol, low_level, LiquidityType.SSL):
                        pool = AsyncLiquidityPool(low_level, LiquidityType.SSL, self.event_bus)
                        await pool.start_monitoring()
                        await self._add_pool(symbol, pool)

    async def _calculate_liquidity_correlation(self, btc_pools, eth_pools) -> dict:
        # Placeholder for correlation logic
        await asyncio.sleep(10) # Simulate complex calculation
        return {'correlation_strength': 0.8, 'details': '...'}


    async def _analyze_cross_symbol_liquidity(self):
        """심볼 간 유동성 상관관계 분석"""
        while True:
            try:
                btc_pools = self.active_pools.get("BTCUSDT", [])
                eth_pools = self.active_pools.get("ETHUSDT", [])

                if btc_pools and eth_pools:
                    # BTC와 ETH 유동성 레벨 간 상관관계 분석
                    correlation_data = await self._calculate_liquidity_correlation(btc_pools, eth_pools)

                    if correlation_data.get('correlation_strength', 0) > 0.7:
                        await self.event_bus.publish(LiquidityEvent(
                            event_type="HIGH_CORRELATION_DETECTED",
                            correlation_data=correlation_data
                        ))
                        logger.info("High liquidity correlation detected between BTC and ETH.")

                await asyncio.sleep(60)  # 1분마다 상관관계 분석

            except Exception as e:
                logger.error(f"Cross-symbol liquidity analysis error: {e}")
                await asyncio.sleep(30)
