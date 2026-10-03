"""
Automate: A local-first, machine-checkable formal physics derivation engine.

Unifies symbolic calculus, formal proof checking, numerical simulation,
statistical inference, dimensional validation, and hierarchical derivation graphs.
"""

__version__ = "0.1.0"
__author__ = "Automate Contributors"

from automate.core.status import VerificationStatus
from automate.core.node import DerivationNode
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph

__all__ = [
    "VerificationStatus",
    "DerivationNode",
    "DerivationEdge",
    "DerivationGraph",
]
