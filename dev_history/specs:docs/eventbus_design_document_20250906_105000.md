**프로젝트 EventBus 설계 문서**

## 1. 개요

본 프로젝트는 EventBus 패턴을 핵심 통신 메커니즘으로 채택하여 시스템 컴포넌트 간의 느슨한 결합(Loose Coupling)과 비동기적인 신호 처리를 구현합니다. EventBus는 이벤트 생산자(Producer)와 소비자(Consumer) 사이의 중재자 역할을 수행하며, 시스템의 확장성, 유연성 및 유지보수성을 향상시킵니다.

## 2. EventBus 구조 및 동작 방식

### 2.1 EventBus 인터페이스 및 구현

*   **인터페이스**: `domain/ports/EventBus.py`에 정의된 `EventBus` 추상 클래스는 `publish` 및 `subscribe` 메서드를 포함하여 EventBus의 핵심 기능을 추상화합니다. 이는 도메인 계층이 인프라스트럭처 구현에 의존하지 않도록 합니다.
*   **구현**: `infrastructure/messaging/EventBus.py`에 구현된 `AsyncEventBus` 클래스는 `EventBus` 인터페이스를 상속받아 실제 EventBus 기능을 제공합니다. 내부적으로 `asyncio.Queue`를 사용하여 이벤트를 비동기적으로 처리합니다.

### 2.3 이벤트 발행 (Publishing)

*   **주체**: 이벤트 생산자 (예: 데이터 수집 모듈, 분석 모듈)
*   **메커니즘**: 생산자는 EventBus 인스턴스의 `publish(event)` 메서드를 호출하여 이벤트를 EventBus 내부의 비동기 큐(`event_queue`)에 저장합니다. 이 메서드는 이벤트를 큐에 넣은 후 즉시 반환되므로, 생산자는 블로킹되지 않습니다.

### 2.3 이벤트 구독 및 처리 (Subscribing & Handling)

*   **주체**: 이벤트 소비자 (예: 전략 모듈, 리스크 관리 모듈, 다른 분석 모듈)
*   **메커니즘**:
    *   소비자는 EventBus 인스턴스의 `subscribe(event_type, handler)` 메서드를 호출하여 특정 `event_type`에 해당하는 이벤트에 대한 핸들러 함수를 등록합니다. 등록되는 핸들러는 반드시 `async` 함수(코루틴)여야 합니다.
    *   EventBus는 `process_events()` 메서드를 통해 백그라운드에서 지속적으로 `event_queue`를 모니터링합니다.
    *   큐에서 이벤트가 추출되면, EventBus는 `_dispatch_event(event)` 메서드를 실행하여 해당 `event_type`에 등록된 모든 핸들러를 비동기적으로 호출하고 이벤트 처리를 위임합니다. 각 핸들러는 독립적으로 실행되며, EventBus의 메인 이벤트 루프를 블로킹하지 않습니다.

## 3. EventBus 접근 방식 (의존성 주입)

EventBus는 시스템의 중앙 통신 허브로서, 이벤트 생산자 및 소비자 모두에게 접근 가능해야 합니다. 본 프로젝트에서는 이를 위해 **의존성 주입(Dependency Injection)** 패턴을 사용합니다.

*   EventBus를 사용하는 컴포넌트(예: `AsyncFVGDetector`, `AsyncTradingOrchestrator`)는 초기화 과정(`__init__` 메서드)에서 EventBus 인스턴스를 속성 값으로 주입받습니다.
*   이러한 방식은 컴포넌트 간의 직접적인 의존성을 제거하고, EventBus 구현 변경 시 해당 컴포넌트의 코드 수정 없이 유연하게 대응할 수 있도록 합니다. 또한, 단위 테스트 시 Mock EventBus를 주입하여 테스트 용이성을 높입니다.

## 4. 설계의 이점

*   **느슨한 결합**: 컴포넌트들이 서로의 존재를 직접 알 필요 없이 EventBus를 통해 통신하므로, 시스템의 모듈성과 유연성이 증대됩니다.
*   **비동기 처리**: 모든 이벤트 처리 과정이 비동기적으로 이루어져, I/O 바운드 작업으로 인한 시스템 블로킹을 방지하고 전체적인 처리량을 향상시킵니다.
*   **확장성**: 새로운 이벤트 생산자나 소비자를 쉽게 추가할 수 있어 시스템 확장이 용이합니다.
*   **유지보수성**: 각 컴포넌트의 책임이 명확해지고, 변경의 영향 범위가 제한되어 코드 유지보수가 용이합니다.
