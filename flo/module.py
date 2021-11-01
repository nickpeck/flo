"""Module and Component
"""

from __future__ import annotations
from typing import Union

from . observable import AsyncObservable

class Module:
    def __init__(self, name, **opts):
        self.name = name
        self.locals = {k:("local", v) for k,v in opts.items()}
        self.parent = None

    def _check_is_not_defined(self, name):
        if name in self.locals:
            raise Exception("Variable '{}' is already defined".format(name))

    def declare_local(self, name: str,
        attr: Union[AsyncObservable, Component, Module]):
        self._check_is_not_defined(name)
        self.locals[name] = ("local", attr)

    def declare_public(self, name: str,
        attr: Union[AsyncObservable, Component, Module]):
        self._check_is_not_defined(name)
        self.locals[name] = ("public", attr)

    def get_member(self, name):
        return self.locals[name][1]

    def __str__(self):
        return "<Module '{}'>".format(self.name)

    def __repr__(self):
        return str(self)

class Component(Module):

    def duplicate(self, **overrides):
        comp = Component(self.name)
        comp.locals = self.locals
        for key, value in overrides.items():
            if key in comp.locals:
                access = comp.locals[key][0]
                comp.locals[key] = (access, value)
            else:
                raise Exception("{} has no local attr '{}'".format(comp, key))
        return comp

    def __str__(self):
        return "<Component '{}'>".format(self.name)

class Filter(Module):
    def __init__(self, name, input_observable: AsyncObservable):
        super().__init__("Anonymous Filter on '{}'".format(name))
        self.declare_public(name, input_observable)

class ModuleBuilder:
    def __init__(self, parent_module: Module):
        self.parent_module = parent_module
    def compose(self):
        pass
