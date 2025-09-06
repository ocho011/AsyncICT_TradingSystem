# EventBus 아키텍처 분석: 단일 인스턴스 vs 다중 인스턴스 구조

**날짜:** 2025-09-03 21:27:34

**작성자:** Gemini

## 분석 개요

AsyncICT_TradingSystem의 EventBus 운영 방식과 잠재적 문제점에 대한 심층 분석입니다. 특히 단일 EventBus 인스턴스의 장단점과 이벤트 큐 혼합으로 인한 처리 지연 문제를 분석합니다.

## 현재 시스템 구조 분석

### 1. EventBus 생성 및 공유 방식

#### 단일 EventBus 인스턴스 생성
```python
# AsyncTradingOrchestrator.py (29번째 줄)
class AsyncTradingOrchestrator:
    def __init__(self, config_path: str = 'config.ini'):
        self._load_config(config_path)

        # 단일 EventBus 인스턴스 생성
        self.event_bus = AsyncEventBus()

        # 모든 컴포넌트에 동일 EventBus 공유
        self.ws_client = AsyncBinanceWebSocketClient(self.event_bus, self.symbol, self.timeframes)
        self.market_structure_detector = AsyncStructureBreakDetector(self.event_bus, self.symbol, self.timeframes)
        self.order_block_detector = AsyncOrderBlockDetector(self.event_bus, self.symbol, self.timeframes)
        # ... 다른 컴포넌트들도 동일 EventBus 공유
```

#### main.py에서의 초기화
```python
# main.py (94번째 줄)
orchestrator = AsyncTradingOrchestrator(config_path='config.ini')
```

### 2. 이벤트 종류 및 빈도 분석

#### 주요 이벤트 유형 및 빈도

| 이벤트 유형 | 발행 빈도 | 발행 주체 | 설명 |
|-------------|----------|----------|------|
| `CandleEvent` | **매 초 1-10회** | WebSocket Client | 실시간 가격 데이터 |
| `OrderBlockEvent` | 분당 0-5회 | 분석 컴포넌트 | Order Block 감지 |
| `LiquidityEvent` | 분당 0-5회 | 분석 컴포넌트 | 유동성 분석 결과 |
| `FVGEvent` | 분당 0-3회 | 분석 컴포넌트 | FVG 감지 |
| `MarketStructureEvent` | 분당 0-5회 | 분석 컴포넌트 | BOS/CHoCH 감지 |
| `KillZoneEvent` | 시간당 0-24회 | 분석 컴포넌트 | 킬존 상태 변화 |
| `PreliminaryTradeDecision` | 시간당 0-10회 | 전략 코디네이터 | 거래 결정 |
| `ApprovedOrderEvent` | 시간당 0-10회 | 리스크 매니저 | 승인된 주문 |
| `OrderEvent` | 시간당 0-20회 | 주문 매니저 | 주문 상태 |

### 3. 단일 EventBus 구조의 장점

#### 3.1 단순성 및 일관성
- **단일 책임 원칙 준수**: 모든 이벤트가 하나의 중앙 집중식 큐로 관리
- **구현 간단성**: 컴포넌트 간 통신을 위한 추가 복잡성 제거
- **메모리 효율성**: 다중 큐 관리로 인한 메모리 오버헤드 감소

#### 3.2 글로벌 상태 관리 용이성
```python
# AsyncEventBus.py
class AsyncEventBus(EventBus):
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}  # 이벤트 타입별 구독자 관리
        self.event_queue: asyncio.Queue = asyncio.Queue()  # 단일 큐
        self._is_running = False
```

### 4. 단일 EventBus 구조의 문제점

#### 4.1 이벤트 큐 혼합으로 인한 처리 지연

**문제점 1: 우선순위 없는 FIFO 처리**
```python
# AsyncEventBus.py (process_events 메서드)
async def process_events(self):
    while self._is_running:
        try:
            event = await self.event_queue.get()  # 순차적 처리
            await self._dispatch_event(event)
            self.event_queue.task_done()
        except Exception as e:
            logger.error(f"Event processing error: {e}")
```

- **고빈도 이벤트(CandleEvent)가 저빈도 이벤트를 블로킹**
- 모든 이벤트가 동일한 우선순위로 처리됨
- 긴급한 거래 이벤트가 가격 데이터 처리 뒤로 밀릴 수 있음

**문제점 2: 큐 백로그 (Queue Backlog)**
```python
# 시스템 건강성 모니터링 (AsyncTradingOrchestrator.py)
async def _monitor_system_health(self):
    # 이벤트 큐 크기 체크
    queue_size = self.event_bus.event_queue.qsize()
    if queue_size > 1000:
        logger.warning(f"Event queue backlog: {queue_size}")
```

**문제점 3: 이벤트 타입별 처리 요구사항 무시**
- 실시간 가격 데이터: 밀리초 단위 처리 필요
- 거래 결정 이벤트: 빠른 응답 필요
- 로깅/모니터링 이벤트: 상대적으로 느린 처리 가능

#### 4.2 확장성 및 성능 제한

**문제점 4: 단일 병목점 (Single Point of Bottleneck)**
- 모든 이벤트가 단일 큐를 통과하므로 큐 처리량이 시스템 전체 성능 제한
- 특정 컴포넌트의 이벤트 폭증 시 전체 시스템 영향

**문제점 5: 디버깅 및 모니터링 복잡성**
- 다양한 이벤트 타입이 혼합되어 있어 특정 이벤트 추적 어려움
- 큐 크기 모니터링만으로는 이벤트 처리 상태 파악 불충분

