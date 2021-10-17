# pylint: disable=invalid-name
"""Flo Antlr Listener implementation
"""
import importlib
import inspect
import os
import traceback
from typing import Any, Union, Optional, List, Callable
import signal
import sys

# pylint: disable=wildcard-import, unused-wildcard-import
from antlr4 import * # type: ignore
from antlr4.error.ErrorListener import ErrorListener # type: ignore
from . FloLexer import FloLexer
from . FloParser import FloParser
from . FloListener import FloListener
from . runtime import setup_default_runtime, Component, Filter, Module
from . observable import AsyncObservable, Subscriber, ComputedMapped, AsyncManager, unwrap, ReadWriteDelegator

class EOFException(Exception):
    """Indicates that the input could not be passed owing to
    an unexpeced EOF.
    """
    pass

class REPLErrorListener(ErrorListener):
    """Custom error listener used in the REPL
    """
    # pylint: disable=too-many-arguments
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Listen for and raise all syntax error.
        EOF syntax errors have a special context in the REPL, so raise
        EOFException in this case.
        """
        if offendingSymbol is not None:
            if offendingSymbol.text == "<EOF>":
                raise EOFException(offendingSymbol, line, column, msg, e)
            raise Exception(msg)

# pylint: disable=too-many-public-methods
class FloListenerImpl(FloListener):
    """
    Walks through an ANTLR-generated parse tree, translating each node into python statements.
    Execution of statements occurs upon exiting each statement block.
    """
    @staticmethod
    def loadModule(name, main_module=None):
        """Load a module from a given file name
        """
        input_observable = FileStream(name)
        return FloListenerImpl._parse_module(input_observable, main_module)

    @staticmethod
    def loadString(code, main_module=None):
        """Load a module from direct code string input
        """
        input_observable = InputStream(code)
        return FloListenerImpl._parse_module(input_observable, main_module)

    @staticmethod
    def _parse_module(input_observable, main_module):
        lexer = FloLexer(input_observable)
        observable = CommonTokenStream(lexer)
        parser = FloParser(observable)
        tree = parser.module()
        listener = FloListenerImpl(main_module)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        # run, to schedual any remaining tasks
        AsyncManager.get_instance().run()
        return listener

    @staticmethod
    def repl():
        """Entry point for the read-evaluate-print-loop
        """
        # pylint: disable=unused-argument
        def signal_handler(sig, frame):
            print('Bye')
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        print('Press Ctrl+C to exit')
        if os.name != 'nt':
            # pylint: disable no-member
            signal.pause()
        buffer = []
        listener = FloListenerImpl(None, True)
        walker = ParseTreeWalker()
        prompt = "> "
        while True:
            buffer.append(input(prompt))
            code = " ".join(buffer)
            input_observable = InputStream(code)
            lexer = FloLexer(input_observable)
            observable = CommonTokenStream(lexer)
            parser = FloParser(observable)
            parser.removeErrorListeners()
            parser.addErrorListener(REPLErrorListener())
            try:
                # attempt to parse the code in an AST
                tree = parser.repl_stmt()
            except EOFException:
                # in the REPL, a premature EOF error indicates
                # there we are still awaiting on further input,
                # so continue to build the code from user input
                prompt = "... "
                continue
            except Exception as e:
                # Other exceptions, syntax error. Display and reset
                # buffer:
                print("SyntaxError", e)
                buffer = []
                prompt = "> "
                continue
            # we got this far, so the code is valid and complete.
            # Evaluate
            try:
                walker.walk(listener, tree)
                AsyncManager.get_instance().run()
            except Exception:
                # error occurs during evaluation
                traceback.print_exc()
            finally:
                buffer = []
                prompt = "> "

    def __init__(self, main_module=None, is_repl=False):
        super().__init__()
        self.register = []
        if main_module is None:
            self.scope = setup_default_runtime()
        else:
            self.scope = main_module
        self._is_get_attrib = False
        self._is_sync = False
        self.is_repl = is_repl
        self._is_lambda = False

    def _enter_nested_scope(self,
        scope: Union[Module, Component, Filter],
        name: Optional[str] = None):

        scope.parent = self.scope
        if name is not None:
            self.scope.declare_local(name, scope)
        self.scope = scope

    def _exit_nested_scope(self):
        self.scope = self.scope.parent

    def _make_computed(self, deps: List, func: Callable):
        if len(deps) == 1:
            # ie some right assoc operators such as 'not x')
            right_expr = deps[0]
            if not isinstance(right_expr, AsyncObservable):
                # not a observable so just go ahead and compute the value
                self.register = self.register[:-1]
                self.register.append(func(right_expr))
                return
            # otherwise, set up a computed to represent all future states
            computed = AsyncObservable.computed(
                func, # type: ignore
                [right_expr]
            )
        elif len(deps) == 2:
            # binary forms... 'x + y' 'x >= y'
            left_expr = deps[0]
            right_expr = deps[1]
            if not isinstance(left_expr, AsyncObservable) \
                and not isinstance(right_expr, AsyncObservable):
                # neither are observables so just go ahead and compute the value
                self.register = self.register[:-2]
                self.register.append(func(*deps))
                return
            if not isinstance(left_expr, AsyncObservable):
                left_expr = AsyncObservable(left_expr)
            if not isinstance(right_expr, AsyncObservable):
                right_expr = AsyncObservable(right_expr)
            computed = AsyncObservable.computed(
                func, # type: ignore
                [left_expr, right_expr]
            )
        self.register = self.register[:-len(deps)]
        self.register.append(computed)

    # Enter a parse tree produced by FloParser#number.
    def enterNumber(self, ctx:FloParser.NumberContext):
        # allow integer or float types
        try:
            value = int(ctx.children[0].getText())
        except ValueError:
            value = float(ctx.children[0].getText()) # type: ignore
        self.register.append(AsyncObservable(value))

    # Enter a parse tree produced by FloParser#string.
    def enterString(self, ctx:FloParser.StringContext):
        value = ctx.children[0].getText()[1:-1]
        self.register.append(AsyncObservable(value))

    # Enter a parse tree produced by FloParser#bool.
    def enterBool(self, ctx:FloParser.BoolContext):
        value = ctx.children[0].getText()
        if value == 'true':
            self.register.append(AsyncObservable(True))
        elif value == 'false':
            self.register.append(AsyncObservable(False))

    # Enter a parse tree produced by FloParser#getAttrib.
    def enterGetAttrib(self, ctx:FloParser.GetAttribContext):
        if self._is_get_attrib:
            return
        self._is_get_attrib = True
        left = ctx.children[0].getText()
        rights = list(filter(
            lambda c: c != ".", 
            [c.getText() for c in ctx.children[2:]]))
        right = rights[0]
        returnval = self.scope.get_member(left).get_member(right)
        for r in rights[1:]:
            returnval = returnval.get_member(r)
        self.register.append(returnval)

    # Exit a parse tree produced by FloParser#index.
    def exitIndex(self, ctx:FloParser.IndexContext):
        # nb this is 1: sliced, as the leftmost is the coded rep of 'left'
        rights = list(filter(
            lambda x: x not in ['[', ']'],
            [c.getText() for c in ctx.children]))[1:]
        # modify each of the index values, parsing to a string or int, accordingly:
        for i, right in enumerate(rights):
            if right.startswith('"') and right.endswith('"'):
                # its a str, because the parse adds "..."
                rights[i] = right[1:-1]
                continue
            # its an int
            rights[i] = int(rights[i])
        left = self.register.pop(-1)

        def _index(l):
            nonlocal rights
            value = unwrap(left)[rights[0]]
            for right in rights[1:]:
                value = unwrap(value)[right]
            return value
        computed = AsyncObservable.computed(
            _index,
            [left]
        )
        self.register.append(computed)

    # Exit a parse tree produced by FloParser#getAttrib.
    def exitGetAttrib(self, ctx:FloParser.GetAttribContext):
        self._is_get_attrib = False

    # Enter a parse tree produced by FloParser#id.
    def enterId(self, ctx:FloParser.IdContext):
        if self._is_get_attrib:
            return
        _id = ctx.children[0].getText()
        self.register.append(self.scope.get_member(_id))

    # Enter a parse tree produced by FloParser#import_statement.
    def enterImport_statement(self, ctx:FloParser.Import_statementContext):
        self._is_get_attrib = True
        # POC simple import only for now!
        if len(ctx.children) == 2:
            libname = ctx.children[1].getText()
            imported = importlib.import_module(libname)
            # https://docs.python.org/3/library/inspect.html
            c = Component(libname)
            for name, obj in inspect.getmembers(imported):
                if inspect.ismethod(obj) or inspect.isfunction(obj) or inspect.isbuiltin(obj):
                    wrapper_observable = ComputedMapped(None, None, obj) # type: ignore
                    c.declare_public(name, wrapper_observable)
            self.scope.declare_local(libname, c)

    # Exit a parse tree produced by FloParser#import_statement.
    def exitImport_statement(self, ctx:FloParser.Import_statementContext):
        self._is_get_attrib = False

    # Enter a parse tree produced by FloParser#simpleDeclaration.
    def enterSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        children = [c.getText() for c in ctx.children]
        is_public = False
        if ctx.children[0].getText() == "public":
            is_public = True
            # dec public name : type
            name = ctx.children[1].getText()
        else:
            # dec name : type
            name = ctx.children[0].getText()

        if name == "?":
            raise Exception("? is not a valid id")

        # resolve the type, if specified.
        if ":" in children:
            right_expr = None
            _scope = self.scope
            i = children.index(":")
            type_parts = children[i+1:]
            try:
                type_parts.remove(".")
            except ValueError: 
                pass
            for t in type_parts:
                # type is a dot-lookup ie dec f : file.reader
                if t in _scope.locals:
                    if isinstance(_scope.get_member(t), Component):
                        right_expr = _scope.get_member(t)
                        # its a component, so create a new instance
                        _scope = right_expr.duplicate()
                    elif isinstance(_scope.get_member(t), Module):
                        right_expr = _scope.get_member(t)
                        _scope = right_expr
                else:
                    right_expr = AsyncObservable[t]() # type: ignore
        else:
            # If no type, its just an untyped observable
            right_expr = AsyncObservable()

        if is_public:
            self.scope.declare_public(name, right_expr)
        else:
            self.scope.declare_local(name, right_expr)

    # Exit a parse tree produced by FloParser#computedDeclaration.
    def exitComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        if ctx.children[0].getText() == "public":
            _id = ctx.children[1].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_public(_id, self.register[0])
        else:
            _id = ctx.children[0].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_local(_id, self.register[0])
        self.register = self.register[1:]

    # Exit a parse tree produced by FloParser#filterDeclaration.
    def exitFilterDeclaration(self, ctx:FloParser.FilterDeclarationContext):
        if ctx.children[0].getText() == "public":
            _id = ctx.children[1].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_public(_id, self.register[0])
        else:
            _id = ctx.children[0].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_local(_id, self.register[0])

    # Exit a parse tree produced by FloParser#joinDeclaration.
    def exitJoinDeclaration(self, ctx:FloParser.JoinDeclarationContext):
        if ctx.children[0].getText() == "public":
            _id = ctx.children[1].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_public(_id, self.register[0])
        else:
            _id = ctx.children[0].getText()
            if _id == "?":
                raise Exception("? is not a valid id")
            self.scope.declare_local(_id, self.register[0])

    # Exit a parse tree produced by FloParser#computedLambdaDeclaration.
    def enterComputedLambdaDeclaration(self, ctx:FloParser.ComputedLambdaDeclarationContext):
        # this is a placeholder for the stream input, that is
        # only present for the duration of the lambda declaration
        placeholder = AsyncObservable[Any]()
        self.scope.declare_local("?", placeholder)
        
        self._is_lambda = True

    # Exit a parse tree produced by FloParser#computedLambdaDeclaration.
    def exitComputedLambdaDeclaration(self, ctx:FloParser.ComputedLambdaDeclarationContext):
        placeholder = self.scope.locals["?"][1]
        del self.scope.locals["?"]
        self._is_lambda = False

        _lambda = ReadWriteDelegator(placeholder, self.register[0])

        if ctx.children[0].getText() == "public":
            _id = ctx.children[1].getText()
            self.scope.declare_public(_id, _lambda)
        else:
            _id = ctx.children[0].getText()
            self.scope.declare_local(_id, _lambda)
        self.register = []

    # # Enter a parse tree produced by FloParser#compound_expression_filter.
    def enterCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        # so given {x : x<5} we declare a hidden module where x is the only local
        _id = ctx.children[0].getText()
        var = self.scope.get_member(_id)
        m = Filter(_id, var)
        self._enter_nested_scope(m)

    # Exit a parse tree produced by FloParser#compound_expression_filter.
    def exitCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        _id = ctx.children[0].getText()
        output = AsyncObservable[Any]()
        _input = self.scope.get_member(_id)
        def f(truthy):
            nonlocal output
            nonlocal _input
            if truthy:
                output.write(_input.peek())
        computed_expr = self.register[-1]
        computed_expr.subscribe(
            Subscriber(
                on_next = f
            )
        )
        self.scope.declare_public("output", output)
        _filter = self.scope
        self._exit_nested_scope()
        self.register[-1] = _filter.get_member("output")

    # Exit a parse tree produced by FloParser#compound_expression_join.
    def exitCompound_expression_join(self, ctx:FloParser.Compound_expression_joinContext):
        left = self.register[-2]
        right = self.register[-1]
        self.register = self.register[:-2]
        joined = left.join_to(right)
        self.register.append(joined)

    # Exit a parse tree produced by FloParser#compound_expression_comparison.
    def exitCompound_expression_comparison(self,
        ctx:FloParser.Compound_expression_comparisonContext):

        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == '>':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a > b)

            elif ctx.children[1].getText() == '<':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a < b)

            elif ctx.children[1].getText() == '>=':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a >= b)

            elif ctx.children[1].getText() == '<=':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a <= b)

            elif ctx.children[1].getText() == '==':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a == b)

    # Exit a parse tree produced by FloParser#compound_expression_not.
    def exitCompound_expression_not(self,
        ctx:FloParser.Compound_expression_notContext):

        if len(ctx.children) >= 2:
            if ctx.children[0].getText() == '!':
                right = self.register[-1]
                self._make_computed([right], lambda a: not a)

    # Exit a parse tree produced by FloParser#compound_expression_mult_div.
    def exitCompound_expression_mult_div(self,
    ctx:FloParser.Compound_expression_mult_divContext):

        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == '*':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a * b)

            elif ctx.children[1].getText() == '/':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a / b)

    # Exit a parse tree produced by FloParser#compound_expression_plus_minus.
    def exitCompound_expression_plus_minus(self,
        ctx:FloParser.Compound_expression_plus_minusContext):

        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == '+':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a + b)

            elif ctx.children[1].getText() == '-':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a - b)

    # Exit a parse tree produced by FloParser#compound_expression_and.
    def exitCompound_expression_and(self,
        ctx:FloParser.Compound_expression_andContext):

        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'and':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a and b)

    # Exit a parse tree produced by FloParser#compound_expression_or.
    def exitCompound_expression_or(self,
        ctx:FloParser.Compound_expression_orContext):

        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'or':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a or b)

    # Exit a parse tree produced by FloParser#compound_expression_putvalue.
    def exitCompound_expression_putvalue(self,
        ctx:FloParser.Compound_expression_putvalueContext):
        if len(ctx.children) == 3:
            if self._is_lambda:
                left = self.register[0]
                right = self.register[1]
                placeholder = self.scope.locals["?"][1]
                def _on_write():
                    nonlocal left
                    nonlocal right
                    left.peek().write(unwrap(right))

                computed = AsyncObservable.computed(
                    lambda x: _on_write(),
                    [placeholder]
                )
                self.register = [computed]
            else:
                self.register[0].write(self.register[1])
                # if this is within a sync {...} block, the
                # asyncio event loop is run to completion on each put value
                if self._is_sync:
                    AsyncManager.get_instance().run()
                self.register = [self.register[0]]

    # Exit a parse tree produced by FloParser#compund_expression_tuple.
    def exitTuple(self, ctx:FloParser.TupleContext):
        tuple_length = len(list(filter(lambda c: c not in  ["(", ")", ","],
            [c.getText() for c in ctx.children])))
        _tuple = AsyncObservable[tuple](tuple(self.register[-tuple_length:]))
        self.register = self.register[:-tuple_length] + [_tuple]

    # Exit a parse tree produced by FloParser#json.
    def exitDictexpr(self, ctx:FloParser.DictexprContext):
        _children = list(filter(lambda c: c not in  ["{", "}", ",", ":"],
            [c.getText() for c in ctx.children]))[::2]
        _children.reverse()
        obj = {}
        while len(_children) > 0:
            i = -len(_children)
            key = _children.pop()[1:-1]
            value = self.register.pop(i)
            obj[key] = value
        self.register.append(AsyncObservable(obj))

    # Exit a parse tree produced by FloParser#compound_expression.
    def exitCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        if len(ctx.children) == 3:
            self.register[0].bind_to(self.register[1])
            self.register = []

    # Enter a parse tree produced by FloParser#statement.
    def enterStatement(self, ctx:FloParser.StatementContext):
        self.register = []

    # Enter a parse tree produced by FloParser#component.
    def enterComponent(self, ctx:FloParser.ComponentContext):
        comp_name = ctx.children[1].getText()
        c = Component(comp_name)
        self._enter_nested_scope(c, comp_name)

    # Exit a parse tree produced by FloParser#component.
    def exitComponent(self, ctx:FloParser.ComponentContext):
        self._exit_nested_scope()

    # Enter a parse tree produced by FloParser#sync_block.
    def enterSync_block(self, ctx:FloParser.Sync_blockContext):
        self._is_sync = True

    # Exit a parse tree produced by FloParser#sync_block.
    def exitSync_block(self, ctx:FloParser.Sync_blockContext):
        self._is_sync = False

    # Exit a parse tree produced by FloParser#mod_body.
    def exitRepl_stmt(self, ctx:FloParser.Repl_stmtContext):
        if self.is_repl and len(self.register) > 0:
            print(self.register[-1])

    # Enter a parse tree produced by FloParser#module.
    def enterModule(self, ctx:FloParser.ModuleContext):
        mod_name = ctx.children[1].getText()
        if mod_name == "main":
            return
        m = Module(mod_name)
        self._enter_nested_scope(m, mod_name)

    # Exit a parse tree produced by FloParser#module.
    def exitModule(self, ctx:FloParser.ModuleContext):
        self._exit_nested_scope()
