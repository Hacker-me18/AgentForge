"""Event bus: bridges synchronous emitters to the async event store."""

import asyncio
import contextlib
from collections.abc import Callable

from packages.tracing.events import Event
from packages.tracing.store import EventStore

Subscriber = Callable[[Event], None]


class EventBus:
    def __init__(self, store: EventStore):
        self.store = store
        self._subscribers: list[Subscriber] = []
        self._pending: set[asyncio.Task] = set()
        # Last write task, used to serialise emissions so events from a single
        # run always land in call order (and writers never contend for SQLite).
        self._tail: asyncio.Task | None = None

    def subscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.append(subscriber)

    async def emit(self, event_type: str, run_id: str, payload: dict) -> Event:
        event = await self.store.append(Event(run_id=run_id, type=event_type, payload=payload))
        for subscriber in self._subscribers:
            subscriber(event)
        return event

    def recorder(self, run_id: str) -> Callable[[str, dict], None]:
        """Return a sync ``(event_type, payload)`` recorder bound to *run_id*.

        Suitable as the ``event_recorder`` for harness / gateway / sandbox
        components running inside an event loop.
        """

        def _record(event_type: str, payload: dict) -> None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            # Chain every write behind the previous one: task1 is awaited by
            # task2, task2 by task3 … so emissions are delivered strictly in the
            # order they were recorded, no matter how the loop interleaves I/O.
            previous = self._tail
            task = loop.create_task(self._chain(previous, event_type, run_id, payload))
            self._tail = task
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

        return _record

    async def _chain(
        self, previous: asyncio.Task | None, event_type: str, run_id: str, payload: dict
    ) -> None:
        if previous is not None:
            # A failed predecessor must not block later events.
            with contextlib.suppress(Exception):
                await previous
        await self.emit(event_type, run_id, payload)

    async def flush(self) -> None:
        """Wait until all scheduled event writes have completed."""
        while self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
