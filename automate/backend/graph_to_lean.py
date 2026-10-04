"""Graph-bound translation from Automate mathematical IR to Lean 4.

This module translates the *actual graph claim* into a Lean proposition. It
does not decide truth and does not inject a canned theorem corresponding to a
named physics law. Unsupported mathematical constructs fail explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import sympy as sp
from sympy.core.relational import Relational

from automate.ir.safe_parser import SafeParser, SafeParseError


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
_MAX_NODES = 160
_MAX_POWER = 12


class GraphToLeanTranslationError(ValueError):
    """Raised when a graph claim cannot be faithfully represented in Lean."""


@dataclass(frozen=True)
class LeanClaim:
    """Translated proposition plus the exact graph expressions that produced it."""

    proposition: str
    binders: List[str]
    source_nodes: List[Dict[str, Any]]
    relation: str


def _check_identifier(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise GraphToLeanTranslationError(
            f"Unsupported Lean identifier: {name!r}"
        )
    if name in {
        "theorem", "example", "def", "let", "fun", "match", "where", "if",
        "then", "else", "namespace", "end", "import", "open", "variable",
        "section", "protected", "private", "mutual", "inductive",
    }:
        raise GraphToLeanTranslationError(
            f"Lean keyword cannot be used as a graph symbol: {name!r}"
        )
    return name


def _check_size(expr: sp.Basic) -> None:
    size = sum(1 for _ in sp.preorder_traversal(expr))
    if size > _MAX_NODES:
        raise GraphToLeanTranslationError(
            f"Expression exceeds graph-to-Lean node budget ({_MAX_NODES})."
        )


def _translate_arithmetic(expr: sp.Basic) -> str:
    if isinstance(expr, sp.Integer):
        return str(int(expr))

    if isinstance(expr, sp.Symbol):
        return _check_identifier(expr.name)

    if isinstance(expr, sp.Add):
        terms = [_translate_arithmetic(arg) for arg in expr.args]
        return "(" + " + ".join(terms) + ")"

    if isinstance(expr, sp.Mul):
        factors = [_translate_arithmetic(arg) for arg in expr.args]
        return "(" + " * ".join(factors) + ")"

    if isinstance(expr, sp.Pow):
        base, exponent = expr.args
        if not isinstance(exponent, sp.Integer):
            raise GraphToLeanTranslationError(
                "Only non-negative integer powers are supported."
            )
        power = int(exponent)
        if power < 0 or power > _MAX_POWER:
            raise GraphToLeanTranslationError(
                f"Power {power} is outside supported range 0..{_MAX_POWER}."
            )
        return f"({_translate_arithmetic(base)} ^ {power})"

    raise GraphToLeanTranslationError(
        f"Unsupported arithmetic construct: {type(expr).__name__}"
    )


def translate_integer_expression(expr: sp.Basic) -> Tuple[str, List[str]]:
    """Translate an already-parsed integer arithmetic expression."""
    _check_size(expr)
    for atom in expr.atoms(sp.Rational):
        if type(atom) is sp.Rational and atom.q != 1:
            raise GraphToLeanTranslationError(
                "Non-integer rational coefficients are not supported."
            )
    names = sorted(
        _check_identifier(symbol.name)
        for symbol in expr.free_symbols
    )
    return _translate_arithmetic(expr), names


def _translate_atom(expr: sp.Basic) -> str:
    if isinstance(expr, Relational):
        lhs = _translate_arithmetic(expr.lhs)
        rhs = _translate_arithmetic(expr.rhs)

        if isinstance(expr, sp.Equality):
            return f"(({lhs} : Int) = ({rhs} : Int))"
        if isinstance(expr, sp.Unequality):
            return f"(({lhs} : Int) != ({rhs} : Int))"
        if isinstance(expr, sp.StrictGreaterThan):
            return f"(({lhs} : Int) > ({rhs} : Int))"
        if isinstance(expr, sp.StrictLessThan):
            return f"(({lhs} : Int) < ({rhs} : Int))"
        if isinstance(expr, sp.GreaterThan):
            return f"(({lhs} : Int) >= ({rhs} : Int))"
        if isinstance(expr, sp.LessThan):
            return f"(({lhs} : Int) <= ({rhs} : Int))"

        raise GraphToLeanTranslationError(
            f"Unsupported relational construct: {type(expr).__name__}"
        )

    return _translate_arithmetic(expr)


_RELATION_PATTERN = re.compile(r"(?P<op><=|>=|!=|=|<|>)")


def _parse_node(raw: str) -> sp.Basic:
    parser = SafeParser()
    text = raw.strip()
    try:
        match = _RELATION_PATTERN.search(text)
        if match:
            operator = match.group("op")
            lhs_text = text[: match.start()].strip()
            rhs_text = text[match.end() :].strip()
            if not lhs_text or not rhs_text:
                raise GraphToLeanTranslationError(
                    "Relation must contain non-empty left and right expressions."
                )
            lhs = parser.parse(lhs_text)
            rhs = parser.parse(rhs_text)
            relation_types = {
                "=": sp.Eq,
                "!=": sp.Ne,
                ">": sp.Gt,
                "<": sp.Lt,
                ">=": sp.Ge,
                "<=": sp.Le,
            }
            return relation_types[operator](lhs, rhs)
        return parser.parse(text)
    except SafeParseError as exc:
        raise GraphToLeanTranslationError(
            f"SafeParser rejected graph expression: {exc}"
        ) from exc


def _expression_and_symbols(expr: sp.Basic) -> Tuple[str, List[str]]:
    _check_size(expr)
    code = _translate_atom(expr)
    names = sorted(
        _check_identifier(symbol.name)
        for symbol in expr.free_symbols
    )
    return code, names


def translate_node_expression(raw_expression: str) -> Tuple[str, List[str]]:
    """Translate one graph node expression/equation into a Lean proposition/expression."""
    raw = raw_expression.strip()
    if not raw:
        raise GraphToLeanTranslationError("Graph node expression is empty.")
    expr = _parse_node(raw)
    return _expression_and_symbols(expr)


def translate_edge_claim(
    rule: str,
    input_expressions: Sequence[str],
    output_expressions: Sequence[str],
) -> LeanClaim:
    """
    Translate an edge into a graph-bound Lean proposition.

    Supported generic relations:
      - algebraic_identity / identity_claim / equivalent:
          first input expression equals first output expression
      - implies:
          all input propositions imply the first output proposition

    The translator intentionally refuses to infer physical laws from the rule
    name. A caller must provide graph mathematics that can itself be translated.
    """
    if not input_expressions:
        raise GraphToLeanTranslationError(
            "Graph-to-Lean translation requires at least one input expression."
        )
    if not output_expressions:
        raise GraphToLeanTranslationError(
            "Graph-to-Lean translation requires at least one output expression."
        )

    rule_name = str(rule)

    parsed_inputs = [_parse_node(raw) for raw in input_expressions]
    parsed_outputs = [_parse_node(raw) for raw in output_expressions]

    translated_inputs = []
    translated_outputs = []
    symbols: set[str] = set()

    for expr in parsed_inputs:
        code, names = _expression_and_symbols(expr)
        translated_inputs.append(code)
        symbols.update(names)

    for expr in parsed_outputs:
        code, names = _expression_and_symbols(expr)
        translated_outputs.append(code)
        symbols.update(names)

    if rule_name in {"algebraic_identity", "identity_claim", "equivalent"}:
        if len(parsed_inputs) != 1 or len(parsed_outputs) != 1:
            raise GraphToLeanTranslationError(
                f"Rule '{rule_name}' requires exactly one input and one output "
                "expression for an equality claim."
            )
        proposition = f"{translated_inputs[0]} = {translated_outputs[0]}"
        relation = "equality"
    elif rule_name == "implies":
        if not all(isinstance(expr, sp.Relational) for expr in [*parsed_inputs, *parsed_outputs]):
            raise GraphToLeanTranslationError(
                "The generic 'implies' relation requires proposition/equation nodes."
            )
        conclusion = translated_outputs[0]
        hypotheses = translated_inputs
        proposition = conclusion
        for hypothesis in reversed(hypotheses):
            proposition = f"({hypothesis}) -> ({proposition})"
        relation = "implication"
    else:
        raise GraphToLeanTranslationError(
            f"Rule '{rule_name}' has no generic graph-to-Lean relation mapping."
        )

    return LeanClaim(
        proposition=proposition,
        binders=sorted(symbols),
        source_nodes=[
            *[
                {"role": "input", "raw_expression": raw}
                for raw in input_expressions
            ],
            *[
                {"role": "output", "raw_expression": raw}
                for raw in output_expressions
            ],
        ],
        relation=relation,
    )
