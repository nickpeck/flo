from __future__ import annotations

import asyncio
from functools import wraps
from typing import TypeVar, Generic, Callable, Optional, List, Coroutine, Any
import traceback

T = TypeVar('T')

def bind(func, *args, **kwargs):
    @wraps(func)
    def inner(*_args, **_kwags):
        return func(*args, *_args, **kwargs, **_kwags)
    return inner

class Subscriber(Generic[T]):
    def __init__(self,
        on_next: Callable[[T], Any] = lambda x : None):
        self._on_next = on_next

    async def on_next(self, value):
        await asyncio.coroutine(self._on_next)(value)
        return self

class Stream(Generic[T]):
    def __init__(self, head=None):
        self.head = None
        if head:
            self.head = head
        self.subscribers = []

    async def subscribe(self, subscriber: Subscriber[T]) -> Stream[T]:
        self.subscribers.append(subscriber)
        if self.head is not None:
            await subscriber.on_next(self.head)
        return self

    def peek(self) -> Optional[T]:
        return self.head

    async def bindTo(self, other: Stream[T]) -> Stream[T]:
        s = Subscriber[T](
            on_next = lambda head: other.write(head)
        )
        await self.subscribe(s)
        return other

    async def joinTo(self, other: Stream[T]) -> Stream[T]:
        joined = Stream[T]()
        s1 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        await self.subscribe(s1)
        s2 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        await other.subscribe(s2)
        return joined

    async def filter(self, expr: Callable[[T], bool]) -> Stream[T]:
        filtered_stream = Stream[T]()
        async def _next(head: T):
            if expr(head):
                await filtered_stream.write(head)
        subscriber = Subscriber(
            on_next = _next
        )
        await self.subscribe(subscriber)
        return filtered_stream

    async def write(self, item: T) -> Stream[T]:
        self.head = item
        _head = self.head

        if self.subscribers != []:
            await asyncio.wait(
                [s.on_next(_head)
                    for s in self.subscribers])
        return self

    @staticmethod
    async def computed(func: Callable[[List[Stream[T]]], T],
        dependants: List[Stream[T]]) -> Stream[T]:

        output_stream = Stream[T]()
        bound_func = bind(func, *dependants)
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
