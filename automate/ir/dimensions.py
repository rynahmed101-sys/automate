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
        Parses dimension strings like 'M*L^2*T^-2', 'M*T^-2', 'L', '1', or ''
        """
        if not dim_str or dim_str.strip() in ("", "1", "dimensionless"):
            return cls.dimensionless()

        s = dim_str.replace(" ", "")
        # Split by multiplication or division
        # Simple parser for products like M * L^2 * T^-2
        tokens = re.split(r'[*]', s)
        exponents: Dict[str, int] = {}

        for token in tokens:
            if not token:
                continue
            if "/" in token:
                parts = token.split("/")
                num = parts[0]
                den = parts[1]
                if num and num != "1":
                    d_num = cls.from_string(num)
                    for k, v in d_num.exponents.items():
                        exponents[k] = exponents.get(k, 0) + v
                if den:
                    d_den = cls.from_string(den)
                    for k, v in d_den.exponents.items():
                        exponents[k] = exponents.get(k, 0) - v
                continue

            if "^" in token:
                base, exp = token.split("^")
                exponents[base] = exponents.get(base, 0) + int(exp)
            else:
                exponents[token] = exponents.get(token, 0) + 1

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
