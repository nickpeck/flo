from __future__ import annotations

import asyncio
from functools import wraps
from typing import TypeVar, Generic, Callable, Optional, List
import traceback

T = TypeVar('T')

def bind(func, *args, **kwargs):
    @wraps(func)
    def inner(*_args, **_kwags):
        return func(*args, *_args, **kwargs, **_kwags)
    return inner

class Subscriber(Generic[T]):
    def __init__(self,
        on_next: Callable[[T], Optional[Stream[T]]] = lambda x : None):
        self.on_next = on_next

class Stream(Generic[T]):
    def __init__(self, head=None):
        self.head = None
        if head:
            self.head = head
        self.subscribers = []

    def subscribe(self, subscriber: Subscriber[T]) -> None:
        self.subscribers.append(subscriber)
        if self.head:
            subscriber.on_next(self.head)

    def peek(self) -> Optional[T]:
        return self.head

    def bindTo(self, other: Stream[T]) -> Stream[T]:
        s = Subscriber[T](
            on_next = lambda head: other.write(head)
        )
        self.subscribe(s)
        return other

    def joinTo(self, other: Stream[T]) -> Stream[T]:
        joined = Stream[T]()
        s1 = Subscriber(
            on_next = lambda head: joined.write(head)
        )
        self.subscribe(s1)
        s2 = Subscriber(
            on_next = lambda head: joined.write(head)
        )
        other.subscribe(s2)
        return joined

    def filter(self, expr: Callable[[T], bool]) -> Stream[T]:
        filtered_stream = Stream[T]()
        def _next(head: T):
            if expr(head):
                filtered_stream.write(head)
        subscriber = Subscriber(
            on_next = _next
        )
        self.subscribe(subscriber)
        return filtered_stream

    def write(self, item: T) -> Stream[T]:
        self.head = item

        '''asyncio.wait(
            [s.on_next(_head))
                for s in self.subscribers])'''
        [s.on_next(self.head) for s in self.subscribers]
        return self

    @staticmethod
    def computed(func: Callable[[List[Stream[T]]], T],
        dependants: List[Stream[T]]) -> Stream[T]:

        output_stream = Stream[T]()
        bound_func = bind(func, *dependants)
        def _on_next(x):
            # TODO check none of them have 'None' as head
            nonlocal bound_func
            nonlocal output_stream
            nonlocal dependants
            if None in [dep.peek() for dep in dependants]:
                return
            output_stream.write(bound_func())


        subscriber = Subscriber[T](
            on_next= _on_next
        )

        for dep in dependants:
            dep.subscribe(subscriber)
        return output_stream
