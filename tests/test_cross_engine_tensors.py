"""
Cross-Engine Tensor Verification Tests.

These tests compare Automate's native TensorGeometry against EinsteinPy
as an independent oracle for multiple coordinate systems and metrics.

Independence Classification:
    DIFFERENT_ENGINE — Automate TensorGeometry vs EinsteinPy

Reference Values:
    - Flat metrics: all curvature identically zero (trivially known)
    - 2-sphere: Ricci scalar = 2/r² (e.g. MTW §8.6)
    - Polar 2D: Ricci scalar = 0, flat (trivially known)
    - 4D Schwarzschild: vacuum solution, R_μν = 0, G_μν = 0
      (Carroll, Spacetime and Geometry, §5.5)
"""

import pytest
import sympy as sp

from automate.tensors.algebra import TensorGeometry
from automate.tensors.einsteinpy_adapter import (
    cross_check_geometry,
    is_einsteinpy_available,
)

pytestmark = [
    pytest.mark.skipif(
        not is_einsteinpy_available(),
        reason="EinsteinPy not installed; cross-engine tests require it."
    ),
    pytest.mark.different_engine,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_cross_check(metric, coords, simplify=True):
    """Run TensorGeometry and cross-check everything against EinsteinPy."""
    tg = TensorGeometry(metric, coords, simplify=simplify)
    report = cross_check_geometry(
        metric=metric,
        coords=coords,
        native_christoffel=tg.christoffel_symbols(),
        native_ricci=tg.ricci_tensor(),
        native_ricci_scalar=tg.ricci_scalar(),
        native_einstein=tg.einstein_tensor(),
    )
    return tg, report


# ---------------------------------------------------------------------------
# A. Flat (Euclidean) 2D
# ---------------------------------------------------------------------------

class TestCrossCheckFlat2D:

    def test_flat_2d_all_match(self):
        x, y = sp.symbols("x y", real=True)
        g = sp.Matrix([[1, 0], [0, 1]])
        tg, rep = _full_cross_check(g, [x, y])

        assert rep["all_matched"] is True
        assert rep["independence_class"] == "DIFFERENT_ENGINE"
        assert len(rep["metric_fingerprint_sha256"]) == 64
        assert rep["comparison_method"] == "exact symbolic equality after SymPy simplification"
        assert rep["execution_status"] == "COMPLETED"
        assert rep["sandbox"]["bounded_process"] is True
        assert rep["reproducibility"]["engine"] == "EinsteinPy"
        assert rep["christoffel_matched"] is True
        assert rep["ricci_matched"] is True
        assert rep["ricci_scalar_matched"] is True
        assert rep["einstein_matched"] is True

    def test_flat_2d_ricci_scalar_zero(self):
        x, y = sp.symbols("x y", real=True)
        g = sp.Matrix([[1, 0], [0, 1]])
        tg = TensorGeometry(g, [x, y])
        assert tg.ricci_scalar() == 0


# ---------------------------------------------------------------------------
# B. Polar Coordinates 2D (flat space, curved coordinates)
# ---------------------------------------------------------------------------

class TestCrossCheckPolar2D:

    def test_polar_2d_all_match(self):
        r, theta = sp.symbols("r theta", positive=True)
        g = sp.Matrix([[1, 0], [0, r**2]])
        tg, rep = _full_cross_check(g, [r, theta])

        assert rep["all_matched"] is True
        assert rep["independence_class"] == "DIFFERENT_ENGINE"
        assert len(rep["discrepancies"]) == 0

    def test_polar_2d_ricci_scalar_zero(self):
        """Polar coords in flat space: R = 0."""
        r, theta = sp.symbols("r theta", positive=True)
        g = sp.Matrix([[1, 0], [0, r**2]])
        tg = TensorGeometry(g, [r, theta])
        assert sp.simplify(tg.ricci_scalar()) == 0


# ---------------------------------------------------------------------------
# C. 2-Sphere (curved space)
# ---------------------------------------------------------------------------

class TestCrossCheckSphere2D:

    def test_sphere_2d_all_match(self):
        theta, phi = sp.symbols("theta phi", real=True)
        r = sp.Symbol("r", positive=True)
        g = sp.Matrix([
            [r**2, 0],
            [0, r**2 * sp.sin(theta)**2]
        ])
        tg, rep = _full_cross_check(g, [theta, phi])

        assert rep["all_matched"] is True
        assert rep["independence_class"] == "DIFFERENT_ENGINE"

    @pytest.mark.textbook_reference
    def test_sphere_2d_ricci_scalar_independent(self):
        """2-sphere Ricci scalar = 2/r² (MTW §8.6, known analytic result)."""
        theta, phi = sp.symbols("theta phi", real=True)
        r = sp.Symbol("r", positive=True)
        g = sp.Matrix([
            [r**2, 0],
            [0, r**2 * sp.sin(theta)**2]
        ])
        tg = TensorGeometry(g, [theta, phi])
        R = tg.ricci_scalar()
        expected = 2 / r**2
        assert sp.simplify(R - expected) == 0, \
            f"Ricci scalar should be 2/r², got {R}"


# ---------------------------------------------------------------------------
# D. Full 4D Schwarzschild (vacuum GR solution)
# ---------------------------------------------------------------------------

class TestCrossCheckSchwarzschild4D:

    @pytest.fixture(autouse=True)
    def setup_schwarzschild(self):
        t, r, theta, phi = sp.symbols("t r theta phi", real=True)
        M = sp.Symbol("M", positive=True)
        f = 1 - 2 * M / r
        self.g = sp.Matrix([
            [-f, 0, 0, 0],
            [0, 1 / f, 0, 0],
            [0, 0, r**2, 0],
            [0, 0, 0, r**2 * sp.sin(theta)**2],
        ])
        self.coords = [t, r, theta, phi]
        self.tg = TensorGeometry(self.g, self.coords, simplify=False)

    def test_schwarzschild_christoffel_cross_check(self):
        rep = cross_check_geometry(
            metric=self.g,
            coords=self.coords,
            native_christoffel=self.tg.christoffel_symbols(),
        )
        assert rep["christoffel_matched"] is True, \
            f"Christoffel discrepancies: {rep.get('discrepancies')}"

    def test_schwarzschild_ricci_tensor_zero(self):
        """Schwarzschild is a vacuum solution: R_μν = 0."""
        ric = self.tg.ricci_tensor()
        for i in range(4):
            for j in range(4):
                assert sp.simplify(ric[i, j]) == 0, \
                    f"Ricci R_{{{i}{j}}} should be 0, got {ric[i, j]}"

    def test_schwarzschild_ricci_scalar_zero(self):
        """Schwarzschild vacuum: R = 0."""
        R = self.tg.ricci_scalar()
        assert sp.simplify(R) == 0, f"Ricci scalar should be 0, got {R}"

    def test_schwarzschild_einstein_tensor_zero(self):
        """Schwarzschild vacuum: G_μν = 0."""
        G = self.tg.einstein_tensor()
        for i in range(4):
            for j in range(4):
                assert sp.simplify(G[i, j]) == 0, \
                    f"Einstein G_{{{i}{j}}} should be 0, got {G[i, j]}"

    def test_schwarzschild_ricci_cross_check(self):
        rep = cross_check_geometry(
            metric=self.g,
            coords=self.coords,
            native_ricci=self.tg.ricci_tensor(),
            native_ricci_scalar=self.tg.ricci_scalar(),
        )
        assert rep["ricci_matched"] is True, \
            f"Ricci discrepancies: {rep.get('discrepancies')}"
        assert rep["ricci_scalar_matched"] is True

    def test_schwarzschild_full_cross_check(self):
        rep = cross_check_geometry(
            metric=self.g,
            coords=self.coords,
            native_christoffel=self.tg.christoffel_symbols(),
            native_ricci=self.tg.ricci_tensor(),
            native_ricci_scalar=self.tg.ricci_scalar(),
            native_einstein=self.tg.einstein_tensor(),
        )
        assert rep["all_matched"] is True, \
            f"Full cross-check failed. Discrepancies: {rep.get('discrepancies')}"
        assert rep["independence_class"] == "DIFFERENT_ENGINE"


# ---------------------------------------------------------------------------
# E. Minkowski 4D (flat spacetime)
# ---------------------------------------------------------------------------

class TestCrossCheckMinkowski4D:

    def test_minkowski_all_match(self):
        t, x, y, z = sp.symbols("t x y z", real=True)
        g = sp.Matrix([
            [-1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])
        tg, rep = _full_cross_check(g, [t, x, y, z])

        assert rep["all_matched"] is True
        assert rep["independence_class"] == "DIFFERENT_ENGINE"

    def test_minkowski_all_curvature_zero(self):
        t, x, y, z = sp.symbols("t x y z", real=True)
        g = sp.Matrix([
            [-1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])
        tg = TensorGeometry(g, [t, x, y, z])
        assert tg.ricci_scalar() == 0
        for i in range(4):
            for j in range(4):
                assert tg.einstein_tensor()[i, j] == 0


# ---------------------------------------------------------------------------
# F. Cylindrical Coordinates 3D (flat, curved coords)
# ---------------------------------------------------------------------------

class TestCrossCheckCylindrical3D:

    def test_cylindrical_all_match(self):
        rho, phi, z = sp.symbols("rho phi z", positive=True)
        g = sp.Matrix([
            [1, 0, 0],
            [0, rho**2, 0],
            [0, 0, 1],
        ])
        tg, rep = _full_cross_check(g, [rho, phi, z])

        assert rep["all_matched"] is True
        assert rep["independence_class"] == "DIFFERENT_ENGINE"

    def test_cylindrical_ricci_scalar_zero(self):
        rho, phi, z = sp.symbols("rho phi z", positive=True)
        g = sp.Matrix([
            [1, 0, 0],
            [0, rho**2, 0],
            [0, 0, 1],
        ])
        tg = TensorGeometry(g, [rho, phi, z])
        assert sp.simplify(tg.ricci_scalar()) == 0


def test_cross_check_exception_is_not_reported_as_independent_agreement(monkeypatch):
    import automate.tensors.einsteinpy_adapter as adapter

    x, y = sp.symbols("x y", real=True)
    metric = sp.Matrix([[1, 0], [0, 1]])

    class ExplodingMetricTensor:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("intentional cross-engine failure")

    monkeypatch.setattr(adapter, "MetricTensor", ExplodingMetricTensor)

    report = adapter._cross_check_geometry_core(
        metric=metric,
        coords=[x, y],
        native_ricci_scalar=sp.Integer(0),
    )

    assert report["available"] is True
    assert report["all_matched"] is None
    assert report["independence_class"] == "CROSS_CHECK_FAILED"
    assert len(report["metric_fingerprint_sha256"]) == 64
    assert report["comparison_method"] == "exact symbolic equality after SymPy simplification"
