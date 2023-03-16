"""
Some functions and a class designed to assist in testing semantic analysis
of Nimble programs.

Authors: Greg Phillips

Version: 2021-02-27

"""

from collections import defaultdict

from antlr4 import ParserRuleContext, ParseTreeWalker
from generic_parser import parse
from nimble import NimbleLexer, NimbleParser, NimbleListener
from .errorlog import ErrorLog
from .nimblesemantics import InferTypesAndCheckConstraints, DefineScopesAndSymbols


def do_semantic_analysis(source, start_rule_name, first_phase_only=False):
    """
    Runs semantic analysis on the source, then runs the `TestValuesCollector`
    to collect types and scopes.

    The semantic analyis is in two phases:

    - DefineScopesAndSymbols, then
    - InferTypesAndCheckConstraints

    The second phase can be switched off using the first_phase_only parameter,
    where testing just the results of the first phase is desired.
    """

    tree = parse(source, start_rule_name, NimbleLexer, NimbleParser)
    errors = ErrorLog()
    walker = ParseTreeWalker()

    walker.walk(DefineScopesAndSymbols(errors), tree)

    if not first_phase_only:
        walker.walk(InferTypesAndCheckConstraints(errors), tree)

    type_collector = ExpressionTypeCollector()
    walker.walk(type_collector, tree)

    global_scope = tree.scope if hasattr(tree, 'scope') else None
    return errors, global_scope, type_collector.inferred_types


class ExpressionTypeCollector(NimbleListener):
    """
    Collects the inferred types of all expressions in a script in an indexed form,
    to assist with testing. Relies on the type of each expression being stored
    in a `type` attribute on the parse tree node.

    self.inferred_types is a dictionary of dictionaries. The outer key is the line
    number, and the inner key is the expression source, with all whitespace removed,
    as returned by ctx.getText()
    """

    def __init__(self):
        self.inferred_types = defaultdict(dict)

    def exitEveryRule(self, ctx: ParserRuleContext):
        if (isinstance(ctx, NimbleParser.ExprContext) or
                isinstance(ctx, NimbleParser.FuncCallStmtContext)):
            line = ctx.start.line
            source = ctx.getText()
            inferred_type = ctx.type if hasattr(ctx, 'type') else None
            self.inferred_types[line][source] = inferred_type


def pretty_types(inferred_types):
    """
    Returns a well-formatted string for inferred_types, as generated by
    the ExpressionTypeCollector; useful for debugging.
    """
    output = []
    for line_number in sorted(inferred_types.keys()):
        output.append(f'line {line_number}:')
        for expr in sorted(inferred_types[line_number]):
            output.append(f'  {expr} : {inferred_types[line_number][expr]}')
    return '\n'.join(output)
