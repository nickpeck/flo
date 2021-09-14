import asyncio
import importlib
import inspect
import os
import traceback
from typing import Any, Union, Optional, List, Callable
import signal
import sys

from antlr4 import * # type: ignore
from antlr4.error.ErrorListener import ErrorListener # type: ignore
from . FloLexer import FloLexer
from . FloParser import FloParser
from . FloListener import FloListener
from . runtime import setup_default_runtime, Component, Filter, Module
from . stream import AsyncStream, Subscriber, ComputedMapped, AsyncManager

class EOFException(Exception):
    pass

class REPLErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        if offendingSymbol is not None:
            if offendingSymbol.text == "<EOF>":
                raise EOFException(offendingSymbol, line, column, msg, e)
            else:
                raise Exception(msg)

    # def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        # #print("reportAmbiguity", recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs)
        # #pass
        # #raise Exception("reportAmbiguity")
        # pass

    # def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        # #print("reportAttemptingFullContext", recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs)
        # #pass
        
        # #print(configs)
        # #raise Exception("reportAttemptingFullContext")
        # pass

    # def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        # #print("reportContextSensitivity", dfa)
        # #raise Exception("reportContextSensitivity")
        # pass

class FloListenerImpl(FloListener):
    """
    Walks through an ANTLR-generated parse tree, translating each node into python statements.
    Execution of statements occurs upon exiting each statement block.
    """
    @staticmethod
    def loadModule(name, main_module=None):
        input_stream = FileStream(name)
        return FloListenerImpl._parse_module(input_stream, main_module)

    @staticmethod
    def loadString(code, main_module=None):
        input_stream = InputStream(code)
        return FloListenerImpl._parse_module(input_stream, main_module)

    @staticmethod
    def _parse_module(input_stream, main_module):
        lexer = FloLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = FloParser(stream)
        tree = parser.module()
        listener = FloListenerImpl(main_module)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        # run, to schedual any remaining tasks
        AsyncManager.get_instance().run()
        return listener

    @staticmethod
    def repl():
        def signal_handler(sig, frame):
            print('Bye')
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        print('Press Ctrl+C to exit')
        if os.name != 'nt':
            signal.pause()
        buffer = []
        listener = None
        prompt = "> "
        while True:
            buffer.append(input(prompt))
            code = " ".join(buffer)
            input_stream = InputStream(code)
            lexer = FloLexer(input_stream)
            stream = CommonTokenStream(lexer)
            parser = FloParser(stream)
            parser.removeErrorListeners()
            parser.addErrorListener(REPLErrorListener())
            try:
                # attempt to parse the code in an AST
                tree = parser.module()
            except EOFException as eof:
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
            listener = FloListenerImpl(None)
            walker = ParseTreeWalker()
            try:
                walker.walk(listener, tree)
                AsyncManager.get_instance().run()
            except Exception:
                # error occurs during evaluation
                traceback.print_exc()
            finally:
                buffer = []
                prompt = "> "

    def __init__(self, main_module=None):
        super().__init__()
        self.register = []
        if main_module is None:
            self.scope = setup_default_runtime()
        else:
            self.scope = main_module
        self._is_get_attrib = False
        self._is_sync = False

    def _enter_nested_scope(self, scope: Union[Module, Component, Filter], name: Optional[str] = None):
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
            if not isinstance(right_expr, AsyncStream):
                # not a stream so just go ahead and compute the value
                self.register = self.register[:-1]
                self.register.append(func(right_expr))
                return
            # otherwise, set up a computed to represent all future states
            computed = AsyncStream.computed(
                func, # type: ignore
                [right_expr]
            )
        elif len(deps) == 2:
            # binary forms... 'x + y' 'x >= y'
            left_expr = deps[0]
            right_expr = deps[1]
            if not isinstance(left_expr, AsyncStream) and not isinstance(right_expr, AsyncStream):
                # neither are streams so just go ahead and compute the value
                self.register = self.register[:-2]
                self.register.append(func(*deps))
                return
            if not isinstance(left_expr, AsyncStream):
                left_expr = AsyncStream(left_expr)
            if not isinstance(right_expr, AsyncStream):
                right_expr = AsyncStream(right_expr)
            computed = AsyncStream.computed(
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
        self.register.append(value)

    # Enter a parse tree produced by FloParser#string.
    def enterString(self, ctx:FloParser.StringContext):
        value = ctx.children[0].getText()[1:-1]
        self.register.append(value)

    # Enter a parse tree produced by FloParser#bool.
    def enterBool(self, ctx:FloParser.BoolContext):
        value = ctx.children[0].getText()
        if value == 'true':
            self.register.append(True)
        elif value == 'false':
            self.register.append(False)

    # Enter a parse tree produced by FloParser#getAttrib.
    def enterGetAttrib(self, ctx:FloParser.GetAttribContext):
        if self._is_get_attrib:
            return
        self._is_get_attrib = True
        left = ctx.children[0].getText()
        rights = ctx.children[2].getText().split(".")
        
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
        for i in range(0, len(rights)):
            right = rights[i]
            if right.startswith('"') and right.endswith('"'):
                # its a str, because the parse adds "..."
                rights[i] = right[1:-1]
                continue
            # its an int
            rights[i] = int(rights[i])
        left = self.register.pop(-1)
        value = left[rights[0]]
        for right in rights[1:]:
            value = value[right]
        self.register.append(value)

    # Exit a parse tree produced by FloParser#getAttrib.
    def exitGetAttrib(self, ctx:FloParser.GetAttribContext):
        self._is_get_attrib = False

    # Enter a parse tree produced by FloParser#id.
    def enterId(self, ctx:FloParser.IdContext):
        if self._is_get_attrib:
            return
        id = ctx.children[0].getText()
        self.register.append(self.scope.get_member(id))

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
                    wrapper_stream = ComputedMapped(None, None, obj) # type: ignore
                    c.declare_public(name, wrapper_stream)
            self.scope.declare_local(libname, c)

    # Exit a parse tree produced by FloParser#import_statement.
    def exitImport_statement(self, ctx:FloParser.Import_statementContext):
        self._is_get_attrib = False

    # Enter a parse tree produced by FloParser#simpleDeclaration.
    def enterSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        _type = None
        if ctx.children[0].getText() == "public":
            if len(ctx.children) == 4:
                _type = ctx.children[3].getText()
            id = ctx.children[1].getText()
            stream = AsyncStream[_type]() # type: ignore
            self.scope.declare_public(id, stream)
        else:
            if len(ctx.children) == 3:
                _type = ctx.children[2].getText()
            id = ctx.children[0].getText()
            if _type in self.scope.locals and isinstance(self.scope.get_member(_type), Component):
                comp_instance = self.scope.get_member(_type)
                self.scope.declare_local(id, comp_instance)
            else:
                stream = AsyncStream[_type]() # type: ignore
                self.scope.declare_local(id, stream)

    # Exit a parse tree produced by FloParser#computedDeclaration.
    def exitComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        if ctx.children[0].getText() == "public":
            id = ctx.children[1].getText()
            self.scope.declare_public(id, self.register[0])
        else:
            id = ctx.children[0].getText()
            self.scope.declare_local(id, self.register[0])
        self.register = self.register[1:]

    # Exit a parse tree produced by FloParser#filterDeclaration.
    def exitFilterDeclaration(self, ctx:FloParser.FilterDeclarationContext):
        if ctx.children[0].getText() == "public":
            id = ctx.children[1].getText()
            self.scope.declare_public(id, self.register[0])
        else:
            id = ctx.children[0].getText()
            self.scope.declare_local(id, self.register[0])

    # Exit a parse tree produced by FloParser#joinDeclaration.
    def exitJoinDeclaration(self, ctx:FloParser.JoinDeclarationContext):
        if ctx.children[0].getText() == "public":
            id = ctx.children[1].getText()
            self.scope.declare_public(id, self.register[0])
        else:
            id = ctx.children[0].getText()
            self.scope.declare_local(id, self.register[0])

    # # Enter a parse tree produced by FloParser#compound_expression_filter.
    def enterCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        # so given {x : x<5} we declare a hidden module where x is the only local
        id = ctx.children[0].getText()
        var = self.scope.get_member(id)
        m = Filter(id, var)
        self._enter_nested_scope(m)

    # Exit a parse tree produced by FloParser#compound_expression_filter.
    def exitCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        id = ctx.children[0].getText()
        output = AsyncStream[Any]()
        input = self.scope.get_member(id)
        def f(truthy):
            nonlocal output
            nonlocal input
            if truthy:
                output.write(input.peek())
        computed_expr = self.register[-1]
        computed_expr.subscribe(
            Subscriber(
                on_next = f
            )
        )
        self.scope.declare_public("output", output)
        filter = self.scope
        self._exit_nested_scope()
        self.register[-1] = filter.get_member("output")

    # Exit a parse tree produced by FloParser#compound_expression_join.
    def exitCompound_expression_join(self, ctx:FloParser.Compound_expression_joinContext):
        left = self.register[-2]
        right = self.register[-1]
        self.register = self.register[:-2]
        joined = left.joinTo(right)
        self.register.append(joined)

    # Exit a parse tree produced by FloParser#compound_expression_comparison.
    def exitCompound_expression_comparison(self, ctx:FloParser.Compound_expression_comparisonContext):
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
    def exitCompound_expression_not(self, ctx:FloParser.Compound_expression_notContext):
        if len(ctx.children) >= 2:
            if ctx.children[0].getText() == '!':
                right = self.register[-1]
                self._make_computed([right], lambda a: not a)

    # Exit a parse tree produced by FloParser#compound_expression_mult_div.
    def exitCompound_expression_mult_div(self, ctx:FloParser.Compound_expression_mult_divContext):
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
    def exitCompound_expression_plus_minus(self, ctx:FloParser.Compound_expression_plus_minusContext):
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
    def exitCompound_expression_and(self, ctx:FloParser.Compound_expression_andContext):
        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'and':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a and b)

    # Exit a parse tree produced by FloParser#compound_expression_or.
    def exitCompound_expression_or(self, ctx:FloParser.Compound_expression_orContext):
         if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'or':
                left = self.register[-2]
                right = self.register[-1]
                self._make_computed([left, right], lambda a,b: a or b)

    # Exit a parse tree produced by FloParser#compound_expression_putvalue.
    def exitCompound_expression_putvalue(self, ctx:FloParser.Compound_expression_putvalueContext):
        if len(ctx.children) == 3:
            self.register[0].write(self.register[1])
            # if this is within a sync {...} block, the
            # asyncio event loop is run to completion on each put value
            if self._is_sync:
                AsyncManager.get_instance().run()
            self.register = []

    # Exit a parse tree produced by FloParser#compund_expression_tuple.
    def exitTuple(self, ctx:FloParser.TupleContext):
        tuple_length = len(list(filter(lambda c: c not in  ["(", ")", ","], 
            [c.getText() for c in ctx.children])))
        _tuple = tuple(self.register[-tuple_length:])
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
        self.register.append(obj)

    # Exit a parse tree produced by FloParser#compound_expression.
    def exitCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        if len(ctx.children) == 3:
            self.register[0].bindTo(self.register[1])
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
