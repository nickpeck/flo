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
        c = Component(self.name)
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
        self.declare_public(name, input_stream)


class Runtime(Subscriber[str]):
    def _restart(self):
        pass
    def _exit(self):
        pass
    async def on_next(self, value):
        # TODO react to value, terminate, restart etc
        pass

def setup_default_runtime():
    active_runtime = AsyncStream[str]

    _builtin_stdout = AsyncStream[Any]()
    _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(str(s))))

    _builtin_stderr = AsyncStream[Any]()
    _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(str(s))))

    _builtin_runtime = AsyncStream[str]()
    _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })
    
    return __main_module__