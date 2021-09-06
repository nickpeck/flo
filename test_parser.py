import asyncio
from typing import Any
import unittest

from flo import AsyncStream, Subscriber, Module, AsyncManager
from flo.FloListenerImpl import FloListenerImpl

class ParserTests(unittest.TestCase):

    def setUp(self):
        self.stdout = []
        self.stderr = []
        self.runtime = self._setup_default_runtime()
        AsyncManager.get_instance()

    def tearDown(self):
        AsyncManager.renew()

    def _setup_default_runtime(self):
        def _unwrap(i):
            while isinstance(i, AsyncStream):
                i = i.peek()
            return str(i)

        active_runtime = AsyncStream[str]

        _builtin_stdout = AsyncStream[Any]()
        _builtin_stdout.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stdout.append(_unwrap(s))))

        _builtin_stderr = AsyncStream[Any]()
        _builtin_stderr.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stderr.append(_unwrap(s))))

        _builtin_runtime = AsyncStream[str]()
        _builtin_runtime.subscribe(active_runtime)

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

    def test_tuple(self):
        src = """
            module main {
                stdout <- ("the answer is", 42)
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["('the answer is', 42)"]

    def test_tuple_containing_an_expr(self):
        src = """
            module main {
                stdout <- ("the answer is", 40 + 2)
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["('the answer is', 42)"]

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

    def test_declare_vars(self):
        src = """
            module main {
                dec {
                    MEANING_OF_LIFE : int = 42
                    greeting : str = "Hello world"
                    truthy : bool = true
                }
                stdout <- (MEANING_OF_LIFE, greeting, truthy)
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["(42, 'Hello world', True)"]

    def test_vars_are_immutable_within_scope(self):
        src = """
            module main {
                dec {
                    x : int
                    x : str
                }
            }
        """
        with self.assertRaises(Exception) as e:
            main_module = FloListenerImpl.loadString(src, self.runtime)
        assert e.exception.args == ("Variable 'x' is already defined",)

    def test_computed_addition_bind_to_output(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int
                    z : int = x+y
                }
                z->stdout
                x <- 8
                y <- 9
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['17']

    def test_computed_feedback_loop(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int = x * x
                }
                y -> stdout
                y -> x
                x <- 2
            }
        """
        with self.assertRaises(RuntimeError) as re:
            main_module = FloListenerImpl.loadString(src, self.runtime)
        assert re.exception.args == ("Cannot bind to a dependant",)

    def test_computed_feedback_loop_two_levels(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int = x * x
                    z : int = y * y
                }
                z -> stdout
                z -> x
                x <- 2
            }
        """
        with self.assertRaises(RuntimeError) as re:
            main_module = FloListenerImpl.loadString(src, self.runtime)
        assert re.exception.args == ("Cannot bind to a dependant",)

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
                dec {
                    x : int
                    z : int = x|x >= 5
                }
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

    def test_declare_join(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int
                    z : int = x & y
                }
                z->stdout
                x <- 1
                y <- 2
                x <- 3
                y <- 4
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['1', '2', '3', '4']

    def test_components(self):
        src = """
            module main {
                component adder {
                    dec {
                        input x : int
                        input y : int
                        z : int = x+y
                    }
                }
                dec a : adder
                a.z -> stdout
                a.x <- 8
                a.y <- 9
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        #print(self.stdout)
        assert self.stdout == ['17']

    def test_nested_modules1(self):
        src = """
            module main {
                module inner {
                    dec output x : str
                    x <- "hello from inner!"
                }
                stdout <- inner.x
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["hello from inner!"]

    def test_nested_modules2(self):
        src = """
            module main {
                module middle {
                    module inner {
                        dec output x : str
                        x <- "hello from inner!"
                    }
                }
                stdout <- middle.inner.x
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ["hello from inner!"]

    def test_import_func_from_python_stdlib(self):
        src = """
            module main {
                uses math
                math.ceil -> stdout
                math.ceil  <- 1.75
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['2']

    def test_import_func_from_local_module(self):
        src = """
            module main {
                uses testimport
                testimport.myfunc -> stdout
                testimport.myfunc <- ("hello","imported module!")
            }
        """
        main_module = FloListenerImpl.loadString(src, self.runtime)
        assert self.stdout == ['hello imported module!']

if __name__ == "__main__":
    unittest.main()