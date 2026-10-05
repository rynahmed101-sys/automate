"""Reusable classical-mechanics representations built on Automate's symbolic engine.

These objects describe mechanical structure (coordinates, kinematics, energies,
forces, and constraints) without encoding named textbook solutions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import sympy as sp

from automate.ir.safe_parser import SafeParser

class GeneralizedCoordinate(BaseModel):
    """A generalized coordinate q_i with explicit domain/dimension metadata."""
    model_config = ConfigDict(extra="forbid")
    name: str
    domain: str = "real"
    dimension: str = ""
    assumptions: List[str] = Field(default_factory=list)

class KinematicQuantity(BaseModel):
    """Position/velocity/acceleration representation for one generalized coordinate."""
    model_config = ConfigDict(extra="forbid")
    coordinate: str
    velocity: str
    acceleration: str

class GeneralizedForce(BaseModel):
    """Generalized force Q_i conjugate to a generalized coordinate q_i."""
    model_config = ConfigDict(extra="forbid")
    coordinate: str
    expression: str
    dimension: str = ""
    assumptions: List[str] = Field(default_factory=list)

class MechanicalConstraint(BaseModel):
    """Explicit holonomic/nonholonomic constraint relation."""
    model_config = ConfigDict(extra="forbid")
    expression: str
    kind: str = "holonomic"
    equality: str = "zero"
    assumptions: List[str] = Field(default_factory=list)

class MechanicalSystemRepresentation(BaseModel):
    """Canonical high-level representation of a finite-dimensional mechanical system."""
    model_config = ConfigDict(extra="forbid")
    coordinates: List[GeneralizedCoordinate]
    kinetic_energy: str
    potential_energy: str = "0"
    forces: List[GeneralizedForce] = Field(default_factory=list)
    constraints: List[MechanicalConstraint] = Field(default_factory=list)
    time: str = "t"
    parameters: Dict[str, str] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)

    def _symbols(self) -> Dict[str, Any]:
        local: Dict[str, Any] = {self.time: sp.Symbol(self.time, real=True)}
        for name, prop in self.parameters.items():
            local[name] = sp.Symbol(name, positive=(prop == "positive"), real=True)
        for q in self.coordinates:
            qf = sp.Function(q.name)(local[self.time])
            local[q.name] = qf
            local[f"{q.name}_dot"] = sp.diff(qf, local[self.time])
            local[f"{q.name}_ddot"] = sp.diff(qf, local[self.time], 2)
        return local

    def parse(self, expression: str) -> sp.Expr:
        """Parse a symbolic mechanics expression through the safe parser."""
        return SafeParser(extra_symbols=self._symbols()).parse(expression)

    def lagrangian(self) -> sp.Expr:
        """Return canonical L = T - V."""
        return sp.simplify(self.parse(self.kinetic_energy) - self.parse(self.potential_energy))

    def mechanical_energy(self) -> sp.Expr:
        """Return E = T + V."""
        return sp.simplify(self.parse(self.kinetic_energy) + self.parse(self.potential_energy))

    def kinematics(self) -> List[KinematicQuantity]:
        """Return explicit first/second time derivatives for every coordinate."""
        return [KinematicQuantity(coordinate=q.name, velocity=f"d({q.name})/d{self.time}", acceleration=f"d2({q.name})/d{self.time}2") for q in self.coordinates]

    def constraint_residuals(self) -> Dict[str, sp.Expr]:
        """Return symbolic residuals; nonzero residuals are explicit violations."""
        return {c.expression: sp.simplify(self.parse(c.expression)) for c in self.constraints}

    def generalized_force_map(self) -> Dict[str, sp.Expr]:
        """Return Q_i expressions keyed by generalized coordinate."""
        names = {q.name for q in self.coordinates}
        unknown = [f.coordinate for f in self.forces if f.coordinate not in names]
        if unknown:
            raise ValueError(f"Force references unknown generalized coordinate(s): {unknown}")
        return {f.coordinate: sp.simplify(self.parse(f.expression)) for f in self.forces}

    def as_lagrangian_system(self):
        """Construct the existing reusable LagrangianSystem from this representation."""
        from automate.mechanics.lagrangian import LagrangianSystem
        return LagrangianSystem(lagrangian=self.lagrangian(), coordinates=[q.name for q in self.coordinates], parameters=self.parameters, time_symbol=self.time)
