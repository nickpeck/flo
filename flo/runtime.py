from __future__ import annotations

import sys
from typing import Any, Union

from . import AsyncStream, Subscriber

class Module:
    def __init__(self, name, **opts):
        self.name = name
        # self.inputs = {}
        # self.outputs = {}
        self.locals = {k:("local", opts[k]) for k in opts.keys()}
        self.parent = None

    def declare_local(self, name: str, 
        attr: Union[AsyncStream, Component, Module]):
        self.locals[name] = ("local", attr)

    def declare_input(self, name: str, pipe: AsyncStream):
        self.locals[name] = ("input", pipe)

    def declare_output(self, name: str, pipe: AsyncStream):
        self.locals[name] =("output", pipe)

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
        c = Component(self.name)
        # c.inputs = self.inputs
        # c.output = self.outputs
        c.locals = self.locals
        for key in overrides.keys():
            if key in c.locals:
                access = c.locals[key][0]
                c.locals[key] = (access, overrides[key])
            else:
                raise Exception("{} has no local attr '{}'".format(c, key))
        return c

    def __str__(self):
        return "<Component '{}'>".format(self.name)

class Filter(Module):
    def __init__(self, name, input_stream: AsyncStream):
        super().__init__("Anonymous Filter on '{}'".format(name))
        self.declare_input(name, input_stream)


class Runtime(Subscriber[str]):
    def _restart(self):
        pass
    def _exit(self):
        pass
    async def on_next(self, value):
        # TODO react to value, terminate, restart etc
        pass

async def setup_default_runtime():
    active_runtime = AsyncStream[str]

    _builtin_stdout = AsyncStream[Any]()
    await _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(str(s))))

    _builtin_stderr = AsyncStream[Any]()
    await _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(str(s))))

    _builtin_runtime = AsyncStream[str]()
    await _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })
    
    return __main_module__