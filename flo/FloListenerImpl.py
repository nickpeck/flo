import asyncio
import sys

from antlr4 import * # type: ignore
from . FloLexer import FloLexer
from . FloParser import FloParser
from . FloListener import FloListener
from . runtime import setup_default_runtime, Component
from . stream import AsyncStream

class FloListenerImpl(FloListener):
    """
    Walks through an ANTLR-generated parse tree, translating each node into python statements.
    Execution of statements occurs upon exiting each statement block.
    """
    @staticmethod
    def loadModule(name, main_module=None):
        input_stream = FileStream(name)
        lexer = FloLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = FloParser(stream)
        tree = parser.module()
        listener = FloListenerImpl(main_module)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        return listener

    @staticmethod
    def loadString(code, main_module=None):
        input_stream = InputStream(code)
        lexer = FloLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = FloParser(stream)
        tree = parser.module()
        listener = FloListenerImpl(main_module)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        return listener

    def __init__(self, main_module=None):
        super().__init__()
        self.register = []
        if main_module is None:
            self.module = asyncio.run(setup_default_runtime())
        else:
            self.module = main_module
        self.isGetAttrib = False

    # Enter a parse tree produced by FloParser#number.
    def enterNumber(self, ctx:FloParser.NumberContext):
        value = int(ctx.children[0].getText())
        self.register.append(value)

    # Exit a parse tree produced by FloParser#number.
    def exitNumber(self, ctx:FloParser.NumberContext):
        pass


    # Enter a parse tree produced by FloParser#string.
    def enterString(self, ctx:FloParser.StringContext):
        value = ctx.children[0].getText()[1:-1]
        self.register.append(value)

    # Exit a parse tree produced by FloParser#string.
    def exitString(self, ctx:FloParser.StringContext):
        pass


    # Enter a parse tree produced by FloParser#bool.
    def enterBool(self, ctx:FloParser.BoolContext):
        value = ctx.children[0].getText()
        if value == 'true':
            self.register.append(True)
        elif value == 'false':
            self.register.append(False)

    # Exit a parse tree produced by FloParser#bool.
    def exitBool(self, ctx:FloParser.BoolContext):
        pass


    # Enter a parse tree produced by FloParser#getAttrib.
    def enterGetAttrib(self, ctx:FloParser.GetAttribContext):
        self.isGetAttrib = True
        left = ctx.children[0].getText()
        right = ctx.children[2].getText()
        # TODO better way to do this, using magic methods?
        try:
            self.register.append(self.module.locals[left].outputs[right])
        except KeyError:
            try:
                self.register.append(self.module.locals[left].inputs[right])
            except KeyError:
                self.register.append(self.module.locals[left].locals[right])

    # Exit a parse tree produced by FloParser#getAttrib.
    def exitGetAttrib(self, ctx:FloParser.GetAttribContext):
        self.isGetAttrib = False
        pass


    # Enter a parse tree produced by FloParser#id.
    def enterId(self, ctx:FloParser.IdContext):
        if self.isGetAttrib:
            return
        # print(dir(ctx))
        id = ctx.children[0].getText()
        # print(ctx.start)
        # print(self.module.locals)
        # TODO better way to do this, using magic methods?
        try:
            self.register.append(self.module.locals[id])
        except KeyError:
            try:
                self.register.append(self.module.inputs[id])
            except KeyError:
                self.register.append(self.module.outputs[id])
        
    # Exit a parse tree produced by FloParser#id.
    def exitId(self, ctx:FloParser.IdContext):
        pass


    # # Enter a parse tree produced by FloParser#declaration.
    # def enterDeclaration(self, ctx:FloParser.DeclarationContext):
        # if ctx.children[1].getText() == "output":
            # _type = ctx.children[4].getText()
            # id = ctx.children[2].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_output(id, stream)
            # self.register.append(stream)
        # elif ctx.children[1].getText() == "input":
            # _type = ctx.children[4].getText()
            # id = ctx.children[2].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_input(id, stream)
            # self.register.append(stream)
        # else:
            # _type = ctx.children[3].getText()
            # id = ctx.children[1].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_local(id, stream)
            # self.register.append(stream)

    # # Exit a parse tree produced by FloParser#declaration.
    # def exitDeclaration(self, ctx:FloParser.DeclarationContext):
        # pass

    # Enter a parse tree produced by FloParser#simpleDeclaration.
    def enterSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        # print("enterSimpleDeclaration", ["".join(c.getText()) for c in ctx.children])
        if ctx.children[1].getText() == "output":
            _type = ctx.children[4].getText()
            id = ctx.children[2].getText()
            stream = AsyncStream[_type]() # type: ignore
            self.module.declare_output(id, stream)
        elif ctx.children[1].getText() == "input":
            _type = ctx.children[4].getText()
            id = ctx.children[2].getText()
            stream = AsyncStream[_type]() # type: ignore
            self.module.declare_input(id, stream)
        else:
            _type = ctx.children[3].getText()
            id = ctx.children[1].getText()
            if _type in self.module.locals and isinstance(self.module.locals[_type], Component):
                comp_instance = self.module.locals[_type]
                self.module.declare_local(id, comp_instance)
            else:
                stream = AsyncStream[_type]() # type: ignore
                self.module.declare_local(id, stream)

    # Exit a parse tree produced by FloParser#simpleDeclaration.
    def exitSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#computedDeclaration.
    def enterComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        # print("enterComputedDeclaration")
        if ctx.children[1].getText() == "output":
            _type = ctx.children[4].getText()
            id = ctx.children[2].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_output(id, stream)
            # self.register.append(stream)
        elif ctx.children[1].getText() == "input":
            _type = ctx.children[4].getText()
            id = ctx.children[2].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_input(id, stream)
            # self.register.append(stream)
        else:
            _type = ctx.children[3].getText()
            id = ctx.children[1].getText()
            # stream = AsyncStream[_type]()
            # self.module.declare_local(id, stream)
            # self.register.append(stream)
        # print("GOT HERE 2")

    # Exit a parse tree produced by FloParser#computedDeclaration.
    def exitComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        if ctx.children[1].getText() == "output":
            id = ctx.children[2].getText()
        elif ctx.children[1].getText() == "input":
            id = ctx.children[2].getText()
        else:
            id = ctx.children[1].getText()
        self.module.declare_local(id, self.register[0])

    # Enter a parse tree produced by FloParser#compound_expression_paren.
    def enterCompound_expression_paren(self, ctx:FloParser.Compound_expression_parenContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_paren.
    def exitCompound_expression_paren(self, ctx:FloParser.Compound_expression_parenContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_not.
    def enterCompound_expression_not(self, ctx:FloParser.Compound_expression_notContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_not.
    def exitCompound_expression_not(self, ctx:FloParser.Compound_expression_notContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_mult_div.
    def enterCompound_expression_mult_div(self, ctx:FloParser.Compound_expression_mult_divContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_mult_div.
    def exitCompound_expression_mult_div(self, ctx:FloParser.Compound_expression_mult_divContext):
        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == '*':
                #print("------",  ctx.children[0].getText(), ctx.children[2].getText(), self.register[-2:])
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left * right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                #print(left, right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a*b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)
            elif ctx.children[1].getText() == '/':
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left / right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a/b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)


    # Enter a parse tree produced by FloParser#compound_expression_plus_minus.
    def enterCompound_expression_plus_minus(self, ctx:FloParser.Compound_expression_plus_minusContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_plus_minus.
    def exitCompound_expression_plus_minus(self, ctx:FloParser.Compound_expression_plus_minusContext):
        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == '+':
                #print("------",  ctx.children[0].getText(), ctx.children[2].getText(), self.register[-2:])
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left + right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                #print(left, right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a+b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)
            elif ctx.children[1].getText() == '-':
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left - right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a-b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)


    # Enter a parse tree produced by FloParser#compound_expression_and.
    def enterCompound_expression_and(self, ctx:FloParser.Compound_expression_andContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_and.
    def exitCompound_expression_and(self, ctx:FloParser.Compound_expression_andContext):
        if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'and':
                #print("------",  ctx.children[0].getText(), ctx.children[2].getText(), self.register[-2:])
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left and right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                #print(left, right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a and b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)


    # Enter a parse tree produced by FloParser#compound_expression_or.
    def enterCompound_expression_or(self, ctx:FloParser.Compound_expression_orContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_or.
    def exitCompound_expression_or(self, ctx:FloParser.Compound_expression_orContext):
         if len(ctx.children) >= 3:
            if ctx.children[1].getText() == 'or':
                #print("------",  ctx.children[0].getText(), ctx.children[2].getText(), self.register[-2:])
                left = self.register[-2]
                right = self.register[-1]
                if not isinstance(left, AsyncStream) and not isinstance(right, AsyncStream):
                    self.register = self.register[:-2]
                    self.register.append(left or right)
                    return
                if not isinstance(left, AsyncStream):
                    left = AsyncStream(left)
                if not isinstance(right, AsyncStream):
                    right = AsyncStream(right)
                #print(left, right)
                computed = asyncio.run(AsyncStream.computed(
                    lambda a,b: a or b, # type: ignore
                    [left, right]
                ))
                self.register = self.register[:-2]
                self.register.append(computed)

    # Enter a parse tree produced by FloParser#compound_expression_putvalue.
    def enterCompound_expression_putvalue(self, ctx:FloParser.Compound_expression_putvalueContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_putvalue.
    def exitCompound_expression_putvalue(self, ctx:FloParser.Compound_expression_putvalueContext):
        if len(ctx.children) == 3:
            asyncio.run(self.register[0].write(self.register[1]))
            self.register = []
        pass

    # Enter a parse tree produced by FloParser#compound_expression.
    def enterCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression.
    def exitCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        if len(ctx.children) == 3:
            asyncio.run(self.register[0].bindTo(self.register[1]))
            self.register = []
        pass


    # Enter a parse tree produced by FloParser#statement.
    def enterStatement(self, ctx:FloParser.StatementContext):
        self.register = []

    # Exit a parse tree produced by FloParser#statement.
    def exitStatement(self, ctx:FloParser.StatementContext):
        #print(self.register)
        #print(self.module.locals, self.module.inputs, self.module.outputs)
        pass


    # Enter a parse tree produced by FloParser#component.
    def enterComponent(self, ctx:FloParser.ComponentContext):
        # print("enterComponent", ctx.children[1].getText())
        # print("-----------------", self.module)
        comp_name = ctx.children[1].getText()
        c = Component(comp_name)
        c.parent = self.module
        # print(">>>>>>>>>", c.__dict__)
        self.module.declare_local(comp_name, c)
        self.module = c

    # Exit a parse tree produced by FloParser#component.
    def exitComponent(self, ctx:FloParser.ComponentContext):
        # print("exitComponent", ctx.children[1].getText())
        self.module = self.module.parent
        # print(self.module)


    # Enter a parse tree produced by FloParser#module.
    def enterModule(self, ctx:FloParser.ModuleContext):
        mod_name = ctx.children[1].getText()
        if mod_name == "main":
            return
        
        # TODO else....

    # Exit a parse tree produced by FloParser#module.
    def exitModule(self, ctx:FloParser.ModuleContext):
        #print(self.module.locals, self.module.inputs, self.module.outputs)
        if self.module.parent is not None:
            self.module = self.module.parent
