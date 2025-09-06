# AsyncBinanceWebSocketClient 개선 제안

## 1. 현재 비효율성 분석

현재 `AsyncBinanceWebSocketClient`는 심볼(symbol)당 하나의 인스턴스를 생성하도록 설계되어 있습니다. 이는 다음과 같은 비효율성을 야기합니다:

*   **다중 웹소켓 연결:** 각 심볼 인스턴스가 바이낸스에 별도의 웹소켓 연결을 엽니다. 바이낸스 API는 단일 연결을 통해 여러 스트림(예: 여러 심볼의 캔들 데이터)을 동시에 구독할 수 있는 기능을 제공하지만, 현재 구조는 이를 활용하지 못합니다.
*   **중복된 리슨 키 요청 (사용자 데이터 스트림 포함 시):** 사용자 데이터 스트림을 포함하는 경우, 각 인스턴스가 자체 리슨 키를 얻으려고 시도할 수 있습니다. 리슨 키는 계정당 하나이므로, 이는 불필요한 중복 요청이 됩니다.

## 2. 개선 제안: 단일 웹소켓 연결 활용

단일 `AsyncBinanceWebSocketClient` 인스턴스를 사용하여 여러 심볼과 타임프레임, 그리고 계정의 모든 사용자 데이터 스트림을 처리하도록 개선하는 것을 제안합니다.

### 2.1. 구현 방안

1.  **`AsyncBinanceWebSocketClient` 초기화 변경:**
    *   `__init__` 메서드를 수정하여 `symbol: str` 대신 `symbols: list[str]`를 인자로 받도록 합니다.
    *   예시: `__init__(self, event_bus: EventBus, symbols: list[str], timeframes: list[str], rest_client: AsyncBinanceRestClient)`

2.  **스트림 URL 구성 로직 수정 (`_get_stream_url`):**
    *   모든 지정된 심볼과 타임프레임에 대한 캔들 데이터를 포함하는 단일 스트림 URL을 구성하도록 변경합니다.
    *   **기존:** `kline_streams = [f"{self.symbol}@kline_{tf}" for tf in self.timeframes]`
    *   **개선:** `kline_streams = [f"{s.lower()}@kline_{tf}" for s in self.symbols for tf in self.timeframes]`
    *   사용자 데이터 스트림(listenKey)은 단일 연결에 한 번만 추가되도록 합니다.

3.  **메시지 핸들링 로직 수정 (`_handle_message`, `_handle_kline_event`):**
    *   단일 스트림에서 여러 심볼의 데이터가 올 수 있으므로, 수신된 메시지의 `stream` 필드를 확인하여 어떤 심볼의 데이터인지 식별하고 적절하게 처리해야 합니다.
    *   `_handle_kline_event`에서 `data['stream']`을 파싱하여 해당 심볼을 추출하는 로직이 필요할 수 있습니다.

4.  **`AsyncBinanceWebSocketClient` 인스턴스 중앙 집중화:**
    *   `AsyncTradingOrchestrator` (또는 데이터 관리 전용 컴포넌트)에서 **단 하나의 `AsyncBinanceWebSocketClient` 인스턴스만 생성**합니다.
    *   이 단일 인스턴스에 모니터링하려는 모든 심볼과 타임프레임을 리스트 형태로 전달합니다.

### 2.2. 고려사항

*   **바이낸스 API 제한:** 바이낸스는 단일 웹소켓 연결당 구독할 수 있는 스트림 수에 제한이 있을 수 있습니다. 매우 많은 수의 심볼/타임프레임을 모니터링하는 경우, 여전히 여러 연결이 필요할 수 있지만, 현재처럼 심볼당 하나보다는 훨씬 효율적일 것입니다.
*   **로직 복잡성:** `_handle_message` 로직은 여러 심볼의 데이터를 올바른 내부 처리 로직으로 라우팅해야 하므로 약간 더 복잡해질 수 있습니다.
*   **사용자 데이터 스트림 처리:** 사용자 데이터 스트림은 계정 전체에 적용되므로, 단일 `AsyncBinanceWebSocketClient` 인스턴스에서 한 번만 구독하는 것이 가장 효율적입니다.

이러한 개선을 통해 웹소켓 연결의 효율성을 크게 높이고 시스템 자원 사용을 최적화할 수 있습니다.
