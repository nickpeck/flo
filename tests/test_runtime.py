import asyncio
import unittest
from flo.module import Module, Component
from flo.runtime import Runtime

class RuntimeTests(unittest.TestCase):
    def test_runtime_creation(self):
        r = Runtime()

    def test_setup_main_module(self):
        async def _test():
            r = Runtime()
            return r.main_module

        result = asyncio.run(_test())
        assert str(result) == "<Module 'main'>"

class ModuleTests(unittest.TestCase):
    def test_module_creation(self):
        mod = Module("mymod", x=3, y=4)
        assert mod.locals == {
            'x': ('local', 3),
            'y': ('local', 4),
        }

    def test_declare_local(self):
        mod = Module("mymod", x=3, y=4)
        mod.declare_local('z', "hello")
        assert mod.locals == {
            'x': ('local', 3),
            'y': ('local', 4),
            "z": ('local', "hello")
        }

    def test_declare_public(self):
        mod = Module("mymod", x=3, y=4)
        mod.declare_public('a', "myinput")
        assert mod.locals == {
            'x': ('local', 3),
            'y': ('local', 4), 
            'a': ('public', 'myinput')}

class ComponentTests(unittest.TestCase):
    def test_duplicate(self):
        comp = Component("mycomp", x=3, y=4)
        assert comp.locals == {
            "x" : ("local", 3),
            "y" : ("local", 4)
        }
        comp2 = comp.duplicate(y=5)
        assert comp2.locals == {
            "x" : ("local", 3),
            "y" : ("local", 5)
        }

    def test_duplicate_only_allows_override_existing_locals(self):
        comp = Component("mycomp", x=3, y=4)
        with self.assertRaises(Exception) as e:
            comp2 = comp.duplicate(z=5)
        assert e.exception.args == ("<Component 'mycomp'> has no local attr 'z'",)

if __name__ == "__main__":
    unittest.main()