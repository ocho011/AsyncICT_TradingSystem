**프로젝트의 EventBus 중심 신호 처리 구조 및 플로우 요약**

이 프로젝트는 EventBus 패턴을 활용하여 시스템 컴포넌트 간의 느슨한 결합과 비동기적인 신호 처리를 구현합니다. 핵심 플로우는 다음과 같습니다.

1.  **이벤트 생성 및 발행 (Publishing)**:
    *   **데이터 소스**: `infrastructure/binance`와 같은 데이터 소스는 실시간 시장 데이터(캔들, 틱 등)를 수신하여 `CandleEvent`와 같은 원시 데이터 이벤트를 생성하고 EventBus에 발행합니다.
    *   **분석 모듈**: `application/analysis` 디렉토리의 'Detector' 클래스들(예: `AsyncFVGDetector`, `AsyncStructureBreakDetector`)은 원시 데이터 이벤트를 구독하여 특정 시장 패턴이나 조건을 능동적으로 탐지합니다. 탐지된 결과는 `FVGEvent`, `MarketStructureEvent` 등과 같은 새로운, 더 높은 수준의 이벤트로 EventBus에 발행됩니다.

2.  **이벤트 구독 및 처리 (Subscribing & Handling)**:
    *   **EventBus 초기화**: 시스템 시작 시 `AsyncEventBus` 인스턴스가 생성되고, `process_events()` 메서드가 백그라운드 태스크로 실행되어 이벤트 큐를 지속적으로 모니터링합니다.
    *   **핸들러 등록**: 각 컴포넌트(예: 'Detector' 클래스, 전략 모듈, 리스크 관리자)는 자신이 관심 있는 이벤트 타입에 대해 비동기 핸들러 함수를 EventBus에 등록(`subscribe`)합니다.
    *   **비동기적 디스패치**: EventBus는 큐에 들어온 이벤트를 해당 타입에 등록된 모든 핸들러에게 비동기적으로 디스패치합니다. 각 핸들러는 독립적으로 이벤트를 처리하며, 이는 발행자의 블로킹을 방지합니다.
    *   **리스크 관리 및 전략 실행**: `AsyncRiskManager`와 같은 리스크 관리 모듈은 특정 이벤트를 구독하여 리스크 지표를 업데이트하고, 전략 모듈은 분석 모듈에서 발행된 고수준의 이벤트를 구독하여 거래 신호를 생성하고 주문을 실행합니다.

3.  **오케스트레이션 (Orchestration)**:
    *   `AsyncTradingOrchestrator` 및 `AsyncStrategyCoordinator`는 EventBus를 중심으로 시스템의 전반적인 흐름을 조정합니다. 이들은 다양한 이벤트(데이터, 분석 결과, 전략 신호, 주문 상태 등)를 구독하고, 이를 바탕으로 다음 단계의 작업을 트리거하거나 다른 컴포넌트에게 명령을 발행합니다.

**결론**:
이 프로젝트의 신호 처리 구조는 EventBus를 중심으로 한 발행-구독(Publish-Subscribe) 모델을 채택하여, 데이터 수집부터 분석, 전략 실행, 리스크 관리까지의 모든 과정이 비동기적이고 느슨하게 결합된 형태로 이루어집니다. 이는 시스템의 확장성, 유연성 및 유지보수성을 높이는 데 기여합니다.
