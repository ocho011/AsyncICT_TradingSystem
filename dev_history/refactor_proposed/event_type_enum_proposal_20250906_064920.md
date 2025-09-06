# 이벤트 타입에 Enum 사용 제안

현재 프로젝트에서 이벤트 타입을 문자열 상수로 정의하고 있지만, 정해진 복수의 이벤트 타입이 존재하는 경우 `enum`을 사용하는 것이 여러 면에서 이점을 제공합니다.

## Enum 사용의 장점

1.  **가독성 및 자기 문서화 (Readability & Self-Documentation)**:
    *   모든 이벤트 타입이 하나의 `Enum` 클래스 내에 명확하게 정의되어 있어, 어떤 이벤트 타입들이 존재하는지 한눈에 파악하기 쉽습니다.
    *   `EventType.CANDLE_EVENT`와 같이 사용하면 코드의 의도가 더욱 명확해집니다.

2.  **타입 안정성 및 오류 방지 (Type Safety & Error Prevention)**:
    *   `Enum` 멤버를 사용하면 오타로 인한 버그를 줄일 수 있습니다. 잘못된 `Enum` 멤버를 사용하려 하면 즉시 오류가 발생하여 런타임에 예상치 못한 동작을 방지합니다.
    *   타입 힌트와 함께 사용 시 정적 분석 도구를 통해 유효하지 않은 이벤트 타입 사용을 감지할 수 있습니다.

3.  **유효성 검사 (Validation)**:
    *   특정 문자열이 유효한 이벤트 타입인지 쉽게 확인할 수 있습니다.

4.  **디버깅 용이성 (Easier Debugging)**:
    *   디버깅 시 `EventType.CANDLE_EVENT`와 같은 `Enum` 멤버를 보는 것이 단순히 문자열을 보는 것보다 더 많은 정보를 제공합니다.

5.  **코드 일관성 (Code Consistency)**:
    *   모든 이벤트 타입을 중앙에서 관리하므로, 코드 전반에 걸쳐 일관된 이벤트 타입 명명 규칙과 사용을 강제할 수 있습니다.

## 구현 예시 (개념적)

```python
# domain/events/EventTypes.py (새 파일 또는 DataEvents.py에 추가)
from enum import Enum

class EventType(Enum):
    CANDLE_EVENT = "CANDLE_EVENT"
    MARKET_STRUCTURE_BOS_DETECTED = "MARKET_STRUCTURE_BOS_DETECTED"
    # ... 프로젝트의 모든 이벤트 타입을 여기에 정의 ...
```

```python
# 이벤트 클래스에서 Enum 값 사용
class CandleEvent:
    def __init__(self, symbol: str, timeframe: str, ...):
        self.event_type = EventType.CANDLE_EVENT.value # Enum 값 사용
        # ...
```

```python
# 이벤트 버스에서 Enum 타입 힌트 및 값 사용
class AsyncEventBus:
    async def subscribe(self, event_type: EventType, handler: Callable):
        if event_type.value not in self.subscribers:
            self.subscribers[event_type.value] = []
        self.subscribers[event_type.value].append(handler)
        # ...

    async def _dispatch_event(self, event: Any):
        event_type_str = getattr(event, 'event_type', None)
        if event_type_str and event_type_str in self.subscribers:
            # ...
```

## 결론

`enum`을 사용하는 것은 프로젝트의 견고성, 가독성, 유지보수성을 크게 향상시킬 수 있는 좋은 리팩토링 방향입니다. 특히 이벤트 타입처럼 고정된 집합의 상수를 관리할 때 매우 효과적입니다.
