"""
Intermediate Representation (IR) module for Automate.
"""

from automate.ir.dimensions import Dimension
from automate.ir.assumptions import Assumption, AssumptionRegistry
from automate.ir.ast import (
    MathematicalExpression,
    PhysicalConstant,
    SymbolNode,
    NumberNode,
    EquationNode,
    DerivativeNode,
    IntegralNode,
    TensorNode,
    DifferentialEquationNode,
    StatisticalModelNode,
    ObservableNode,
)
from automate.ir.serialization import dump_json, load_json, dump_yaml, load_yaml

__all__ = [
    "Dimension",
    "Assumption",
    "AssumptionRegistry",
    "MathematicalExpression",
    "PhysicalConstant",
    "SymbolNode",
    "NumberNode",
    "EquationNode",
    "DerivativeNode",
    "IntegralNode",
    "TensorNode",
    "DifferentialEquationNode",
    "StatisticalModelNode",
    "ObservableNode",
    "dump_json",
    "load_json",
    "dump_yaml",
    "load_yaml",
]
