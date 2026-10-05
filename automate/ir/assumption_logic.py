"""
Principled local assumption entailment for verification obligations.

This module deliberately exposes a narrow, auditable interface rather than
letting individual backends invent ad-hoc implication rules. It converts
declared scalar relational predicates into SymPy assumptions and asks SymPy's
assumption system whether a requested nonzero property follows.

Unsupported predicates or inconclusive entailment return False. No heuristic
fallback is treated as proof.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import sympy as sp

from automate.core.graph import DerivationGraph
from automate.ir.safe_parser import SafeParseError, SafeParser

_RELATION_RE = re.compile(r"^(.+?)\s*(>=|<=|!=|==|>|<)\s*(.+?)$")

# Names which are functions/constants in the SafeParser namespace rather than
# free scalar symbols. The actual allowlist remains owned by SafeParser.
_NON_SYMBOL_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "exp", "log", "sqrt", "Abs", "abs", "sign",
    "re", "im", "conjugate", "diff", "Derivative", "Integral",
    "pi", "E", "I", "oo", "zoo", "nan", "Symbol",
}


class AssumptionEntailment:
    """Evaluate explicit consequences of active graph assumptions."""

    def __init__(self, graph: DerivationGraph):
        self.graph = graph

    @staticmethod
    def _identifier_names(text: str) -> set[str]:
        return {
            name for name in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", text)
            if name not in _NON_SYMBOL_NAMES
        }

    @staticmethod
    def _relation_to_sympy(
        predicate: str,
        parser: SafeParser,
    ) -> Optional[sp.Boolean]:
        match = _RELATION_RE.match(predicate.strip())
        if not match:
            return None

        left_s, op, right_s = match.groups()
        try:
            left = parser.parse(left_s.strip())
            right = parser.parse(right_s.strip())
        except SafeParseError:
            return None

        relations = {
            "==": sp.Eq,
            "!=": sp.Ne,
            ">": sp.Gt,
            "<": sp.Lt,
            ">=": sp.Ge,
            "<=": sp.Le,
        }
        relation = relations.get(op)
        if relation is None:
            return None

        try:
            return relation(left, right)
        except (TypeError, ValueError):
            return None

    def _build_context(
        self,
        predicate_ids: Iterable[str],
        target_expr: sp.Expr,
    ) -> Tuple[SafeParser, Dict[str, sp.Symbol]]:
        texts: List[str] = [str(target_expr)]
        for aid in predicate_ids:
            assumption = self.graph.assumptions.get(aid)
            if assumption is not None:
                texts.append(assumption.formal_predicate)

        names: set[str] = set()
        for text in texts:
            names.update(self._identifier_names(text))

        # Relational assumptions are interpreted over real-valued scalar
        # quantities. Existing target symbols are replaced with these canonical
        # real symbols so SymPy's assumption engine can reason about them.
        symbols = {name: sp.Symbol(name, real=True) for name in sorted(names)}
        parser = SafeParser(extra_symbols=symbols)
        return parser, symbols

    def entails_nonzero(
        self,
        expr: sp.Expr,
        assumption_ids: Iterable[str],
    ) -> Tuple[bool, Optional[str]]:
        """Return whether active declared assumptions entail expr != 0.

        The returned source is one assumption ID only when SymPy can establish
        the nonzero consequence from the complete active assumption context.
        A missing, inactive, malformed, unsupported, or inconclusive premise
        never counts as proof.
        """
        ids = list(dict.fromkeys(assumption_ids))
        if expr.is_number:
            try:
                return bool(expr != 0), "__numeric_literal__" if expr != 0 else None
            except TypeError:
                return False, None

        active_ids = [
            aid for aid in ids
            if aid in self.graph.assumptions and self.graph.assumptions[aid].active
        ]
        if not active_ids:
            return False, None

        parser, symbols = self._build_context(active_ids, expr)
        normalized_expr = expr.xreplace({
            symbol: symbols.get(str(symbol), symbol)
            for symbol in expr.free_symbols
        })

        predicates: List[sp.Boolean] = []
        usable_ids: List[str] = []
        for aid in active_ids:
            predicate = self._relation_to_sympy(
                self.graph.assumptions[aid].formal_predicate,
                parser,
            )
            if predicate is None:
                continue
            predicates.append(predicate)
            usable_ids.append(aid)

        if not predicates:
            return False, None

        context = sp.And(*predicates)
        try:
            proved = sp.ask(sp.Q.nonzero(normalized_expr), assumptions=context)
        except Exception:
            return False, None

        if proved is True:
            # Prefer an assumption whose predicate directly names the divisor,
            # otherwise report the complete-context consequence without
            # pretending a single premise was sufficient.
            for aid in usable_ids:
                predicate = self.graph.assumptions[aid].formal_predicate.strip()
                if predicate in {
                    f"{normalized_expr} != 0",
                    f"{normalized_expr} > 0",
                    f"{normalized_expr} < 0",
                    f"{normalized_expr} >= 1",
                    f"{normalized_expr} <= -1",
                }:
                    return True, aid
            return True, "assumption_context"

        return False, None
