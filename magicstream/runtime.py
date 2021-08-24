import sys
from typing import Any

from . import AsyncStream, Subscriber

class Module:
    def __init__(self, name, **opts):
        self.name = name
        self.inputs = {}
        self.outputs = {}
        self.locals = opts

    def declare_local(self, name: str, component):
        self.locals[name] = component

    def declare_input(self, name: str, component):
        self.inputs[name] = component

    def declare_output(self, name: str, component):
        self.outputs[name] = component

    def __str__(self):
        return "<Module {}>".format(self.name)

    def __repr__(self):
        return str(self)

class Component(Module):
    def __init__(self, name, **opts):
        super().__init__(name, **opts)

    def duplicate(self, **overrides):
        c = Component(self.name)
        c.inputs = self.inputs
        c.output = self.outputs
        c.locals = self.locals
        for key in overrides.keys():
            if key in c.locals:
                c.locals[key] = overrides[key]
            else:
                raise Exception("{} has no local attr '{}'".format(c, key))
        return c

    def __str__(self):
        return "<Component {}>".format(self.name)

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

    _builtin_stdout = AsyncStream[str]()
    await _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(s)))

    _builtin_stderr = AsyncStream[str]()
    await _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(s)))

    _builtin_runtime = AsyncStream[str]()
    await _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })
    
    return __main_module__