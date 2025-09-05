# AsyncTradingOrchestrator 초기화 과정 가독성 향상 제안

`AsyncTradingOrchestrator`의 `__init__` 메서드에서 구성요소 초기화 시 인자 중복으로 인한 가독성 저하 문제를 개선하기 위한 제안입니다.

## 1. 공통 컨텍스트 객체(Context Object) 또는 데이터 클래스(Dataclass) 도입

여러 컴포넌트에서 공통적으로 사용되는 인자들(예: `event_bus`, `symbol`, `timeframes`, `rest_client`)을 하나의 객체로 묶어 전달하는 방식입니다.

*   **제안**: `TradingContext`와 같은 데이터 클래스를 정의하고, 오케스트레이터 초기화 시 이 객체를 한 번 생성하여 필요한 컴포넌트들에게 전달합니다.

```python
# 예시: domain/entities/TradingContext.py
from dataclasses import dataclass
from typing import List, Any

@dataclass
class TradingContext:
    event_bus: Any # 실제 타입으로 변경
    symbol: str
    timeframes: List[str]
    rest_client: Any # 실제 타입으로 변경
    # 필요에 따라 다른 공통 인자들 추가
```

```python
# AsyncTradingOrchestrator __init__ 내 적용 예시
class AsyncTradingOrchestrator:
    def __init__(self, config_path: str = 'config.ini'):
        # ... (기존 초기화 로직) ...

        # 공통 컨텍스트 객체 생성
        self.trading_context = TradingContext(
            event_bus=self.event_bus,
            symbol=self.symbol,
            timeframes=self.timeframes,
            rest_client=self.rest_client
        )

        # 컴포넌트 초기화 시 컨텍스트 객체의 속성 사용
        self.market_structure_detector = AsyncStructureBreakDetector(
            self.trading_context.event_bus,
            self.trading_context.symbol,
            self.trading_context.timeframes
        )
        # 또는, 컴포넌트가 TradingContext 객체를 직접 받도록 변경
        # self.market_structure_detector = AsyncStructureBreakDetector(self.trading_context)
        # ...
```

*   **장점**: 각 컴포넌트의 생성자 호출 시 인자 목록이 짧아지고, 어떤 공통 컨텍스트 내에서 동작하는지 명확해집니다.

## 2. 팩토리 메서드(Factory Method) 도입

관련된 컴포넌트들을 생성하는 로직을 별도의 프라이빗 팩토리 메서드로 분리하여 `__init__` 메서드를 더 간결하게 만듭니다.

*   **제안**: `AsyncTradingOrchestrator` 내부에 `_initialize_analysis_components()`, `_initialize_execution_components()` 등과 같은 메서드를 정의합니다.

```python
class AsyncTradingOrchestrator:
    def __init__(self, config_path: str = 'config.ini'):
        # ... (기존 초기화 로직) ...

        self._initialize_analysis_components()
        self._initialize_execution_components()
        self._initialize_strategy_components()

        # ...
    
    def _initialize_analysis_components(self):
        self.market_structure_detector = AsyncStructureBreakDetector(self.event_bus, self.symbol, self.timeframes)
        self.order_block_detector = AsyncOrderBlockDetector(self.event_bus, self.symbol, self.timeframes)
        # ...
```

*   **장점**: `__init__` 메서드가 짧아지고, 각 섹션이 어떤 종류의 컴포넌트를 초기화하는지 명확해집니다.

## 3. 설정 객체 직접 전달 (제한적 사용)

일부 컴포넌트가 `config.ini`의 여러 섹션이나 많은 설정을 필요로 하는 경우, `configparser.ConfigParser` 객체 자체 또는 특정 섹션 객체를 직접 전달하는 것을 고려할 수 있습니다.

*   **주의**: 이 방법은 컴포넌트가 설정 파일의 구조에 대해 너무 많은 지식을 갖게 될 수 있으므로, 꼭 필요한 경우에만 사용하고, 가능한 한 필요한 특정 값만 전달하는 것이 좋습니다.

이러한 제안들은 `AsyncTradingOrchestrator`의 `__init__` 메서드를 더 깔끔하고 이해하기 쉽게 만들면서, 각 컴포넌트의 의존성을 명확히 하는 데 도움이 될 것입니다.
