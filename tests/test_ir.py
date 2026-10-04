"""
Tests for Intermediate Representation (IR), AST, and Dimensional Analysis.
"""

import pytest
from automate.ir.dimensions import Dimension
from automate.ir.ast import (
    MathematicalExpression,
    PhysicalConstant,
    SymbolNode,
    NumberNode,
    EquationNode,
    DerivativeNode
)
from automate.ir.serialization import dump_json, load_json, dump_yaml, load_yaml


def test_dimension_arithmetic():
    # Base dimensions
    m = Dimension.mass()  # [M]
    l = Dimension.length()  # [L]
    t = Dimension.time()  # [T]

    # Velocity: [L][T]^-1
    v = l / t
    assert v == Dimension({"L": 1, "T": -1})
    assert v == Dimension.velocity()

    # Acceleration: [L][T]^-2
    a = v / t
    assert a == Dimension.acceleration()

    # Force: [M][L][T]^-2
    f = m * a
    assert f == Dimension.force()

    # Energy: [M][L]^2[T]^-2
    e = f * l
    assert e == Dimension.energy()

    # Spring constant: [Force] / [Length] = [M][T]^-2
    k = f / l
    assert k == Dimension.spring_constant()

    # Frequency: sqrt(k/m) -> [k] / [m] = [T]^-2 -> sqrt is [T]^-1
    omega_sq = k / m
    assert omega_sq == Dimension({"T": -2})


def test_dimension_from_string():
    d1 = Dimension.from_string("M*L^2*T^-2")
    assert d1 == Dimension.energy()

    d2 = Dimension.from_string("M*T^-2")
    assert d2 == Dimension.spring_constant()

    d3 = Dimension.from_string("L")
    assert d3 == Dimension.length()

    d4 = Dimension.from_string("1")
    assert d4.is_dimensionless()


def test_ast_serialization():
    expr = MathematicalExpression(
        raw_str="1/2 * m * x_dot**2 - 1/2 * k * x**2",
        dimension="M*L^2*T^-2",
        latex=r"\frac{1}{2}m\dot{x}^2 - \frac{1}{2}kx^2"
    )

    json_str = dump_json(expr)
    data = load_json(json_str)
    assert data["raw_str"] == "1/2 * m * x_dot**2 - 1/2 * k * x**2"
    assert data["dimension"] == "M*L^2*T^-2"
    assert data["schema_version"] == "0.1.0"

    yaml_str = dump_yaml(expr)
    yaml_data = load_yaml(yaml_str)
    assert yaml_data["raw_str"] == expr.raw_str


def test_physical_constant():
    c = PhysicalConstant(
        name="speed_of_light",
        symbol="c",
        value=299792458.0,
        dimension="L*T^-1",
        unit="m/s"
    )
    assert c.value == 299792458.0
    assert c.dimension == "L*T^-1"


def test_unknown_dimension_name_is_rejected():
    """Unknown physical dimensions must never collapse to dimensionless."""
    with pytest.raises(ValueError, match="Unknown base dimension"):
        Dimension.from_string("M*Bogus")

def test_malformed_dimension_exponent_is_rejected():
    """Malformed exponents must be rejected rather than silently coerced."""
    with pytest.raises(ValueError, match="must be an integer"):
        Dimension.from_string("L^not_an_integer")


def test_dimension_metadata_presence_is_distinct_from_dimensionless():
    unspecified = MathematicalExpression(raw_str="x")
    explicit = MathematicalExpression(raw_str="theta", dimension="dimensionless")

    assert unspecified.has_explicit_dimension is False
    assert explicit.has_explicit_dimension is True
    assert unspecified.get_dimension().is_dimensionless()
    assert explicit.get_dimension().is_dimensionless()
