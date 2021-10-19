import asyncio
import unittest
from flo.observable import AsyncObservable, ReadWriteDelegator, Subscriber, AsyncManager

class AsyncObservableTests(unittest.TestCase):
    def setUp(self):
        AsyncManager.get_instance()

    def tearDown(self):
        AsyncManager.renew()

    def test_observable_creation(self):
        observable = AsyncObservable[int]()
        assert observable.peek() == None

    def test_observable_subscribe(self):
        subscriber_called_with = None
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with = i

        observable = AsyncObservable[int](10)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        observable.subscribe(subscriber)
        AsyncManager.get_instance().run()
        assert subscriber_called_with == 10

    def test_observable_peek(self):
        observable = AsyncObservable[int](10)
        assert observable.peek() == 10

    def test_observable_bind_to(self):

        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int]()
        observable1.bind_to(observable2)
        observable1.write(10)
        AsyncManager.get_instance().run()
        result = observable2.peek()

        assert result == 10

    def test_observable_cannot_bind_to_itself(self):

        observable1 = AsyncObservable[int]()
        with self.assertRaises(Exception) as e:
            observable1.bind_to(observable1)
        result = e.exception.args

        assert result == ("AsyncObservable cannot bind to itself",)
            
    def test_join_to(self):
        observable1 = AsyncObservable[str]()
        observable2 = AsyncObservable[str]()
        observable3 = observable1.join_to(observable2)

        subscriber_called_with = []
        def _callback(x):
            nonlocal subscriber_called_with
            subscriber_called_with.append(x)

        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        observable3.subscribe(subscriber)

        observable1.write("hello")
        observable2.write("world")
        AsyncManager.get_instance().run()
        result = subscriber_called_with
        assert result == ["hello", "world"]

    def test_observable_cannot_join_to_itself(self):
        observable1 = AsyncObservable[int]()
        with self.assertRaises(Exception) as e:
            observable1.join_to(observable1)
        assert e.exception.args == ("AsyncObservable cannot join to itself",)

    def test_filter(self):
        subscriber_called_with = []
        def _callback(i):
            nonlocal subscriber_called_with
            subscriber_called_with.append(i)

        observable1 = AsyncObservable[int]()
        observable2 = observable1.filter(lambda x : x > 5)
        subscriber = Subscriber[int](
            on_next = lambda i : _callback(i)
        )
        observable2.subscribe(subscriber)

        for i in range(10):
            observable1.write(i)
        AsyncManager.get_instance().run()
        result = subscriber_called_with
        assert result == [6,7,8,9]

    def test_computed(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int]()

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])

        observable1.write(3)
        observable2.write(4)
        observable1.write(2)
        observable1.write(5)
        observable2.write(6)
        AsyncManager.get_instance().run()
        result = observable3.peek()
        # nb the result is only that of the last 'state' (5 + 6)
        assert result == 11

    def test_computed_default_value(self):
        observable1 = AsyncObservable[int](3)
        observable2 = AsyncObservable[int](4)

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])

        AsyncManager.get_instance().run()
        result = observable3.peek()
        assert result == 7

    def test_observable_from_false(self):
        observable1 = AsyncObservable(False)
        assert observable1.peek() == False

class ReadWriteDelegateTests(unittest.TestCase):
    def test_create_delegate(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int](10)

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])
        
        delegator = ReadWriteDelegator(observable1, observable3)
        AsyncManager.get_instance().run()
        assert delegator.peek() == None

    def test_delegate_write(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int](10)

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])
        
        delegator = ReadWriteDelegator(observable1, observable3)
        delegator.write(5)
        AsyncManager.get_instance().run()
        assert delegator.peek() == 15

    def test_delegate_bind_to(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int](10)
        observable4 = AsyncObservable[int]()

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])
        
        delegator = ReadWriteDelegator(observable1, observable3)
        delegator.bind_to(observable4)
        delegator.write(5)
        AsyncManager.get_instance().run()
        assert observable4.peek() == 15

    def test_delegate_join_to(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int](10)
        observable4 = AsyncObservable[int]()

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])
        
        delegator = ReadWriteDelegator(observable1, observable3)
        observable5 = delegator.join_to(observable4)
        delegator.write(5)
        AsyncManager.get_instance().run()
        assert observable5.peek() == 15

    def test_delegate_filter(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int](10)
        observable4 = AsyncObservable[int]()

        observable3 = AsyncObservable.computed(
            lambda a,b: a+b, [observable1, observable2])
        
        delegator = ReadWriteDelegator(observable1, observable3)
        observable5 = delegator.filter(lambda v : v > 20)
        delegator.write(5)
        AsyncManager.get_instance().run()
        assert observable5.peek() == None
        delegator.write(15)
        AsyncManager.get_instance().run()
        assert observable5.peek() == 25

    def test_delegate_args_must_be_bound(self):
        observable1 = AsyncObservable[int]()
        observable2 = AsyncObservable[int]()
        with self.assertRaises(Exception) as e:
            delegator = ReadWriteDelegator(observable1, observable2)
        assert e.exception.args ==\
            ("Cannot construct a delegate, as the observables are not bound",)

if __name__ == "__main__":
    unittest.main()