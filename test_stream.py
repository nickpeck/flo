import unittest
from magicstream import Stream, Subscriber

class StreamTests(unittest.TestCase):
    def test_stream_creation(self):
        stream = Stream[int]()
        assert stream.peek() == None

    def test_stream_subscribe(self):
        subscriber_called_with = None
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with = i

        stream = Stream[int](10)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream.subscribe(subscriber)

        assert subscriber_called_with == 10

    def test_stream_peek(self):
        stream = Stream[int](10)
        assert stream.peek() == 10

    def test_stream_bind_to(self):
        stream1 = Stream[int]()
        stream2 = Stream[int]()
        stream1.bindTo(stream2)
        stream1.write(10)
        assert stream2.peek() == 10

    def test_joinTo(self):
        stream1 = Stream[str]()
        stream2 = Stream[str]()
        stream3 = stream1.joinTo(stream2)

        subscriber_called_with = []
        def _callback(x):
            nonlocal subscriber_called_with
            subscriber_called_with.append(x)

        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream3.subscribe(subscriber)

        stream1.write("bob")
        stream2.write("holness")
        assert subscriber_called_with == ["bob", "holness"]

    def test_filter(self):
        subscriber_called_with = []
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with.append(i)

        stream1 = Stream[int]()
        stream2 = stream1.filter(lambda x : x > 5)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        stream2.subscribe(subscriber)

        for i in range(10):
            stream1.write(i)

        assert subscriber_called_with == [6,7,8,9]

    def test_computed(self):
        stream1 = Stream[int]()
        stream2 = Stream[int]()

        stream3 = Stream.computed(
            lambda a,b: a.head+b.head, [stream1, stream2])

        stream1.write(3)
        stream2.write(4)
        assert stream3.peek() == 7
        