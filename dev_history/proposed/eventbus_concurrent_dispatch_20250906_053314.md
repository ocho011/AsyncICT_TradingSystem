# AsyncEventBus `_dispatch_event` 메서드 동시 실행 제안

## 현재 구현 방식

`infrastructure/messaging/EventBus.py` 파일의 `AsyncEventBus` 클래스 내 `_dispatch_event` 메서드는 현재 다음과 같이 구현되어 있습니다.

```python
    async def _dispatch_event(self, event: Any):
        """
        Dispatches an event to all subscribed handlers.
        """
        event_type = getattr(event, 'event_type', None)
        if event_type and event_type in self.subscribers:
            handlers = self.subscribers[event_type]
            for handler in handlers:
                try:
                    # Handlers are coroutines, so they need to be awaited
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__} for {event_type}: {e}")
```

이 방식은 구독된 핸들러들을 `for` 루프 내에서 순차적으로 `await`합니다. 즉, 하나의 핸들러가 완료될 때까지 다음 핸들러의 실행을 기다립니다.

## 제안된 동시 실행 방식

핸들러들이 독립적으로 실행될 수 있고, 하나의 핸들러가 다른 핸들러의 완료를 기다릴 필요가 없는 경우, `asyncio.create_task`를 사용하여 각 핸들러를 별도의 태스크로 실행하는 방식을 고려할 수 있습니다.

제안된 `_dispatch_event` 및 헬퍼 메서드 `_run_handler`의 구현은 다음과 같습니다.

```python
    async def _dispatch_event(self, event: Any):
        """
        Dispatches an event to all subscribed handlers concurrently.
        """
        event_type = getattr(event, 'event_type', None)
        if event_type and event_type in self.subscribers:
            handlers = self.subscribers[event_type]
            # Create a list of tasks for concurrent execution
            tasks = []
            for handler in handlers:
                # Create a task for each handler
                task = asyncio.create_task(self._run_handler(handler, event, event_type))
                tasks.append(task)
            
            # Note: For an event bus, often you just fire and forget.
            # No need to await asyncio.gather(*tasks) here unless specific synchronization is required.

    async def _run_handler(self, handler: Callable, event: Any, event_type: str):
        """
        Helper method to run a single handler and catch exceptions.
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler {handler.__name__} for {event_type}: {e}")
```

## 장점

1.  **동시성(Concurrency) 향상**: 모든 핸들러가 거의 동시에 실행되기 시작하므로, 이벤트 처리의 전반적인 응답성이 향상됩니다.
2.  **비블로킹(Non-blocking)**: `_dispatch_event` 메서드는 각 핸들러 태스크가 생성된 후 즉시 반환되므로, 이벤트 디스패치 자체가 블로킹되지 않습니다. 이는 `process_events` 루프가 다음 이벤트를 더 빠르게 가져와 처리할 수 있게 합니다.
3.  **독립적인 실행**: 각 핸들러는 독립적인 태스크로 실행되므로, 하나의 핸들러에서 발생하는 예외가 다른 핸들러의 실행을 직접적으로 방해하지 않습니다.

## 고려사항

*   **실행 순서 보장 안됨**: 핸들러들이 동시에 실행되므로, 특정 핸들러가 다른 핸들러보다 먼저 완료될 것이라는 보장이 없습니다. 핸들러 간에 엄격한 실행 순서 의존성이 있다면 이 방식은 적합하지 않을 수 있습니다. (일반적으로 이벤트 핸들러는 독립적으로 설계됩니다.)
*   **예외 처리**: 각 태스크 내에서 발생하는 예외는 해당 태스크 내에서 처리되어야 합니다. `_run_handler` 헬퍼 메서드를 통해 각 태스크의 예외를 개별적으로 로깅할 수 있습니다.
*   **자원 관리**: 매우 많은 수의 핸들러가 동시에 실행될 경우, 시스템 자원(메모리, CPU) 사용량에 대한 고려가 필요할 수 있습니다.

이 변경은 `AsyncICT_TradingSystem`의 이벤트 처리 효율성을 높이는 데 기여할 수 있습니다.
