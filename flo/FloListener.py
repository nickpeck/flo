# Generated from flo\Flo.g4 by ANTLR 4.7
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .FloParser import FloParser
else:
    from FloParser import FloParser

# This class defines a complete listener for a parse tree produced by FloParser.
class FloListener(ParseTreeListener):

    # Enter a parse tree produced by FloParser#number.
    def enterNumber(self, ctx:FloParser.NumberContext):
        pass

    # Exit a parse tree produced by FloParser#number.
    def exitNumber(self, ctx:FloParser.NumberContext):
        pass


    # Enter a parse tree produced by FloParser#tuple.
    def enterTuple(self, ctx:FloParser.TupleContext):
        pass

    # Exit a parse tree produced by FloParser#tuple.
    def exitTuple(self, ctx:FloParser.TupleContext):
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


    # Enter a parse tree produced by FloParser#import_statement.
    def enterImport_statement(self, ctx:FloParser.Import_statementContext):
        pass

    # Exit a parse tree produced by FloParser#import_statement.
    def exitImport_statement(self, ctx:FloParser.Import_statementContext):
        pass


    # Enter a parse tree produced by FloParser#simpleDeclaration.
    def enterSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        pass

    # Exit a parse tree produced by FloParser#simpleDeclaration.
    def exitSimpleDeclaration(self, ctx:FloParser.SimpleDeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#computedDeclaration.
    def enterComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        pass

    # Exit a parse tree produced by FloParser#computedDeclaration.
    def exitComputedDeclaration(self, ctx:FloParser.ComputedDeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#filterDeclaration.
    def enterFilterDeclaration(self, ctx:FloParser.FilterDeclarationContext):
        pass

    # Exit a parse tree produced by FloParser#filterDeclaration.
    def exitFilterDeclaration(self, ctx:FloParser.FilterDeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#joinDeclaration.
    def enterJoinDeclaration(self, ctx:FloParser.JoinDeclarationContext):
        pass

    # Exit a parse tree produced by FloParser#joinDeclaration.
    def exitJoinDeclaration(self, ctx:FloParser.JoinDeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#declaration.
    def enterDeclaration(self, ctx:FloParser.DeclarationContext):
        pass

    # Exit a parse tree produced by FloParser#declaration.
    def exitDeclaration(self, ctx:FloParser.DeclarationContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_join.
    def enterCompound_expression_join(self, ctx:FloParser.Compound_expression_joinContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_join.
    def exitCompound_expression_join(self, ctx:FloParser.Compound_expression_joinContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_filter.
    def enterCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_filter.
    def exitCompound_expression_filter(self, ctx:FloParser.Compound_expression_filterContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_not.
    def enterCompound_expression_not(self, ctx:FloParser.Compound_expression_notContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_not.
    def exitCompound_expression_not(self, ctx:FloParser.Compound_expression_notContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_comparison.
    def enterCompound_expression_comparison(self, ctx:FloParser.Compound_expression_comparisonContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_comparison.
    def exitCompound_expression_comparison(self, ctx:FloParser.Compound_expression_comparisonContext):
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


    # Enter a parse tree produced by FloParser#compound_expression_putvalue.
    def enterCompound_expression_putvalue(self, ctx:FloParser.Compound_expression_putvalueContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_putvalue.
    def exitCompound_expression_putvalue(self, ctx:FloParser.Compound_expression_putvalueContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression.
    def enterCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression.
    def exitCompound_expression(self, ctx:FloParser.Compound_expressionContext):
        pass


    # Enter a parse tree produced by FloParser#compound_expression_paren.
    def enterCompound_expression_paren(self, ctx:FloParser.Compound_expression_parenContext):
        pass

    # Exit a parse tree produced by FloParser#compound_expression_paren.
    def exitCompound_expression_paren(self, ctx:FloParser.Compound_expression_parenContext):
        pass


    # Enter a parse tree produced by FloParser#statement.
    def enterStatement(self, ctx:FloParser.StatementContext):
        pass

    # Exit a parse tree produced by FloParser#statement.
    def exitStatement(self, ctx:FloParser.StatementContext):
        pass


    # Enter a parse tree produced by FloParser#sync_block.
    def enterSync_block(self, ctx:FloParser.Sync_blockContext):
        pass

    # Exit a parse tree produced by FloParser#sync_block.
    def exitSync_block(self, ctx:FloParser.Sync_blockContext):
        pass


    # Enter a parse tree produced by FloParser#statements.
    def enterStatements(self, ctx:FloParser.StatementsContext):
        pass

    # Exit a parse tree produced by FloParser#statements.
    def exitStatements(self, ctx:FloParser.StatementsContext):
        pass


    # Enter a parse tree produced by FloParser#component.
    def enterComponent(self, ctx:FloParser.ComponentContext):
        pass

    # Exit a parse tree produced by FloParser#component.
    def exitComponent(self, ctx:FloParser.ComponentContext):
        pass


    # Enter a parse tree produced by FloParser#module.
    def enterModule(self, ctx:FloParser.ModuleContext):
        pass

    # Exit a parse tree produced by FloParser#module.
    def exitModule(self, ctx:FloParser.ModuleContext):
        pass


