import asyncio
import unittest
from magicstream import Stream, Subscriber

class StreamTests(unittest.TestCase):
    def test_stream_creation(self):
        stream = Stream[int]()
        assert stream.peek() == None

    def test_stream_subscribe(self):
        async def _test():
            subscriber_called_with = None
            def _callback(i):
                nonlocal subscriber_called_with
                subscriber_called_with = i

            stream = Stream[int](10)
            subscriber = Subscriber[int](
                on_next = lambda i : _callback(i)
            )
            await stream.subscribe(subscriber)
            return subscriber_called_with
            
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())

        assert result == 10

    def test_stream_peek(self):
        stream = Stream[int](10)
        assert stream.peek() == 10

    def test_stream_bind_to(self):
        async def _test():
            stream1 = Stream[int]()
            stream2 = Stream[int]()
            await stream1.bindTo(stream2)
            await stream1.write(10)
            return stream2.peek()

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == 10

    def test_joinTo(self):
        async def _test():
            stream1 = Stream[str]()
            stream2 = Stream[str]()
            stream3 = await stream1.joinTo(stream2)

            subscriber_called_with = []
            def _callback(x):
                nonlocal subscriber_called_with
                subscriber_called_with.append(x)

            subscriber = Subscriber[int](
                on_next = lambda i : _callback(i)
            )
            await stream3.subscribe(subscriber)

            await stream1.write("bob")
            await stream2.write("holness")
            return subscriber_called_with

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == ["bob", "holness"]

    def test_filter(self):
        async def _test():
            subscriber_called_with = []
            def _callback(i):
                nonlocal subscriber_called_with
                subscriber_called_with.append(i)

            stream1 = Stream[int]()
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
            stream1 = Stream[int]()
            stream2 = Stream[int]()

            stream3 = await Stream.computed(
                lambda a,b: a.head+b.head, [stream1, stream2])

            await stream1.write(3)
            await stream2.write(4)
            return stream3.peek()

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_test())
        assert result == 7
        