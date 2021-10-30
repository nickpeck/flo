"""Entities used as part of the runtime
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
import socket
import sys
from typing import Any, Union, Tuple

from . observable import AsyncObservable, Subscriber, AsyncManager, unwrap
from . module import Module, ModuleBuilder
from . import flobuiltins

class Runtime(Subscriber[int]):
    SIG_TERMINATE = 0

    def __init__(self):
        super().__init__()
        self.main_module = None
        self.compose_main_module()

    def _restart(self):
        pass

    def _exit(self):
        sys.exit(0)

    async def on_next(self, value: int):
        if value == self.__class__.SIG_TERMINATE:
            self._exit()
        # TODO react to value, terminate, restart etc
        pass

    def load_builtins(self):
        sub_modules = [mod_info[1] for mod_info in pkgutil.iter_modules(flobuiltins.__path__)] # type: ignore
        for mod_name in sub_modules:
            mod_name = importlib.import_module("flo.flobuiltins." + mod_name) # type: ignore
            for cls in inspect.getmembers(mod_name, inspect.isclass):
                if not cls[1].__module__.startswith('flo.flobuiltins.'):
                    continue
                if not issubclass(cls[1], ModuleBuilder):
                    continue
                cls[1](self.main_module).compose()

    def compose_main_module(self):

        _builtin_stdout = AsyncObservable[Any]()
        _builtin_stdout.subscribe(
            Subscriber[str](
                on_next = lambda s : sys.stdout.write(str(s) + "\n")))

        _builtin_stderr = AsyncObservable[Any]()
        _builtin_stderr.subscribe(
            Subscriber[str](
                on_next = lambda s : sys.stderr.write(str(s) + "\n")))

        _builtin_runtime = AsyncObservable[int]()
        _builtin_runtime.subscribe(self)

        self.main_module = Module("main", **{
            "stdout" : _builtin_stdout,
            "stderr" : _builtin_stderr,
            "rt" : _builtin_runtime
        })

        self.load_builtins()
