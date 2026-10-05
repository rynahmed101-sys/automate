"""Reusable electromagnetism representations and verification machinery."""
from automate.electromagnetism.representation import (
    ElectromagneticField, ElectromagneticSource, ElectromagneticPotentials,
    ConstitutiveModel, ElectromagneticSystem,
)
from automate.electromagnetism.maxwell import MaxwellVerifier, LorentzForceCalculator, PoyntingVerifier
__all__ = [
    "ElectromagneticField", "ElectromagneticSource", "ElectromagneticPotentials",
    "ConstitutiveModel", "ElectromagneticSystem",
    "MaxwellVerifier", "LorentzForceCalculator", "PoyntingVerifier",
]
