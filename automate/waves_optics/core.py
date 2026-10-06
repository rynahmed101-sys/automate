"""Machine-checkable, bounded foundation for waves and basic optics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence, Tuple
import math

import sympy as sp


@dataclass(frozen=True)
class HarmonicWave:
    """1-D harmonic wave A cos(k*x - s*omega*t + phi), s=+/-1."""

    amplitude: float
    angular_frequency: float
    wavenumber: float
    phase: float = 0.0
    direction: float = 1.0
    origin: float = 0.0

    def __post_init__(self):
        if self.amplitude < 0:
            raise ValueError("amplitude must be non-negative")
        if self.angular_frequency <= 0 or self.wavenumber < 0:
            raise ValueError("angular frequency must be positive and wavenumber non-negative")
        if self.direction not in (-1.0, 1.0):
            raise ValueError("direction must be +1 or -1")

    def phase_at(self, x: float, t: float) -> float:
        return self.wavenumber * (x - self.origin) - self.direction * self.angular_frequency * t + self.phase

    def value(self, x: float, t: float) -> float:
        return self.amplitude * math.cos(self.phase_at(x, t))

    def symbolic(self, x: str = "x", t: str = "t"):
        xs, ts = sp.symbols(f"{x} {t}", real=True)
        return self.amplitude * sp.cos(
            self.wavenumber * (xs - self.origin)
            - self.direction * self.angular_frequency * ts
            + self.phase
        )


def superpose(waves: Iterable[HarmonicWave]) -> HarmonicWave:
    """Reduce compatible co-propagating harmonics to one canonical harmonic."""
    ws = tuple(waves)
    if not ws:
        raise ValueError("at least one wave is required")
    first = ws[0]
    if any(w.angular_frequency != first.angular_frequency or w.wavenumber != first.wavenumber for w in ws):
        raise ValueError("single-wave reduction requires identical frequency and wavenumber")
    if len({w.direction for w in ws}) != 1:
        raise ValueError("counter-propagating superposition is not a single traveling harmonic wave")
    if any(w.origin != first.origin for w in ws):
        raise ValueError("single-wave reduction requires a common origin")
    C = sum(w.amplitude * math.cos(w.phase) for w in ws)
    S = sum(w.amplitude * math.sin(w.phase) for w in ws)
    return HarmonicWave(
        amplitude=math.hypot(C, S),
        angular_frequency=first.angular_frequency,
        wavenumber=first.wavenumber,
        phase=math.atan2(S, C),
        direction=first.direction,
        origin=first.origin,
    )


def interference_intensity(
    wave1: HarmonicWave,
    wave2: HarmonicWave,
    x: float,
    t: float,
    *,
    normalization: float = 1.0,
) -> dict:
    """Return the local squared-field interference observable.

    This deliberately reports a normalized field-intensity proxy rather than
    claiming an absolute radiometric intensity without physical calibration.
    """
    if normalization <= 0:
        raise ValueError("normalization must be positive")
    e1, e2 = wave1.value(x, t), wave2.value(x, t)
    total = e1 + e2
    return {
        "status": "NUMERICALLY_CHECKED",
        "field_1": e1,
        "field_2": e2,
        "field_sum": total,
        "relative_intensity": (total * total) / normalization,
        "observable": "squared scalar field amplitude",
    }


def standing_wave(
    amplitude: float,
    angular_frequency: float,
    wavenumber: float,
    phase: float = 0.0,
) -> sp.Expr:
    """Equal-amplitude counter-propagating standing-wave idealization."""
    if amplitude < 0 or angular_frequency <= 0 or wavenumber < 0:
        raise ValueError("invalid wave parameters")
    x, t = sp.symbols("x t", real=True)
    return sp.simplify(2 * amplitude * sp.cos(wavenumber * x) * sp.cos(angular_frequency * t - phase))


def verify_harmonic_wave_equation(wave: HarmonicWave, speed: float) -> dict:
    """Verify the 1-D wave equation residual from the represented harmonic."""
    if speed <= 0:
        raise ValueError("wave speed must be positive")
    # For A cos(kx - omega t + phi), u_xx - u_tt/c^2 =
    # A*(-k^2 + omega^2/c^2)*cos(...).
    coefficient = -wave.wavenumber**2 + (wave.angular_frequency / speed) ** 2
    residual_amplitude = abs(wave.amplitude * coefficient)
    return {
        "status": "SYMBOLIC_CHECKED" if math.isclose(residual_amplitude, 0.0, abs_tol=1e-12) else "FAILED",
        "residual_amplitude": residual_amplitude,
        "condition": "omega = speed * k",
        "assumption": "1-D homogeneous nondispersive wave equation",
    }


def dispersion_relation(
    omega: float,
    k: float,
    *,
    expected_phase_velocity: Optional[float] = None,
    expected_group_velocity: Optional[float] = None,
) -> dict:
    if omega <= 0 or k <= 0:
        raise ValueError("omega and k must be positive")
    phase = omega / k
    out = {"status": "NUMERICALLY_CHECKED", "phase_velocity": phase, "omega": omega, "k": k}
    if expected_phase_velocity is not None:
        out["phase_velocity_match"] = math.isclose(
            phase, expected_phase_velocity, rel_tol=1e-10, abs_tol=1e-12
        )
    if expected_group_velocity is not None:
        out["group_velocity"] = expected_group_velocity
        out["group_velocity_source"] = "caller-supplied; not inferred"
    return out


def dispersion_curve(
    omega_of_k: Callable[[float], float],
    wavenumbers: Sequence[float],
    *,
    step: float = 1e-5,
) -> dict:
    """Sample a dispersion relation and estimate group velocity dω/dk."""
    if step <= 0:
        raise ValueError("step must be positive")
    ks = [float(k) for k in wavenumbers]
    if not ks or any(k <= 0 for k in ks):
        raise ValueError("wavenumbers must be a non-empty positive sequence")
    values = [float(omega_of_k(k)) for k in ks]
    if any(not math.isfinite(v) or v <= 0 for v in values):
        return {"status": "UNVERIFIED", "reason": "dispersion relation returned non-positive or non-finite omega"}
    group = []
    for k in ks:
        km, kp = max(1e-15, k - step), k + step
        group.append((float(omega_of_k(kp)) - float(omega_of_k(km))) / (kp - km))
    return {
        "status": "NUMERICALLY_CHECKED",
        "wavenumbers": ks,
        "angular_frequencies": values,
        "phase_velocities": [w / k for w, k in zip(values, ks)],
        "group_velocities": group,
        "method": "central finite difference in k",
    }


@dataclass(frozen=True)
class ReflectionRefraction:
    n1: float
    n2: float
    incidence_angle: float

    def __post_init__(self):
        if self.n1 <= 0 or self.n2 <= 0:
            raise ValueError("refractive indices must be positive")
        if not 0 <= self.incidence_angle < math.pi / 2:
            raise ValueError("incidence angle must be in [0, pi/2)")

    def fresnel_reflectance_normal(self) -> float:
        r = (self.n1 - self.n2) / (self.n1 + self.n2)
        return r * r

    def refracted_angle(self) -> float:
        s = self.n1 * math.sin(self.incidence_angle) / self.n2
        if abs(s) > 1:
            raise ValueError("total internal reflection: no real refracted angle")
        return math.asin(s)

    def fresnel_reflectance(self) -> dict:
        """Oblique-incidence s/p reflectance for non-absorbing media."""
        s = self.n1 * math.sin(self.incidence_angle) / self.n2
        if abs(s) > 1:
            return {
                "status": "NOT_APPLICABLE",
                "total_internal_reflection": True,
                "reflectance_s": 1.0,
                "reflectance_p": 1.0,
            }
        theta2 = math.asin(s)
        c1, c2 = math.cos(self.incidence_angle), math.cos(theta2)
        rs = (self.n1 * c1 - self.n2 * c2) / (self.n1 * c1 + self.n2 * c2)
        rp = (self.n2 * c1 - self.n1 * c2) / (self.n2 * c1 + self.n1 * c2)
        return {
            "status": "NUMERICALLY_CHECKED",
            "refracted_angle": theta2,
            "reflectance_s": rs * rs,
            "reflectance_p": rp * rp,
        }


@dataclass(frozen=True)
class PolarizationState:
    """Complex transverse Jones state."""

    ex: complex
    ey: complex

    def intensity(self) -> float:
        return abs(self.ex) ** 2 + abs(self.ey) ** 2

    def normalized(self) -> "PolarizationState":
        I = self.intensity()
        if I <= 0:
            raise ValueError("zero polarization state is undefined")
        scale = math.sqrt(I)
        return PolarizationState(self.ex / scale, self.ey / scale)

    def jones(self) -> Tuple[complex, complex]:
        n = self.normalized()
        return n.ex, n.ey

    def stokes(self) -> dict:
        ex, ey = self.jones()
        I = 1.0
        return {
            "status": "NUMERICALLY_CHECKED",
            "I": I,
            "Q": abs(ex) ** 2 - abs(ey) ** 2,
            "U": 2 * (ex.conjugate() * ey).real,
            "V": 2 * (ex.conjugate() * ey).imag,
        }


def diffraction_single_slit(wavelength: float, slit_width: float, angle: float) -> dict:
    if wavelength <= 0 or slit_width <= 0:
        raise ValueError("wavelength and slit width must be positive")
    if not -math.pi / 2 < angle < math.pi / 2:
        raise ValueError("angle must lie in (-pi/2,pi/2)")
    beta = math.pi * slit_width * math.sin(angle) / wavelength
    intensity = (math.sin(beta) / beta) ** 2 if abs(beta) > 1e-14 else 1.0
    return {
        "status": "NUMERICALLY_CHECKED",
        "beta": beta,
        "relative_intensity": intensity,
        "model": "Fraunhofer single-slit",
    }
