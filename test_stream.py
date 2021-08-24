import asyncio
import unittest
from magicstream import AsyncStream, Subscriber

class AsyncStreamTests(unittest.TestCase):
    def test_stream_creation(self):
        stream = AsyncStream[int]()
        assert stream.peek() == None

    def test_stream_subscribe(self):
        async def _test():
            subscriber_called_with = None
            def _callback(i):
                nonlocal subscriber_called_with
                subscriber_called_with = i

            stream = AsyncStream[int](10)
            subscriber = Subscriber[int](
                on_next = lambda i : _callback(i)
            )
            await stream.subscribe(subscriber)
            return subscriber_called_with
            
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())

        assert result == 10

    def test_stream_peek(self):
        stream = AsyncStream[int](10)
        assert stream.peek() == 10

    def test_stream_bind_to(self):
        async def _test():
            stream1 = AsyncStream[int]()
            stream2 = AsyncStream[int]()
            await stream1.bindTo(stream2)
            await stream1.write(10)
            return stream2.peek()

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == 10

    def test_stream_cannot_bind_to_itself(self):
        async def _test():
            stream1 = AsyncStream[int]()
            with self.assertRaises(Exception) as e:
                await stream1.bindTo(stream1)
            return e.exception.args

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == ("AsyncStream cannot bind to itself",)
            
    def test_joinTo(self):
        async def _test():
            stream1 = AsyncStream[str]()
            stream2 = AsyncStream[str]()
            stream3 = await stream1.joinTo(stream2)

            subscriber_called_with = []
            def _callback(x):
                nonlocal subscriber_called_with
                subscriber_called_with.append(x)

            subscriber = Subscriber[int](
                on_next = lambda i : _callback(i)
            )
            await stream3.subscribe(subscriber)

            await stream1.write("hello")
            await stream2.write("world")
            return subscriber_called_with

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == ["hello", "world"]

    def test_stream_cannot_join_to_itself(self):
        async def _test():
            stream1 = AsyncStream[int]()
            with self.assertRaises(Exception) as e:
                await stream1.joinTo(stream1)
            return e.exception.args

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == ("AsyncStream cannot join to itself",)

    def test_filter(self):
        async def _test():
            subscriber_called_with = []
            def _callback(i):
                nonlocal subscriber_called_with
                subscriber_called_with.append(i)

            stream1 = AsyncStream[int]()
            stream2 = await stream1.filter(lambda x : x > 5)
            subscriber = Subscriber[int](
                on_next = lambda i : _callback(i)
            )
            await stream2.subscribe(subscriber)

            for i in range(10):
                await stream1.write(i)
            return subscriber_called_with

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == [6,7,8,9]

    def test_computed(self):
        async def _test():
            stream1 = AsyncStream[int]()
            stream2 = AsyncStream[int]()

            stream3 = await AsyncStream.computed(
                lambda a,b: a+b, [stream1, stream2])

            await stream1.write(3)
            await stream2.write(4)
            await stream1.write(2)
            await stream1.write(5)
            await stream2.write(6)
            return stream3.peek()

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        # nb the result is only that of the last 'state' (5 + 6)
        assert result == 11
        