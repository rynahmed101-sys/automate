"""Reusable harmonic-wave and basic-optics representations and verification."""
from .core import (
    HarmonicWave, superpose, standing_wave, dispersion_relation,
    ReflectionRefraction, PolarizationState, diffraction_single_slit,
)
__all__ = ["HarmonicWave","superpose","standing_wave","dispersion_relation",
           "ReflectionRefraction","PolarizationState","diffraction_single_slit"]
