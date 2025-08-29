from abc import ABC, abstractmethod
from typing import Any, Callable

class EventBus(ABC):
    """
    Defines the interface for an event bus.
    Domain services will depend on this abstraction.
    """

    @abstractmethod
    async def publish(self, event: Any):
        """
        Publish an event to the bus.

        Args:
            event: The event object to publish.
        """
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to subscribe to.
            handler: The coroutine function to handle the event.
        """
        raise NotImplementedError
