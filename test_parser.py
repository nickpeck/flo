import asyncio
from typing import Any
import unittest

from flo import AsyncStream, Subscriber, Module
from flo.FloListenerImpl import FloListenerImpl

class ParserTests(unittest.TestCase):

    def setUp(self):
        self.stdout = []
        self.stderr = []
        self.runtime = asyncio.run(self._setup_default_runtime())

    async def _setup_default_runtime(self):
        def _unwrap(i):
            while isinstance(i, AsyncStream):
                i = i.peek()
            return i

        active_runtime = AsyncStream[str]

        _builtin_stdout = AsyncStream[Any]()
        await _builtin_stdout.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stdout.append(_unwrap(str(s)))))

        _builtin_stderr = AsyncStream[Any]()
        await _builtin_stderr.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stderr.append(_unwrap(str(s)))))

        _builtin_runtime = AsyncStream[str]()
        await _builtin_runtime.subscribe(active_runtime)

        __main_module__ = Module("main", **{
            "stdout" : _builtin_stdout,
            "stderr" : _builtin_stderr,
            "rt" : _builtin_runtime
        })
        
        return __main_module__

    def test_hello_world(self):
        src = """
            module main {
                stdout <- "hello, world!"
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["hello, world!"]

    def test_single_line_comment(self):
        src = """
            module main {
                // stdout <- "hello, world!"
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == []

    def test_simple_addition(self):
        src = """
            module main {
                stdout <- 3 + 4
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['7']

    def test_simple_subtraction(self):
        src = """
            module main {
                stdout <- 3 - 4
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['-1']

    def test_simple_multi(self):
        src = """
            module main {
                stdout <- 3 * 4
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['12']

    def test_simple_division(self):
        src = """
            module main {
                stdout <- 12 / 4
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['3.0']

    def test_logical_and(self):
        src = """
            module main {
                stdout <- false and true
                stdout <- true and false
                stdout <- true and true
                stdout <- false and false
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["False", "False", "True", "False"]

    def test_logical_or(self):
        src = """
            module main {
                stdout <- false or true
                stdout <- true or false
                stdout <- true or true
                stdout <- false or false
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["True", "True", "True", "False"]

    def test_not(self):
        src = """
            module main {
                stdout <- ! true
                stdout <- ! false
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["False", "True"]

    def test_precedence_of_ops(self):
        # nb https://www.tutorialspoint.com/python/operators_precedence_example.htm
        src = """
            module main {
                stdout <- 20 + 10 * 15 / 5
                stdout <- (20 + 10) * 15 / 5
                stdout <- ((20 + 10) * 15) / 5
                stdout <- (20 + 10) * (15 / 5)
                stdout <- 15 + (10 * 15) / 5
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["50.0", "90.0", "90.0", "90.0", "45.0"]

    def test_computed_addition_bind_to_output(self):
        src = """
            module main {
                dec x : int
                dec y : int
                dec z : int = x+y
                z->stdout
                x <- 8
                y <- 9
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['17']

    def test_comparison_operators(self):
        src = """
            module main {
                stdout <- 2 > 1
                stdout <- 2 < 1
                stdout <- 2 >= 1
                stdout <- 2 <= 1
                stdout <- 2 == 1
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['True', 'False', 'True', 'False', 'False']

    def test_declare_filter(self):
        src = """
            module main {
                dec x : int
                dec z : int = {x: x >= 5}
                z->stdout
                x <- 0
                x <- 5
                x <- 6
                x <- 4
                x <- 10
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['5', '6', '10']

    def test_components(self):
        src = """
            module main {
                component adder {
                    dec input x : int
                    dec input y : int
                    dec z : int = x+y
                }
                
                dec a : adder
                a.z -> stdout
                a.x <- 8
                a.y <- 9
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['17']

if __name__ == "__main__":
    unittest.main()