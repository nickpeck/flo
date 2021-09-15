import asyncio
import unittest
from flo import AsyncStream, Subscriber, AsyncManager

class AsyncStreamTests(unittest.TestCase):
    def setUp(self):
        AsyncManager.get_instance()

    def tearDown(self):
        AsyncManager.renew()

    def test_stream_creation(self):
        stream = AsyncStream[int]()
        assert stream.peek() == None

    def test_stream_subscribe(self):
        subscriber_called_with = None
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with = i

        stream = AsyncStream[int](10)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream.subscribe(subscriber)
        AsyncManager.get_instance().run()
        assert subscriber_called_with == 10

    def test_stream_peek(self):
        stream = AsyncStream[int](10)
        assert stream.peek() == 10

    def test_stream_bind_to(self):

        stream1 = AsyncStream[int]()
        stream2 = AsyncStream[int]()
        stream1.bind_to(stream2)
        stream1.write(10)
        AsyncManager.get_instance().run()
        result = stream2.peek()

        assert result == 10

    def test_stream_cannot_bind_to_itself(self):

        stream1 = AsyncStream[int]()
        with self.assertRaises(Exception) as e:
            stream1.bind_to(stream1)
        result = e.exception.args

        assert result == ("AsyncStream cannot bind to itself",)
            
    def test_join_to(self):
        stream1 = AsyncStream[str]()
        stream2 = AsyncStream[str]()
        stream3 = stream1.join_to(stream2)

        subscriber_called_with = []
        def _callback(x):
            nonlocal subscriber_called_with
            subscriber_called_with.append(x)

        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream3.subscribe(subscriber)

        stream1.write("hello")
        stream2.write("world")
        AsyncManager.get_instance().run()
        result = subscriber_called_with
        assert result == ["hello", "world"]

    def test_stream_cannot_join_to_itself(self):
        stream1 = AsyncStream[int]()
        with self.assertRaises(Exception) as e:
            stream1.join_to(stream1)
        assert e.exception.args == ("AsyncStream cannot join to itself",)

    def test_filter(self):
        subscriber_called_with = []
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with.append(i)

        stream1 = AsyncStream[int]()
        stream2 = stream1.filter(lambda x : x > 5)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream2.subscribe(subscriber)

        for i in range(10):
            stream1.write(i)
        AsyncManager.get_instance().run()
        result = subscriber_called_with
        assert result == [6,7,8,9]

    def test_computed(self):
        stream1 = AsyncStream[int]()
        stream2 = AsyncStream[int]()

        stream3 = AsyncStream.computed(
            lambda a,b: a+b, [stream1, stream2])

        stream1.write(3)
        stream2.write(4)
        stream1.write(2)
        stream1.write(5)
        stream2.write(6)
        AsyncManager.get_instance().run()
        result = stream3.peek()
        # nb the result is only that of the last 'state' (5 + 6)
        assert result == 11

if __name__ == "__main__":
    unittest.main()