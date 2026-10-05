"""
Verification backends for Automate.
"""

from automate.backend.base import BaseChecker, VerificationReport, VerificationEvidence
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.backend.tensor_backend import TensorChecker

__all__ = [
    "BaseChecker",
    "VerificationReport",
    "VerificationEvidence",
    "DimensionChecker",
    "SymPyChecker",
    "LeanChecker",
    "NumericalChecker",
    "StatisticalChecker",
    "TensorChecker",
]


from automate.backend.linear_algebra_backend import LinearAlgebraChecker