## 대안적 설계 방안

### 1. 우선순위 기반 EventBus (Priority-Based EventBus)

```python
class PriorityAsyncEventBus(EventBus):
    def __init__(self):
        # 우선순위별 큐 생성
        self.high_priority_queue = asyncio.PriorityQueue()
        self.normal_priority_queue = asyncio.Queue()
        self.low_priority_queue = asyncio.Queue()

    async def publish(self, event: Any, priority: EventPriority = EventPriority.NORMAL):
        """우선순위 기반 이벤트 발행"""
        if priority == EventPriority.HIGH:
            await self.high_priority_queue.put((0, event))  # 긴급 이벤트
        elif priority == EventPriority.NORMAL:
            await self.normal_priority_queue.put(event)
        else:
            await self.low_priority_queue.put(event)
```

### 2. 이벤트 타입별 분리 EventBus (Typed EventBus)

```python
class TypedAsyncEventBus:
    def __init__(self):
        # 이벤트 타입별 큐 분리
        self.queues = {
            'market_data': asyncio.Queue(),
            'analysis': asyncio.Queue(),
            'trading': asyncio.Queue(),
            'execution': asyncio.Queue(),
            'monitoring': asyncio.Queue()
        }

        # 타입별 전용 처리 태스크
        self.processors = {}

    async def publish(self, event: Any, event_category: str):
        """카테고리별 큐로 이벤트 분배"""
        if event_category in self.queues:
            await self.queues[event_category].put(event)
```

### 3. 하이브리드 EventBus (Hybrid EventBus)

```python
class HybridAsyncEventBus:
    def __init__(self):
        # 실시간 이벤트용 우선순위 큐
        self.realtime_queue = asyncio.PriorityQueue()

        # 일반 이벤트용 타입별 큐
        self.typed_queues = {
            'analysis': asyncio.Queue(),
            'trading': asyncio.Queue(),
            'monitoring': asyncio.Queue()
        }
```

## 현재 시스템에서의 해결 방안

### 1. 이벤트 필터링 및 최적화

```python
# AsyncEventBus 개선 제안
class OptimizedAsyncEventBus(EventBus):
    def __init__(self):
        self.event_queue = asyncio.Queue()
        self._event_stats = {}  # 이벤트 처리 통계
        self._processing_times = {}  # 이벤트별 처리 시간 추적

    async def publish(self, event: Any):
        """이벤트 발행 시 메타데이터 추가"""
        if hasattr(event, 'event_type'):
            event._publish_time = time.time()
            event._priority = self._calculate_priority(event.event_type)

        await self.event_queue.put(event)

    def _calculate_priority(self, event_type: str) -> int:
        """이벤트 타입별 우선순위 계산"""
        priorities = {
            'CANDLE_EVENT': 1,  # 최고 우선순위
            'ORDER_STATE_CHANGE': 2,
            'PRELIMINARY_TRADE_DECISION': 3,
            'APPROVED_TRADE_ORDER': 4,
            # ... 다른 이벤트들
        }
        return priorities.get(event_type, 10)
```

### 2. 이벤트 처리 모니터링 강화

```python
# AsyncTradingOrchestrator에 추가
async def _monitor_event_processing(self):
    """이벤트 처리 모니터링"""
    while self._is_running:
        try:
            queue_size = self.event_bus.event_queue.qsize()

            # 이벤트 타입별 큐 크기 모니터링
            event_types = await self._get_event_types_in_queue()

            if queue_size > 500:
                logger.warning(f"High event queue backlog: {queue_size}")
                logger.warning(f"Event types in queue: {event_types}")

                # 긴급 이벤트 우선 처리 모드 전환
                await self._enable_priority_mode()

            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Event monitoring error: {e}")
```

### 3. 이벤트 배치 처리 (Batch Processing)

```python
# 이벤트 배치 처리로 효율성 향상
async def process_events_batch(self):
    """이벤트 배치 처리"""
    batch_size = 10
    batch_timeout = 0.1  # 100ms

    while self._is_running:
        events = []

        # 배치 수집
        try:
            while len(events) < batch_size:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=batch_timeout
                )
                events.append(event)
        except asyncio.TimeoutError:
            pass  # 배치 타임아웃

        # 배치 처리
        if events:
            await self._process_batch(events)
```

## 결론 및 권장사항

### 현재 구조의 타당성
현재 **단일 EventBus 구조는 초기 개발 단계에서는 적합**합니다:
- 구현 복잡성 낮음
- 디버깅 용이성
- 시스템 이해도 높음

### 개선이 필요한 시점
다음 조건 중 하나라도 충족되면 구조 개선 고려:
1. **이벤트 처리량 증가**: 초당 이벤트 수가 100개를 초과할 때
2. **실시간성 요구사항 강화**: 이벤트 처리 지연이 100ms를 초과할 때
3. **시스템 복잡성 증가**: 이벤트 타입이 20개를 초과할 때

### 단계적 개선 전략
1. **모니터링 강화**: 현재 이벤트 큐 상태 실시간 모니터링
2. **우선순위 시스템 도입**: 긴급 이벤트 우선 처리
3. **배치 처리 구현**: 유사 이벤트 묶음 처리
4. **타입별 큐 분리**: 필요시 이벤트 타입별 큐 분리

## 관련 파일
- `infrastructure/messaging/EventBus.py`
- `application/orchestration/AsyncTradingOrchestrator.py`
- `main.py`
- `domain/events/*.py`
