from __future__ import annotations

import asyncio
from functools import wraps
from typing import TypeVar, Generic, Callable, Optional, List, Coroutine, Any
import traceback

class AsyncManager:
    __instance__ = None
    @staticmethod
    def get_instance():
        if AsyncManager.__instance__ is None:
            AsyncManager.__instance__ = AsyncManager()
        return AsyncManager.__instance__

    @staticmethod
    def renew():
        if AsyncManager.__instance__ is not None:
            AsyncManager.__instance__.loop.close()
        AsyncManager.__instance__ = AsyncManager()
        return AsyncManager.__instance__

    def __init__(self):
        self.loop = asyncio.new_event_loop();
        self.funcs = []

    def add_async_func(self, task, arg):
        #task,args = self.loop.create_task(coro)
        #print("ADDING TASK", task, arg)
        self.funcs.append((task,arg))
        # https://stackoverflow.com/questions/51116849/asyncio-await-coroutine-more-than-once-periodic-tasks
        
        # async def wrapper(_async_func, args):
            # while True:
                # await _async_func(*args)
        # self.loop.create_task(wrapper(task, args))

    def run(self):
        #print("STARTING RUN", len(self.funcs))
        #import pprint
        #pprint.pprint(self.funcs, indent=4)
        tasks = []
        while len(self.funcs) > 0:
            while len(self.funcs) > 0:
                #pprint.pprint(self.funcs, indent=4)
                #for f, arg in self.funcs:
                #print("#", len(self.funcs))
                f, arg = self.funcs.pop(0)
                #print("!", len(self.funcs))
                tasks.append(self.loop.create_task(f(arg)))
                #await asyncio.create_task(f(arg))

            self.loop.run_until_complete(asyncio.wait(tasks))
        #print("ENDING RUN", len(self.funcs))

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
    def __init__(self, head=None, dependants=None):
        """Initialize a AsyncStream, where head is 
        an initial value of Type T
        """
        self._v = None
        if head:
            self._v = head
        self._subscribers = []
        if dependants is None:
            self._dependants = []
        else:
            self._dependants = dependants
        child_dependants = []
        for dep in self._dependants:
            try:
                child_dependants = child_dependants + dep._dependants
            except AttributeError:
                pass
        self._dependants = self._dependants + child_dependants

    def __str__(self):
        return "<AsyncStream {}>".format(self._v)

    def __repr__(self):
        return str(self)

    def subscribe(self, subscriber: Subscriber[T]) -> AsyncStream[T]:
        """Add a new subscriber and return the stream.
        If the subscriber is already added,
        then silently return. If this stream has a value, 
        notify the subscriber.
        """
        if subscriber in self._subscribers:
            return self
        self._subscribers.append(subscriber)
        if self._v is not None:
            AsyncManager.get_instance().add_async_func(
                subscriber.on_next, self._v)
            #await subscriber.on_next(self._v)
        return self

    def peek(self) -> Optional[T]:
        """Return the current value held by the stream, which is of type T,
        or None, if nothing has been written to the stream yet.
        """
        return self._v

    def bindTo(self, other: AsyncStream[T]) -> AsyncStream[T]:
        """Create a binding between this stream, and another stream
        of a similar type, so that the other is subscribed to events
        in this stream. Return the initial stream.
        Raise an exception if attempting to bind a stream to itself.
        """
        if other in self._dependants:
            raise RuntimeError("Cannot bind to a dependant")
        if other == self:
            raise Exception("AsyncStream cannot bind to itself")
        s = Subscriber[T](
            on_next = lambda head: other.write(head)
        )
        self.subscribe(s)
        return other

    def joinTo(self, other: AsyncStream[T]) -> AsyncStream[T]:
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
        self.subscribe(s1)
        #await self.subscribe(s1)
        s2 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        other.subscribe(s2)
        #await other.subscribe(s2)
        return joined

    def filter(self, expr: Callable[[T], bool]) -> AsyncStream[T]:
        """Return a new stream that contains events in the source
        stream, filtered through expr.
        """
        filtered_stream = AsyncStream[T]()
        def _next(head: T):
            truthy = expr(head)
            if truthy:
                filtered_stream.write(head)
        subscriber = Subscriber[T](
            on_next = lambda x: _next(x)
        )
        self.subscribe(subscriber)
        #await self.subscribe(subscriber)
        return filtered_stream

    def write(self, item: T) -> AsyncStream[T]:
        """Write a new value to this stream, and await the
        notification of all subscribers.
        """
        self._v = item
        _head = self._v

        if self._subscribers != []:
            for s in self._subscribers:
                AsyncManager.get_instance().add_async_func(
                    s.on_next, _head)
        return self

    @staticmethod
    def computed(func: Callable[[List[AsyncStream[T]]], T],
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

        output_stream = AsyncStream[T](None, dependants)
        bound_func = _bind(func, *dependants)
        def _on_next(x):
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

class ComputedMapped(AsyncStream):
    def __init__(self,
        head=None, dependants=None,
        func: Callable[[T], Any] = lambda x : x):
        super().__init__(head, dependants)
        self.func = func

    def write(self, item: T) -> AsyncStream[T]:
        """Write a new value to this stream, and await the
        notification of all subscribers.
        """
        self._v = self.func(item)
        _head = self._v

        if self._subscribers != []:
            for s in self._subscribers:
                AsyncManager.get_instance().add_async_func(
                    s.on_next, _head)
        return self