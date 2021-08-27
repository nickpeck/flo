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
        active_runtime = AsyncStream[str]

        _builtin_stdout = AsyncStream[Any]()
        await _builtin_stdout.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stdout.append(str(s))))

        _builtin_stderr = AsyncStream[Any]()
        await _builtin_stderr.subscribe(
            Subscriber[str](
                on_next = lambda s : self.stdout.append(str(s))))

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
        assert main_module.module.locals["stdout"].peek() == "hello, world!"

    def test_simple_addition(self):
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
        assert main_module.module.locals["stdout"].peek() == 17

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
        assert main_module.module.locals["stdout"].peek() == 17