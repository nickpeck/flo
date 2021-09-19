"""Entities used as part of the runtime
"""
from __future__ import annotations

import sys
from typing import Any, Union

from . import AsyncStream, Subscriber

class Module:
    def __init__(self, name, **opts):
        self.name = name
        self.locals = {k:("local", opts[k]) for k in opts.keys()}
        self.parent = None

    def _check_is_not_defined(self, name):
        if name in self.locals:
            raise Exception("Variable '{}' is already defined".format(name))

    def declare_local(self, name: str,
        attr: Union[AsyncStream, Component, Module]):
        self._check_is_not_defined(name)
        self.locals[name] = ("local", attr)

    def declare_public(self, name: str, pipe: AsyncStream):
        self._check_is_not_defined(name)
        self.locals[name] = ("public", pipe)

    def get_member(self, name):
        return self.locals[name][1]

    def __str__(self):
        return "<Module '{}'>".format(self.name)

    def __repr__(self):
        return str(self)

class Component(Module):
    def __init__(self, name, **opts):
        super().__init__(name, **opts)

    def duplicate(self, **overrides):
        comp = Component(self.name)
        comp.locals = self.locals
        for key in overrides.keys():
            if key in comp.locals:
                access = comp.locals[key][0]
                comp.locals[key] = (access, overrides[key])
            else:
                raise Exception("{} has no local attr '{}'".format(comp, key))
        return comp

    def __str__(self):
        return "<Component '{}'>".format(self.name)

class Filter(Module):
    def __init__(self, name, input_stream: AsyncStream):
        super().__init__("Anonymous Filter on '{}'".format(name))
        self.declare_public(name, input_stream)


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

def add_file_reader(parent_module):
    reader = Component("reader")
    path = AsyncStream[str]()
    reader.declare_public("path", path)
    reader_stream = AsyncStream[str]()
    reader.declare_public("readlines", reader_stream)
    def _reader(path):
        with open(path, "r") as f:
            for line in f:
                reader_stream.write(line)
    path.subscribe(
        Subscriber(
            on_next = lambda p: _reader(p)
        )
    )
    parent_module.declare_public("reader", reader)

def add_file_writer(parent_module):
    writer = Component("writer")
    parent_module.declare_public("writer", writer)

def compose_file_module(parent_module):
    file = Module("file")
    add_file_reader(file)
    add_file_writer(file)
    parent_module.declare_public("file", file)

def setup_default_runtime():
    active_runtime = Runtime()

    _builtin_stdout = AsyncStream[Any]()
    _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(str(s) + "\n")))

    _builtin_stderr = AsyncStream[Any]()
    _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(str(s) + "\n")))

    _builtin_runtime = AsyncStream[int]()
    _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })

    compose_file_module(__main_module__)

    return __main_module__
