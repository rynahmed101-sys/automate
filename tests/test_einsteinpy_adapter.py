"""Adversarial tests for independent EinsteinPy comparison classification."""

import sympy as sp

import automate.tensors.einsteinpy_adapter as adapter


def test_external_engine_failure_is_not_classified_as_mathematical_discrepancy(monkeypatch):
    class FailingSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            raise adapter.SandboxError("worker crashed")

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FailingSandbox)
    metric = sp.Matrix([[1, 0], [0, 1]])
    coords = list(sp.symbols("x y"))

    report = adapter.cross_check_geometry(
        metric=metric,
        coords=coords,
        native_ricci=sp.zeros(2),
    )

    assert report["execution_status"] == "FAILED"
    assert report["all_matched"] is None
    assert report["independence_class"] == "CROSS_CHECK_FAILED"
    assert report["discrepancies"] == []


def test_einsteinpy_runtime_provenance_is_explicit():
    assert adapter.get_einsteinpy_version()
    assert adapter.get_einsteinpy_version() == "0.4.0" or not adapter.is_einsteinpy_available()


def test_einsteinpy_runtime_provenance_fingerprint_is_stable():
    first = adapter._runtime_environment_fingerprint()
    second = adapter._runtime_environment_fingerprint()
    assert len(first) == 64
    assert first == second
