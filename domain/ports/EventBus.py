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
        Publishes an event to the event bus for asynchronous processing.

        This method places the event into the bus's processing queue where it will be
        asynchronously dispatched to all registered subscribers of the event type.
        The method returns immediately after queuing the event.

        Args:
            event: The event object to publish. Must have an 'event_type' attribute
                   that identifies the type of event for subscriber matching.

        Note:
            Event processing is asynchronous and may not happen immediately.
            Subscribers must be registered before events are published to ensure delivery.
        """
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable):
        """
        Registers a handler to receive events of a specific type.

        When an event with the specified event_type is published to the bus,
        all registered handlers for that type will be called asynchronously
        with the event as their argument.

        Args:
            event_type: The string identifier for the event type to subscribe to.
                       This should match the 'event_type' attribute of published events.
            handler: An async callable (coroutine function) that will be invoked
                    with the event object when matching events are published.
                    The handler signature should be: async def handler(event) -> None

        Note:
            Multiple handlers can be registered for the same event type.
            Handlers are called in the order they were registered.
            Handler execution is asynchronous and will not block the publisher.
        """
        raise NotImplementedError
