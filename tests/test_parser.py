import asyncio
import os
from typing import Any
import unittest

from flo.observable import (AsyncObservable, Subscriber, 
     AsyncManager, unwrap)
from flo.module import Module
from flo.flobuiltins import file, socket
from flo.FloListenerImpl import FloListenerImpl
from flo.runtime import Runtime

class ParserTests(unittest.TestCase):
    class DummyRuntime(Runtime):

        def compose_main_module(self):
            self.stdout = []
            self.stderr = []
            active_runtime = AsyncObservable[str]

            _builtin_stdout = AsyncObservable[Any]()
            _builtin_stdout.subscribe(
                Subscriber[str](
                    on_next = lambda s : self.stdout.append(str(unwrap(s)))))

            _builtin_stderr = AsyncObservable[Any]()
            _builtin_stderr.subscribe(
                Subscriber[str](
                    on_next = lambda s : self.stderr.append(str(unwrap(s)))))

            _builtin_runtime = AsyncObservable[str]()
            _builtin_runtime.subscribe(active_runtime)

            self.main_module = Module("main", **{
                "stdout" : _builtin_stdout,
                "stderr" : _builtin_stderr,
                "rt" : _builtin_runtime
            })

            file.File(self.main_module).compose()

    def setUp(self):
        self.runtime = ParserTests.DummyRuntime()
        AsyncManager.get_instance()

    def tearDown(self):
        AsyncManager.renew()

    def test_hello_world(self):
        src = """
            module main {
                stdout <- "hello, world!"
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["hello, world!"]

    def test_single_line_comment(self):
        src = """
            module main {
                // stdout <- "hello, world!"
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == []

    def test_tuple(self):
        src = """
            module main {
                stdout <- ("the answer is", 42)
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["('the answer is', 42)"]

    def test_tuple_containing_an_expr(self):
        src = """
            module main {
                stdout <- ("the answer is", 40 + 2)
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["('the answer is', 42)"]

    def test_simple_addition(self):
        src = """
            module main {
                stdout <- 3 + 4
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['7']

    def test_cannot_use_self_in_expr(self):
        src = """
            module main {
                dec x = 3
                x <- x + 2
                stdout <- x
            }
        """
        with self.assertRaises(Exception) as e:
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert e.exception.args ==\
            ("Put expression violates dependancy constrants : x<-x+2",)

    def test_simple_addition_no_spaces(self):
        # nb addresses a bug with the lexer, whereby it was
        # attempting to parse '3+4' as a number
        src = """
            module main {
                stdout <- 3+4
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['7']

    def test_parsing_numbers(self):
        src = """
            module main {
                stdout <- 1 + 0.1
                stdout <- 2 + .1
                stdout <- 03 + .1
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['1.1', '2.1', '3.1']

    def test_simple_subtraction(self):
        src = """
            module main {
                stdout <- 3 - 4
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['-1']

    def test_simple_multi(self):
        src = """
            module main {
                stdout <- 3 * 4
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['12']

    def test_simple_division(self):
        src = """
            module main {
                stdout <- 12 / 4
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['3.0']

    def test_logical_and(self):
        src = """
            module main {
                stdout <- false and true
                stdout <- true and false
                stdout <- true and true
                stdout <- false and false
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["False", "False", "True", "False"]

    def test_logical_or(self):
        src = """
            module main {
                stdout <- false or true
                stdout <- true or false
                stdout <- true or true
                stdout <- false or false
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["True", "True", "True", "False"]

    def test_not(self):
        src = """
            module main {
                stdout <- ! true
                stdout <- ! false
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["False", "True"]

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
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["50.0", "90.0", "90.0", "90.0", "45.0"]

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
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["(42, 'Hello world', True)"]

    def test_declared_vars_are_observables(self):
        src = """
            module main {
                dec x = 1
                dec public y = 2
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        x_scope, x = self.runtime.main_module.locals["x"]
        assert x_scope == 'local'
        assert x.peek() == 1
        y_scope, y = self.runtime.main_module.locals["y"]
        assert y_scope == 'public'
        assert y.peek() == 2

    def test_computed_dependencies(self):
        src = """
            module main {
                dec x = 1
                dec y = x + 2
                sync {
                    stdout <- y
                    x <- 4
                    stdout <- y
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["3", "6"]

    def test_computed_dependencies_w_indexing(self):
        src = """
            module main {
                dec x = (1,2)
                dec y = x[1] // indexes should be computed
                sync {
                    stdout <- y
                    x <- (3,4)
                    stdout <- y
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["2", "4"]

    def test_computed_lambda_style_syntax(self):
        src = """
            module main {
                dec { x :: ? + 10 }
                sync {
                    x <- 3
                    stdout <- x
                    x <- 5
                    stdout <- x
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["13", "15"]

    def test_computed_lambda_style_syntax(self):
        src = """
            module main {
                dec { x :: ?[0] <- ?[1] }
                sync {
                    x <- (stdout, 1)
                    x <- (stdout, 2)
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["1", "2"]

    def test_computed_lambda_style_syntax2(self):
        src = """
            module main {
                dec  x :: ? <- "Hello world"
                x <- stdout
                // stdout <- x TODO , this will cause recursion - need to detect
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["Hello world"]

    def test_computed_lambda_style_syntax3(self):
        src = """
            module main {
                dec { x :: ?[0] -> ?[1]}
                sync {
                    x <- ("1", stdout)
                    x <- ("2", stdout)
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["1", "2"]

    def test_typings_are_optional(self):
        src = """
            module main {
                dec {
                    MEANING_OF_LIFE = 42
                    greeting = "Hello world"
                    truthy = true
                }
                stdout <- (MEANING_OF_LIFE, greeting, truthy)
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["(42, 'Hello world', True)"]

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
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert e.exception.args == ("Variable 'x' is already defined",)

    def test_computed_addition_bind_to_public(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int
                    z : int = x+y
                }
                z->stdout
                sync {
                    x <- 8
                    y <- 9
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['17']

    def test_computed_addition_bind_to_public_async(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int
                    z : int = x+y
                }
                z->stdout
                // both of these are evaluated at the same time
                x <- 8
                y <- 9
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['17', '17']

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
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
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
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
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
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['True', 'False', 'True', 'False', 'False']

    def test_declare_filter(self):
        src = """
            module main {
                dec {
                    x : int
                    z : int = x|x >= 5
                }
                z->stdout
                sync {
                    x <- 0
                    x <- 5
                    x <- 6
                    x <- 4
                    x <- 10
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['5', '6', '10']

    def test_declare_join(self):
        src = """
            module main {
                dec {
                    x : int
                    y : int
                    z : int = x & y
                }
                z->stdout
                sync {
                    x <- 1
                    y <- 2
                    x <- 3
                    y <- 4
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['1', '2', '3', '4']

    def test_list_expressions(self):
        src = """
            module main {
                stdout <- (1,2, 3 + 4)
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['(1, 2, 7)']

    def test_list_index_expressions(self):
        src = """
            module main {
                stdout <- (1,2, 3 + 4)[1]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['2']

    def test_list_index_expressions2(self):
        src = """
            module main {
                dec x = (1,2, 3 + 4)
                stdout <- x[1]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['2']

    def test_list_index_expressions_nested(self):
        src = """
            module main {
                dec x = (1,2, (3, 4))
                stdout <- x[2][0]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['3']

    def test_json_objects(self):
        src = """
            module main {
                stdout <- {"a" : 1, "b" : {"c" : "hello"}}
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["{'a': 1, 'b': {'c': 'hello'}}"]

    def test_json_object_indexing(self):
        src = """
            module main {
                stdout <- {"a" : 1, "b" : {"c" : "hello"}}["a"]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["1"]

    def test_json_object_indexing2(self):
        src = """
            module main {
                stdout <- {"a" : 1, "b" : {"c" : "hello"}}["b"]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["{'c': 'hello'}"]

    def test_json_object_indexing_nested(self):
        src = """
            module main {
                stdout <- {"a" : 1, "b" : {"c" : "hello"}}["b"]["c"]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['hello']

    def test_json_object_indexing_nested2(self):
        src = """
            module main {
                dec x = {"a" : 1, "b" : {"c" : "hello"}}
                stdout <- x["b"]["c"]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['hello']

    def test_json_object_indexing_nested3(self):
        src = """
            module main {
                dec x = {"a" : 1, "b" : (1,2,3,4)}
                stdout <- x["b"][0]
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['1']

    def test_mix_dot_lookup_and_indexing(self):
        src = """
            module main {
                component c {
                    dec public d = (1,2)
                }
                dec a : c
                dec b = a.d[1]
                stdout <- b
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['2']

    def test_components(self):
        src = """
            module main {
                component adder {
                    dec {
                        public x : int
                        public y : int
                        z : int = x+y
                    }
                }
                dec a : adder
                a.z -> stdout
                sync {
                    a.x <- 8
                    a.y <- 9
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['17']

    def test_nested_modules1(self):
        src = """
            module main {
                module inner {
                    dec public x : str
                    x <- "hello from inner!"
                }
                stdout <- inner.x
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["hello from inner!"]

    def test_nested_modules2(self):
        src = """
            module main {
                module middle {
                    module inner {
                        dec public x : str
                        x <- "hello from inner!"
                    }
                }
                stdout <- middle.inner.x
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["hello from inner!"]

    def test_import_func_from_python_stdlib(self):
        src = """
            module main {
                uses math
                math.ceil -> stdout
                math.ceil  <- 1.75
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['2']

    def test_import_func_from_local_module(self):
        src = """
            module main {
                uses testimport
                testimport.myfunc -> stdout
                testimport.myfunc <- ("hello","imported module!")
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ['hello imported module!']

    def test_file_reader_builtin(self):
        with open("test.log", "w") as f:
            f.write("hello\nfrom logfile!")
        try:
            src = """
                module main {
                    dec reader : file.reader
                    reader.readlines -> stdout
                    reader.path <- "test.log"
                }
            """
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
            assert self.runtime.stdout == ["hello\n", "from logfile!"]
        finally:
            os.remove("test.log")

    def test_file_writer_builtin(self):
        with open("test.log", "w") as f:
            f.write("")
        try:
            src = """
                module main {
                    dec writer : file.writer
                    writer.path <- "test.log"
                    writer.write <- "hello, world!"
                }
            """
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
            with open("test.log", "r") as f:
                contents = f.read()
                assert contents == "hello, world!"
        finally:
            os.remove("test.log")

    def test_file_write_append_builtin(self):
        with open("test.log", "w") as f:
            f.write("line 1")
        try:
            src = """
                module main {
                    dec writer : file.writer
                    writer.path <- "test.log"
                    writer.append <- "\nline 2"
                }
            """
            main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
            with open("test.log", "r") as f:
                contents = f.read()
                assert contents == "line 1\nline 2"
        finally:
            os.remove("test.log")

    def test_put_stmts_can_be_chained(self):
        src = """
            module main {
                dec x = 3
                dec y = 4
                stdout <- x <- y <- 8
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["8"]

    def test_bind_stmts_can_be_chained(self):
        src = """
            module main {
                dec x
                dec y
                dec z
                sync {
                    x -> y -> z
                    x <- "the message"
                    stdout <- z
                }
            }
        """
        main_module = FloListenerImpl.loadString(src,  self.runtime.main_module)
        assert self.runtime.stdout == ["the message"]


if __name__ == "__main__":
    unittest.main()