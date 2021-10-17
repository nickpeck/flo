from __future__ import annotations

import asyncio
from functools import wraps
from typing import TypeVar, Generic, Callable, Optional, List, Any, Union

class AsyncManager:
    """Singleton instance that allows us to enqueue coroutines
    for execution
    """
    __instance__ = None
    @staticmethod
    def get_instance():
        """Return the manager instance, or create and return
        one if it does not exist.
        """
        if AsyncManager.__instance__ is None:
            AsyncManager.__instance__ = AsyncManager()
        return AsyncManager.__instance__

    @staticmethod
    def renew():
        """Reset the AsyncManager instance
        """
        if AsyncManager.__instance__ is not None:
            AsyncManager.__instance__._loop.close()
        AsyncManager.__instance__ = AsyncManager()
        return AsyncManager.__instance__

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._queue = []

    def enqueue_async(self, coro):
        """Enqueue an coroutines, as task to be executed
        on the event loop when run() is invoked.
        """
        self._queue.append(self._loop.create_task(coro))

    def run(self):
        """Schedual all tasks in the queue for execution on the
        asyncio event loop.
        """
        tasks = []
        while len(self._queue) > 0:
            while len(self._queue) > 0:
                task = self._queue.pop(0)
                tasks.append(task)
            # nb, more tasks might get added to the queue here,
            # hence the double 'while'
            self._loop.run_until_complete(asyncio.wait(tasks))

T = TypeVar('T')

