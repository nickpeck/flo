"""Entities used as part of the runtime
"""
from __future__ import annotations

import asyncio
import socket
import sys
from typing import Any, Union, Tuple

from . observable import AsyncObservable, Subscriber, AsyncManager, unwrap
from . module import Module
from . builtins.socket import compose_socket_module
from . builtins.file import compose_file_module


class Runtime(Subscriber[int]):
    SIG_TERMINATE = 0
    def _restart(self):
        pass
    def _exit(self):
        sys.exit(0)
    async def on_next(self, value: int):
        if value == self.__class__.SIG_TERMINATE:
            self._exit()
        # TODO react to value, terminate, restart etc
        pass


def setup_default_runtime():
    active_runtime = Runtime()

    _builtin_stdout = AsyncObservable[Any]()
    _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(str(s) + "\n")))

    _builtin_stderr = AsyncObservable[Any]()
    _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(str(s) + "\n")))

    #_builtin_stdin = AsyncObservable[Any]()
    # for line in sys.stdin:
        # _builtin_stdin.write(line)

    _builtin_runtime = AsyncObservable[int]()
    _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        # "stdin": _builtin_stdin,
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })

    compose_file_module(__main_module__)
    compose_socket_module(__main_module__)

    return __main_module__
