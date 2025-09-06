**프로젝트 내 'Detector' 클래스 네이밍 컨벤션 요약**

이 프로젝트에서 'Detector' 접미사가 붙은 클래스들은 단순히 이벤트를 수신하고 처리하는 것을 넘어, **능동적인 탐지(Active Detection)** 역할을 수행합니다. 이들은 일반적으로 다음 단계를 따릅니다:

1.  **이벤트 구독**: 원시 데이터 이벤트(예: `CandleEvent`)를 구독합니다.
2.  **능동적 분석 및 패턴 매칭**: 구독한 데이터를 기반으로 특정 조건이나 패턴을 능동적으로 분석하고 탐지합니다.
3.  **새로운 이벤트 발행**: 탐지된 결과를 바탕으로 더 높은 수준의 새로운 이벤트를 발행합니다.

**`AsyncStructureBreakDetector`의 역할**

`AsyncStructureBreakDetector` 또한 위 'Detector' 컨벤션을 따릅니다. 이 클래스는 시장 구조 변화(Break of Structure, BOS 및 Change of Character, CHoCH)를 탐지하는 역할을 하지만, 실제 **능동적인 탐지 로직(분석 알고리즘)**은 `AsyncMarketStructureAnalyzer` 인스턴스에 위임합니다.

즉, `AsyncStructureBreakDetector`는 `CandleEvent`를 수신하여 `AsyncMarketStructureAnalyzer`에게 분석을 요청하고, `AsyncMarketStructureAnalyzer`가 반환한 탐지 결과를 바탕으로 최종 `MarketStructureEvent`를 발행하는 조정자 역할을 수행합니다.
