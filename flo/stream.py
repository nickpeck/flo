from __future__ import annotations

import asyncio
from functools import wraps
from typing import TypeVar, Generic, Callable, Optional, List, Coroutine, Any
import traceback

T = TypeVar('T')

class Subscriber(Generic[T]):
    """AsyncStream Subscriber
    """
    def __init__(self,
        on_next: Callable[[T], Any] = lambda x : None):
        self._on_next = on_next

    async def on_next(self, value):
        """Called when a new value is communicated to the 
        subscriber by an entity it is subscribed to.
        """
        await asyncio.coroutine(self._on_next)(value)
        return self

class AsyncStream(Generic[T]):
    """Presents a stream that allows for asynchronous
    communication between multiple subscribers.
    """
    def __init__(self, head=None):
        """Initialize a AsyncStream, where head is 
        an initial value of Type T
        """
        self._v = None
        if head:
            self._v = head
        self._subscribers = []

    async def subscribe(self, subscriber: Subscriber[T]) -> AsyncStream[T]:
        """Add a new subscriber and return the stream.
        If the subscriber is already added,
        then silently return. If this stream has a value, 
        notify the subscriber.
        """
        if subscriber in self._subscribers:
            return self
        self._subscribers.append(subscriber)
        if self._v is not None:
            await subscriber.on_next(self._v)
        return self

    def peek(self) -> Optional[T]:
        """Return the current value held by the stream, which is of type T,
        or None, if nothing has been written to the stream yet.
        """
        return self._v

    async def bindTo(self, other: AsyncStream[T]) -> AsyncStream[T]:
        """Create a binding between this stream, and another stream
        of a similar type, so that the other is subscribed to events
        in this stream. Return the initial stream.
        Raise an exception if attempting to bind a stream to itself.
        """
        if other == self:
            raise Exception("AsyncStream cannot bind to itself")
        s = Subscriber[T](
            on_next = lambda head: other.write(head)
        )
        await self.subscribe(s)
        return other

    async def joinTo(self, other: AsyncStream[T]) -> AsyncStream[T]:
        """Join this stream to another stream of the same type.
        The result is a new stream that recieves events from both
        source streams.
        Raise an exception if attempting to join a stream to itself.
        """
        if other == self:
            raise Exception("AsyncStream cannot join to itself")
        joined = AsyncStream[T]()
        s1 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        await self.subscribe(s1)
        s2 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        await other.subscribe(s2)
        return joined

    async def filter(self, expr: Callable[[T], bool]) -> AsyncStream[T]:
        """Return a new stream that contains events in the source
        stream, filtered through expr.
        """
        filtered_stream = AsyncStream[T]()
        async def _next(head: T):
            if expr(head):
                await filtered_stream.write(head)
        subscriber = Subscriber(
            on_next = _next
        )
        await self.subscribe(subscriber)
        return filtered_stream

    async def write(self, item: T) -> AsyncStream[T]:
        """Write a new value to this stream, and await the
        notification of all subscribers.
        """
        self._v = item
        _head = self._v

        if self._subscribers != []:
            await asyncio.wait(
                [s.on_next(_head)
                    for s in self._subscribers])
        return self

    @staticmethod
    async def computed(func: Callable[[List[AsyncStream[T]]], T],
        dependants: List[AsyncStream[T]]) -> AsyncStream[T]:
        """Create a new stream that is based on a computed
        expression of dependent streams, so that when any of dependents
        emits a new value, the computed result is written to the
        resulting stream.
        """
        def _bind(func, *args, **kwargs):
            @wraps(func)
            def inner(*_args, **_kwags):
                _args_ = [a.peek() for a in args]
                return func(*_args_, *_args, **kwargs, **_kwags)
            return inner

        output_stream = AsyncStream[T]()
        bound_func = _bind(func, *dependants)
        async def _on_next(x):
            nonlocal bound_func
            nonlocal output_stream
            nonlocal dependants
            if None in [dep.peek() for dep in dependants]:
                return
            await output_stream.write(bound_func())

        subscriber = Subscriber[T](
            on_next= _on_next
        )

        for dep in dependants:
            await dep.subscribe(subscriber)
        return output_stream
