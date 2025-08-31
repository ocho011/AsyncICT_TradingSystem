import asyncio
import logging
import configparser
from typing import Set
import psutil # Dependency to be added

from infrastructure.messaging.EventBus import AsyncEventBus
from infrastructure.binance.AsyncBinanceWebSocketClient import AsyncBinanceWebSocketClient
from application.analysis.AsyncStructureBreakDetector import AsyncStructureBreakDetector
from application.analysis.AsyncOrderBlockDetector import AsyncOrderBlockDetector
from application.analysis.AsyncLiquidityDetector import AsyncLiquidityDetector
from application.analysis.AsyncFVGDetector import AsyncFVGDetector
from application.strategies.AsyncTimeBasedStrategy import AsyncTimeBasedStrategy
from application.orchestration.AsyncStrategyCoordinator import AsyncStrategyCoordinator
from application.execution.AsyncRiskManager import AsyncRiskManager
from infrastructure.binance.AsyncOrderManager import AsyncOrderManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AsyncTradingOrchestrator:
    """메인 거래 오케스트레이터 - 모든 비동기 컴포넌트 조정"""

    def __init__(self, config_path: str = 'config.ini'):
        self._load_config(config_path)

        self.event_bus = AsyncEventBus()
        
        # Initialize components with necessary parameters from config
        self.ws_client = AsyncBinanceWebSocketClient(self.event_bus, self.symbol, self.timeframes)
        self.market_structure_detector = AsyncStructureBreakDetector(self.event_bus, self.symbol, self.timeframes)
        self.order_block_detector = AsyncOrderBlockDetector(self.event_bus, self.symbol, self.timeframes)
        self.liquidity_detector = AsyncLiquidityDetector(self.event_bus, self.symbol)
        self.fvg_detector = AsyncFVGDetector(self.event_bus, self.symbol, self.timeframes)
        self.time_strategy = AsyncTimeBasedStrategy(self.event_bus)
        self.strategy_coordinator = AsyncStrategyCoordinator(self.event_bus, self.symbol, self.timeframes)
        self.risk_manager = AsyncRiskManager(self.event_bus, self.account_balance, risk_per_trade=self.risk_per_trade)
        self.order_manager = AsyncOrderManager(self.event_bus)

        self._main_tasks: Set[asyncio.Task] = set()
        self._is_running = False

    def _load_config(self, config_path: str):
        """Loads configuration from the .ini file."""
        config = configparser.ConfigParser()
        config.read(config_path)

        # Binance API credentials
        self.api_key = config.get('binance', 'api_key')
        self.api_secret = config.get('binance', 'api_secret')

        # Trading settings
        self.symbol = config.get('trading', 'symbol')
        self.timeframes = [tf.strip() for tf in config.get('trading', 'timeframes').split(',')]
        self.risk_per_trade = config.getfloat('trading', 'risk_per_trade')

        # Account settings
        self.account_balance = config.getfloat('account', 'balance')
        
        logger.info("Configuration loaded from %s for symbol %s", config_path, self.symbol)

    async def start_trading_system(self):
        """전체 거래 시스템 시작"""
        try:
            self._is_running = True
            logger.info("Starting all trading system components for %s...", self.symbol)

            # 이벤트 버스 및 웹소켓 클라이언트 시작
            event_bus_task = asyncio.create_task(self.event_bus.process_events())
            self._main_tasks.add(event_bus_task)
            
            ws_client_task = asyncio.create_task(self.ws_client.start())
            self._main_tasks.add(ws_client_task)

            # 각 분석/실행 컴포넌트 시작
            components_tasks = [
                asyncio.create_task(self.market_structure_detector.start_detection()),
                asyncio.create_task(self.order_block_detector.start_detection()),
                asyncio.create_task(self.liquidity_detector.start_detection()),
                asyncio.create_task(self.fvg_detector.start_detection()),
                asyncio.create_task(self.time_strategy.start_time_based_analysis()),
                asyncio.create_task(self.strategy_coordinator.start_strategy_coordination()),
                asyncio.create_task(self.risk_manager.start_risk_monitoring()),
                asyncio.create_task(self.order_manager.start_order_processing())
            ]

            self._main_tasks.update(components_tasks)

            # 시스템 건강성 모니터링
            health_task = asyncio.create_task(self._monitor_system_health())
            self._main_tasks.add(health_task)

            logger.info("All components started. Trading system is live for %s.", self.symbol)
            # 모든 태스크 실행
            await asyncio.gather(*self._main_tasks)

        except Exception as e:
            logger.error(f"Critical error in trading system orchestrator: {e}", exc_info=True)
            await self.shutdown()

    async def shutdown(self):
        """시스템 우아한 종료"""
        if not self._is_running:
            return

        logger.info("Shutting down trading system...")
        self._is_running = False

        # 웹소켓 클라이언트 종료
        self.ws_client.stop()

        # 모든 진행 중인 주문 취소
        await self.order_manager.cancel_all_orders()

        # 모든 포지션 청산 (선택적)
        await self.risk_manager.emergency_close_all_positions()

        # 태스크 정리
        for task in self._main_tasks:
            if not task.done():
                task.cancel()

        # 태스크 완료 대기
        await asyncio.gather(*self._main_tasks, return_exceptions=True)

        logger.info("Trading system shutdown complete.")

    async def _check_api_health(self) -> bool:
        # Placeholder for checking connectivity to exchange APIs
        return True

    async def _handle_api_disconnection(self):
        # Placeholder for handling API disconnection
        logger.error("API disconnection detected. Attempting to reconnect...")


    async def _monitor_system_health(self):
        """시스템 건강성 모니터링"""
        while self._is_running:
            try:
                # 메모리 사용량 체크
                process = psutil.Process()
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                if memory_usage > 1000:  # 1GB 초과 시 경고
                    logger.warning(f"High memory usage: {memory_usage:.2f} MB")

                # 이벤트 큐 크기 체크
                queue_size = self.event_bus.event_queue.qsize()
                if queue_size > 1000:
                    logger.warning(f"Event queue backlog: {queue_size}")

                # API 연결 상태 체크
                api_health = await self._check_api_health()
                if not api_health:
                    logger.error("API connection unhealthy")
                    await self._handle_api_disconnection()

                await asyncio.sleep(30)  # 30초마다 체크

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}", exc_info=True)
                await asyncio.sleep(60)
