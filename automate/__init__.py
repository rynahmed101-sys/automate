"""Automate: a local-first mathematics and physics calculator for AI systems."""

__version__ = "0.3.0"
__author__ = "Automate Contributors"

from automate.core.status import VerificationStatus
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.calculator import CALCULATOR_OPERATIONS, CalculatorError, calculate

__all__ = [
    "VerificationStatus",
    "DerivationNode",
    "DerivationEdge",
    "DerivationGraph",
]
