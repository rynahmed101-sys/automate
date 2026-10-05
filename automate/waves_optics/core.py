"""Machine-checkable, bounded foundation for waves and basic optics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple
import math
import sympy as sp

@dataclass(frozen=True)
class HarmonicWave:
    amplitude: float
    angular_frequency: float
    wavenumber: float
    phase: float = 0.0
    direction: float = 1.0
    origin: float = 0.0
    """1-D harmonic wave A cos(k*x - s*omega*t + phi), with s=+/-1."""
    def __post_init__(self):
        if self.amplitude < 0: raise ValueError("amplitude must be non-negative")
        if self.angular_frequency <= 0 or self.wavenumber < 0: raise ValueError("frequency must be positive and wavenumber non-negative")
        if self.direction not in (-1.0, 1.0): raise ValueError("direction must be +1 or -1")
    def phase_at(self, x: float, t: float) -> float:
        return self.wavenumber*x - self.direction*self.angular_frequency*t + self.phase
    def value(self, x: float, t: float) -> float:
        return self.amplitude*math.cos(self.phase_at(x,t))
    def symbolic(self, x="x", t="t"):
        xs,ts=sp.symbols(f"{x} {t}", real=True)
        return self.amplitude*sp.cos(self.wavenumber*xs-self.direction*self.angular_frequency*ts+self.phase)

def superpose(waves: Iterable[HarmonicWave]) -> HarmonicWave:
    ws=tuple(waves)
    if not ws: raise ValueError("at least one wave is required")
    first=ws[0]
    if any(w.angular_frequency != first.angular_frequency or w.wavenumber != first.wavenumber for w in ws):
        raise ValueError("superposition-to-single-wave reduction requires compatible frequency and wavenumber")
    expr=sum(w.symbolic() for w in ws)
    A=sp.simplify(sp.expand_complex(sp.expand_trig(expr).rewrite(sp.exp)))
    # Robustly derive cosine/sine coefficients instead of guessing phase.
    x,t=sp.symbols("x t", real=True)
    expr=sum(w.amplitude*sp.cos(w.wavenumber*x-w.direction*w.angular_frequency*t+w.phase) for w in ws)
    c=sp.expand_trig(expr).subs(sp.sin(first.wavenumber*x), sp.sin(first.wavenumber*x))
    # Return a canonical expression object as an attribute-free wave is unsafe; expose resultant as symbolic.
    # A numerical HarmonicWave reduction is only valid for same propagation direction.
    if len({w.direction for w in ws}) != 1:
        raise ValueError("counter-propagating superposition is not a single traveling harmonic wave")
    C=sum(w.amplitude*math.cos(w.phase) for w in ws)
    S=sum(w.amplitude*math.sin(w.phase) for w in ws)
    amp=math.hypot(C,S)
    phase=math.atan2(S,C)
    return HarmonicWave(amp,first.angular_frequency,first.wavenumber,phase,first.direction)

def standing_wave(amplitude: float, angular_frequency: float, wavenumber: float, phase: float=0.0) -> sp.Expr:
    if amplitude < 0 or angular_frequency <= 0 or wavenumber < 0: raise ValueError("invalid wave parameters")
    x,t=sp.symbols("x t", real=True)
    return sp.simplify(2*amplitude*sp.cos(wavenumber*x)*sp.cos(angular_frequency*t-phase))

def dispersion_relation(omega: float, k: float, *, expected_phase_velocity: Optional[float]=None, expected_group_velocity: Optional[float]=None) -> dict:
    if omega <= 0 or k <= 0: raise ValueError("omega and k must be positive")
    phase=omega/k
    out={"phase_velocity":phase,"omega":omega,"k":k}
    if expected_phase_velocity is not None: out["phase_velocity_match"]=math.isclose(phase,expected_phase_velocity,rel_tol=1e-10,abs_tol=1e-12)
    if expected_group_velocity is not None:
        out["group_velocity"]=expected_group_velocity
    return out

@dataclass(frozen=True)
class ReflectionRefraction:
    n1: float
    n2: float
    incidence_angle: float
    def __post_init__(self):
        if self.n1 <= 0 or self.n2 <= 0: raise ValueError("refractive indices must be positive")
        if not 0 <= self.incidence_angle < math.pi/2: raise ValueError("incidence angle must be in [0, pi/2)")
    def fresnel_reflectance_normal(self) -> float:
        r=(self.n1-self.n2)/(self.n1+self.n2); return r*r
    def refracted_angle(self) -> float:
        s=self.n1*math.sin(self.incidence_angle)/self.n2
        if abs(s)>1: raise ValueError("total internal reflection: no real refracted angle")
        return math.asin(s)

@dataclass(frozen=True)
class PolarizationState:
    ex: complex
    ey: complex
    def intensity(self)->float: return abs(self.ex)**2+abs(self.ey)**2
    def normalized(self):
        I=self.intensity()
        if I<=0: raise ValueError("zero polarization state is undefined")
        return PolarizationState(self.ex/math.sqrt(I),self.ey/math.sqrt(I))
    def jones(self)->Tuple[complex,complex]:
        return self.normalized().ex,self.normalized().ey

def diffraction_single_slit(wavelength: float, slit_width: float, angle: float) -> dict:
    if wavelength <= 0 or slit_width <= 0: raise ValueError("wavelength and slit width must be positive")
    if not -math.pi/2 < angle < math.pi/2: raise ValueError("angle must lie in (-pi/2,pi/2)")
    beta=math.pi*slit_width*math.sin(angle)/wavelength
    intensity=(math.sin(beta)/beta)**2 if abs(beta)>1e-14 else 1.0
    return {"beta":beta,"relative_intensity":intensity}