class Subscriber(Generic[T]):
    """AsyncObservable Subscriber
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

class AsyncObservable(Generic[T]):
    """Presents a observable that allows for asynchronous
    updates to and from multiple subscribers.
    """
    def __init__(self, head=None, dependants=None):
        """Initialize an AsyncObservable, where head is
        an initial value of Type T
        """
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
        if isinstance(self._v, str):
            return "'{}'".format(self._v)
        return "{}".format(self._v)

    def __repr__(self):
        return str(self)

    def subscribe(self, subscriber: Subscriber[T]) -> AsyncObservable[T]:
        """Add a new subscriber and return the observable.
        If the subscriber is already added,
        then silently return. If this observable has a value,
        notify the subscriber.
        """
        if subscriber in self._subscribers:
            return self
        self._subscribers.append(subscriber)
        if self._v is not None:
            AsyncManager.get_instance().enqueue_async(
                subscriber.on_next(self._v))
        return self

    def peek(self) -> Optional[T]:
        """Return the current value held by the observable, which is of type T,
        or None, if nothing has been written to the observable yet.
        """
        return self._v

    def bind_to(self, other: AsyncObservable[T]) -> AsyncObservable[T]:
        """Create a binding between this observable, and another observable
        of a similar type, so that the other is subscribed to events
        in this observable. Return the initial observable.
        Raise an exception if attempting to bind a observable to itself.
        """
        if other in self._dependants:
            raise RuntimeError("Cannot bind to a dependant")
        if other == self:
            raise Exception("AsyncObservable cannot bind to itself")
        subscr = Subscriber[T](
            on_next = lambda head: other.write(head)
        )
        self.subscribe(subscr)
        return other

    def join_to(self, other: AsyncObservable[T]) -> AsyncObservable[T]:
        """Join this observable to another observable of the same type.
        The result is a new observable that recieves events from both
        source observables.
        Raise an exception if attempting to join a observable to itself.
        """
        if other == self:
            raise Exception("AsyncObservable cannot join to itself")
        joined = AsyncObservable[T]()
        subscr1 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        self.subscribe(subscr1)
        subscr2 = Subscriber[T](
            on_next = lambda head: joined.write(head)
        )
        other.subscribe(subscr2)
        return joined

    def filter(self, expr: Callable[[T], bool]) -> AsyncObservable[T]:
        """Return a new observable that contains events in the source
        observable, filtered through expr.
        """
        filtered_observable = AsyncObservable[T]()
        def _next(head: T):
            truthy = expr(head)
            if truthy:
                filtered_observable.write(head)
        subscriber = Subscriber[T](
            on_next = lambda x: _next(x)
        )
        self.subscribe(subscriber)
        return filtered_observable

    def write(self, item: T) -> AsyncObservable[T]:
        """Write a new value to this observable, and await the
        notification of all subscribers.
        """
        self._v = item
        _head = self._v

        if self._subscribers != []:
            for subscr in self._subscribers:
                AsyncManager.get_instance().enqueue_async(
                    subscr.on_next(_head))
        return self

    @staticmethod
    def computed(func: Callable[[List[AsyncObservable[T]]], T],
        dependants: List[AsyncObservable[T]]) -> AsyncObservable[T]:
        """Create a new observable that is based on a computed
        expression of dependent observables, so that when any of the dependents
        emits a new value, the computed result is written to the
        resulting observable.
        """
        def unwrap(i):
            while isinstance(i, AsyncObservable):
                i = i.peek()
            return i
        def _bind(func, *args, **kwargs):
            @wraps(func)
            def inner(*_args, **_kwags):
                _args_ = [unwrap(a) for a in args]
                return func(*_args_, *_args, **kwargs, **_kwags)
            return inner

        output_observable = AsyncObservable[T](None, dependants)
        bound_func = _bind(func, *dependants)
        def _on_next(val):
            nonlocal bound_func
            nonlocal output_observable
            nonlocal dependants
            if None in [dep.peek() for dep in dependants]:
                return
            output_observable.write(bound_func())

        subscriber = Subscriber[T](
            on_next = _on_next
        )

        for dep in dependants:
            dep.subscribe(subscriber)

        # compute initial value, if it can be resolved
        if None not in [dep.peek() for dep in dependants]:
            output_observable.write(bound_func())

        return output_observable

class ReadWriteDelegator(AsyncObservable):
    """Construct an observable that delagtes both writes to another observable
    and reads to a computed observable into which the write
    delegate is bound.
    The outward effect, (to the consumer) is of a single observable
    which emits a modified response to each value written to it.
    """
    def __init__(self, 
        write_delegate: AsyncObservable, 
        read_delegate: AsyncObservable[T]):

        super().__init__(None, [])
        if write_delegate not in read_delegate._dependants:
            raise Exception("Cannot construct a delegate, as the observables are not bound")
        self._write_delegate = write_delegate
        self._read_delegate = read_delegate

    def write(self, item: AsyncObservable[T]) -> AsyncObservable[T]:
        self._write_delegate.write(item)
        return self

    def peek(self) -> Optional[T]:
        return self._read_delegate.peek()

    def subscribe(self, subscriber: Subscriber[T]) -> AsyncObservable[T]:
        self._read_delegate.subscribe(subscriber)
        return self

    def bind_to(self, other: AsyncObservable[T]) -> AsyncObservable[T]:
        self._read_delegate.bind_to(other)
        return other

    def join_to(self, other: AsyncObservable[T]) -> AsyncObservable[T]:
        joined = self._read_delegate.join_to(other)
        return joined

    def filter(self, expr: Callable[[T], bool]) -> AsyncObservable[T]:
        filtered = self._read_delegate.filter(expr)
        return filtered

class ComputedMapped(AsyncObservable):
    """Used as a wrapper to elevate library functions
    into observables
    """
    def __init__(self,
        head=None, dependants=None,
        func: Callable[[T], Any] = lambda x : x):
        super().__init__(head, dependants)
        self.func = func

    def write(self, item: AsyncObservable[T]) -> AsyncObservable[T]:
        """Write a new value to this observable, and await the
        notification of all subscribers.
        """
        arg = item.peek()
        if isinstance(arg, tuple):
            self._v = self.func(*[unwrap(a) for a in arg])
        else:
            self._v = self.func(unwrap(arg))
        _head = self._v

        if self._subscribers != []:
            for subscr in self._subscribers:
                AsyncManager.get_instance().enqueue_async(
                    subscr.on_next(_head))
        return self

def unwrap(i: Union[AsyncObservable|Any]):
    while isinstance(i, AsyncObservable):
        i = i.peek()
    return i
