"""
Physical dimension and unit representation for Automate.
Implements dimensional analysis based on the SI base dimensions:
[M] Mass, [L] Length, [T] Time, [Q] Electric Charge / [I] Current,
[Theta] Temperature, [N] Amount of substance, [J] Luminous intensity.
"""

from typing import Dict, Any, Optional
import re


class Dimension:
    """
    Represents a physical dimension as exponents of base SI dimensions.
    """
    BASE_DIMENSIONS = ("M", "L", "T", "I", "Theta", "N", "J")

    def __init__(self, exponents: Optional[Dict[str, int]] = None):
        self.exponents: Dict[str, int] = {}
        if exponents:
            for k, v in exponents.items():
                if k in self.BASE_DIMENSIONS and v != 0:
                    self.exponents[k] = int(v)

    @classmethod
    def dimensionless(cls) -> "Dimension":
        return cls({})

    @classmethod
    def mass(cls) -> "Dimension":
        return cls({"M": 1})

    @classmethod
    def length(cls) -> "Dimension":
        return cls({"L": 1})

    @classmethod
    def time(cls) -> "Dimension":
        return cls({"T": 1})

    @classmethod
    def velocity(cls) -> "Dimension":
        return cls({"L": 1, "T": -1})

    @classmethod
    def acceleration(cls) -> "Dimension":
        return cls({"L": 1, "T": -2})

    @classmethod
    def force(cls) -> "Dimension":
        return cls({"M": 1, "L": 1, "T": -2})

    @classmethod
    def energy(cls) -> "Dimension":
        return cls({"M": 1, "L": 2, "T": -2})

    @classmethod
    def action(cls) -> "Dimension":
        return cls({"M": 1, "L": 2, "T": -1})

    @classmethod
    def spring_constant(cls) -> "Dimension":
        return cls({"M": 1, "T": -2})

    @classmethod
    def frequency(cls) -> "Dimension":
        return cls({"T": -1})

    @classmethod
    def from_string(cls, dim_str: str) -> "Dimension":
        """
        Parse SI-base dimension expressions such as M*L^2*T^-2 or M/L/T.
        Unknown dimensions and malformed exponents are rejected instead of
        silently collapsing to dimensionless.
        """
        if not isinstance(dim_str, str):
            raise TypeError("Dimension string must be a string.")

        s = dim_str.replace(" ", "")
        if not s or s in ("1", "dimensionless"):
            return cls.dimensionless()

        tokens = re.split(r"([*/])", s)
        exponents: Dict[str, int] = {}
        sign = 1
        expect_factor = True

        for token in tokens:
            if token == "":
                continue
            if token == "*":
                if expect_factor:
                    raise ValueError(f"Malformed dimension expression: {dim_str!r}")
                expect_factor = True
                continue
            if token == "/":
                if expect_factor:
                    raise ValueError(f"Malformed dimension expression: {dim_str!r}")
                sign = -1
                expect_factor = True
                continue

            match = re.fullmatch(r"([A-Za-z]+)(?:\^(-?\d+))?", token)
            if not match:
                raise ValueError(f"Malformed dimension factor: {token!r}")

            base = match.group(1)
            if base not in cls.BASE_DIMENSIONS:
                raise ValueError(
                    f"Unknown base dimension {base!r}. "
                    f"Expected one of: {', '.join(cls.BASE_DIMENSIONS)}"
                )

            exponent = int(match.group(2) or "1")
            exponents[base] = exponents.get(base, 0) + sign * exponent
            sign = 1
            expect_factor = False

        if expect_factor:
            raise ValueError(f"Malformed dimension expression: {dim_str!r}")

        return cls(exponents)

    def is_dimensionless(self) -> bool:
        return len(self.exponents) == 0

    def __mul__(self, other: "Dimension") -> "Dimension":
        new_exp = dict(self.exponents)
        for k, v in other.exponents.items():
            new_exp[k] = new_exp.get(k, 0) + v
        return Dimension(new_exp)

    def __truediv__(self, other: "Dimension") -> "Dimension":
        new_exp = dict(self.exponents)
        for k, v in other.exponents.items():
            new_exp[k] = new_exp.get(k, 0) - v
        return Dimension(new_exp)

    def __pow__(self, power: int) -> "Dimension":
        return Dimension({k: v * power for k, v in self.exponents.items()})

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Dimension):
            return False
        return self.exponents == other.exponents

    def __repr__(self) -> str:
        if self.is_dimensionless():
            return "Dimension(1)"
        parts = []
        for k in self.BASE_DIMENSIONS:
            if k in self.exponents:
                exp = self.exponents[k]
                if exp == 1:
                    parts.append(k)
                else:
                    parts.append(f"{k}^{exp}")
        return "*".join(parts)

    def to_dict(self) -> Dict[str, int]:
        return dict(self.exponents)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Dimension":
        return cls(data)
