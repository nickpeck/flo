import sys

from antlr4 import *
from . FloLexer import FloLexer
from . FloParser import FloParser
from . FloListener import FloListener

class FloListenerImpl(FloListener):
    """
    Walks through an ANTLR-generated parse tree, translating each node into python statements.
    Execution of statements occurs upon exiting each statement block.
    """
    @staticmethod
    def loadModule(name):
        input_stream = FileStream(name)
        lexer = FloLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = FloParser(stream)
        tree = parser.module()
        listener = FloListenerImpl()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        return listener

    def __init__(self):
        super().__init__()

    # Enter a parse tree produced by FloParser#number.
    def enterNumber(self, ctx:FloParser.NumberContext):
        pass

    # Exit a parse tree produced by FloParser#number.
    def exitNumber(self, ctx:FloParser.NumberContext):
        pass


    # Enter a parse tree produced by FloParser#string.
    def enterString(self, ctx:FloParser.StringContext):
        pass

    # Exit a parse tree produced by FloParser#string.
    def exitString(self, ctx:FloParser.StringContext):
        pass


    # Enter a parse tree produced by FloParser#bool.
    def enterBool(self, ctx:FloParser.BoolContext):
        pass

    # Exit a parse tree produced by FloParser#bool.
    def exitBool(self, ctx:FloParser.BoolContext):
        pass


    # Enter a parse tree produced by FloParser#getAttrib.
    def enterGetAttrib(self, ctx:FloParser.GetAttribContext):
        pass

    # Exit a parse tree produced by FloParser#getAttrib.
    def exitGetAttrib(self, ctx:FloParser.GetAttribContext):
        pass


    # Enter a parse tree produced by FloParser#id.
    def enterId(self, ctx:FloParser.IdContext):
        pass

    # Exit a parse tree produced by FloParser#id.
    def exitId(self, ctx:FloParser.IdContext):
        pass


    # Enter a parse tree produced by FloParser#declaration.
    def enterDeclaration(self, ctx:FloParser.DeclarationContext):
        if ctx.children[1].getText() == "output":
            _type = ctx.children[4].getText()
            print("dec output", ctx.children[2].getText(), _type)
        elif ctx.children[1].getText() == "input":
            _type = ctx.children[4].getText()
            print("dec input", ctx.children[2].getText(), _type)
        else:
            _type = ctx.children[3].getText()
            print("dec", ctx.children[1].getText(), _type)
        pass

    # Exit a parse tree produced by FloParser#declaration.
    def exitDeclaration(self, ctx:FloParser.DeclarationContext):
        pass


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
        pass


    # Enter a parse tree produced by FloParser#compound_expression_plus_minus.
    def enterCompound_expression_plus_minus(self, ctx:FloParser.Compound_expression_plus_minusContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_plus_minus.
    def exitCompound_expression_plus_minus(self, ctx:FloParser.Compound_expression_plus_minusContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_and.
    def enterCompound_expression_and(self, ctx:FloParser.Compound_expression_andContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_and.
    def exitCompound_expression_and(self, ctx:FloParser.Compound_expression_andContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_or.
    def enterCompound_expression_or(self, ctx:FloParser.Compound_expression_orContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_or.
    def exitCompound_expression_or(self, ctx:FloParser.Compound_expression_orContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression.
    def enterCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression.
    def exitCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        pass


    # Enter a parse tree produced by FloParser#statement.
    def enterStatement(self, ctx:FloParser.StatementContext):
        pass

    # Exit a parse tree produced by FloParser#statement.
    def exitStatement(self, ctx:FloParser.StatementContext):
        pass


    # Enter a parse tree produced by FloParser#component.
    def enterComponent(self, ctx:FloParser.ComponentContext):
        pass

    # Exit a parse tree produced by FloParser#component.
    def exitComponent(self, ctx:FloParser.ComponentContext):
        pass


    # Enter a parse tree produced by FloParser#module.
    def enterModule(self, ctx:FloParser.ModuleContext):
        mod_name = ctx.children[1].getText()
        print("Module", mod_name)
        pass

    # Exit a parse tree produced by FloParser#module.
    def exitModule(self, ctx:FloParser.ModuleContext):
        pass

if __name__ == "__main__":
    file = sys.argv[1]
    FloListenerImpl.loadModule(file)