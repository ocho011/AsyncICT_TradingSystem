import asyncio
import logging
from typing import Dict, List, Callable, Any

from domain.ports.EventBus import EventBus

# Basic logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AsyncEventBus(EventBus):
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

    async def publish(self, event: Any):
        """
        Publishes an event to the event queue.
        """
        if self._is_running:
            await self.event_queue.put(event)
        else:
            logger.warning("Event bus is not running. Event not published.")

    async def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribes a handler to a specific event type.
        The handler must be an async function (coroutine).
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"Handler {handler.__name__} subscribed to {event_type}")

    async def _dispatch_event(self, event: Any):
        """
        Dispatches an event to all subscribed handlers.
        """
        # Assumes event objects have an 'event_type' attribute.
        event_type = getattr(event, 'event_type', None)
        if event_type and event_type in self.subscribers:
            handlers = self.subscribers[event_type]
            for handler in handlers:
                try:
                    # Handlers are coroutines, so they need to be awaited
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__} for {event_type}: {e}")

    async def process_events(self):
        """
        The main event processing loop.
        This should be run as a background task.
        """
        self._is_running = True
        logger.info("Event bus is running.")
        while self._is_running:
            try:
                event = await self.event_queue.get()
                await self._dispatch_event(event)
                self.event_queue.task_done()
            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    def stop(self):
        """
        Stops the event processing loop.
        """
        self._is_running = False
        # To unblock the queue.get() if it's waiting
        # A dummy event could be put, or we can rely on task cancellation
        logger.info("Event bus stopping.")
