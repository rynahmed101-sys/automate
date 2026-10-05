"""Reusable classical electromagnetism representations.
This layer describes fields, sources, potentials, and constitutive assumptions
without hard-coding a named solution.
"""
from typing import List
from pydantic import BaseModel, Field, ConfigDict

class ElectromagneticField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    electric: str
    magnetic: str
    independent_variables: List[str] = Field(default_factory=lambda: ["t", "x", "y", "z"])
    units: str = "SI"
    assumptions: List[str] = Field(default_factory=list)

class ElectromagneticSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    charge_density: str = "0"
    current_density: str = "0"
    independent_variables: List[str] = Field(default_factory=lambda: ["t", "x", "y", "z"])
    assumptions: List[str] = Field(default_factory=list)

class ElectromagneticPotentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scalar_potential: str
    vector_potential: str
    gauge: str = ""
    assumptions: List[str] = Field(default_factory=list)

class ConstitutiveModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permittivity: str = "epsilon"
    permeability: str = "mu"
    electric_relation: str = "D = epsilon*E"
    magnetic_relation: str = "H = B/mu"
    assumptions: List[str] = Field(default_factory=list)

class ElectromagneticSystem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: ElectromagneticField
    source: ElectromagneticSource = Field(default_factory=ElectromagneticSource)
    potentials: ElectromagneticPotentials | None = None
    constitutive: ConstitutiveModel = Field(default_factory=ConstitutiveModel)
    assumptions: List[str] = Field(default_factory=list)

    def has_dynamic_sources(self) -> bool:
        return any(v.strip() not in {"0", "0.0"} for v in (self.source.charge_density, self.source.current_density))

    def has_potentials(self) -> bool:
        return self.potentials is not None