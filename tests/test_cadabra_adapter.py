"""Adversarial and provenance tests for the bounded Cadabra adapter."""

import pytest

from automate.core.sandbox import SandboxLimits
import automate.tensors.cadabra_adapter as adapter


def test_unavailable_cadabra_is_explicit(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: None)
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "Not Installed")

    report = adapter.run_cadabra_script("\\simplify;")

    assert report["execution_status"] == "UNAVAILABLE"
    assert report["independence_class"] == "NOT_RUN"
    assert len(report["input_fingerprint_sha256"]) == 64


@pytest.mark.adversarial
@pytest.mark.trust_boundary
def test_unsupported_external_control_is_not_executed(monkeypatch):
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("unsupported Cadabra source reached execution")

    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "test")
    monkeypatch.setattr(adapter.VerifiedExecutionSandbox, "run", fail_if_called)

    report = adapter.run_cadabra_script("@import evil.cdb")

    assert report["execution_status"] == "UNSUPPORTED"
    assert report["independence_class"] == "UNVERIFIED"
    assert called is False


def test_success_without_expected_output_remains_unverified(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "result",
                "stderr": "",
                "output_fingerprint_sha256": "a" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)

    report = adapter.run_cadabra_script("\\simplify;", sandbox_limits=SandboxLimits())

    assert report["execution_status"] == "COMPLETED"
    assert report["independence_class"] == "UNVERIFIED"


def test_matching_output_is_different_engine_evidence(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "R_{a b} = R_{a b}",
                "stderr": "",
                "output_fingerprint_sha256": "b" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)

    report = adapter.run_cadabra_script(
        "\\simplify;",
        expected_output="R_{a b} = R_{a b}",
    )

    assert report["execution_status"] == "COMPLETED"
    assert report["independence_class"] == "UNVERIFIED"
    assert report["comparison_target_source"] == "caller_supplied"
    assert report["comparison_target_fingerprint_sha256"]
    assert report["checks_performed"] == 1
    assert report["claim_fingerprint_sha256"] is None
    assert "not independent evidence" in report["notes"][0]


def test_mismatching_output_is_discrepancy_not_proof_of_falsity(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "wrong",
                "stderr": "",
                "output_fingerprint_sha256": "c" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)

    report = adapter.run_cadabra_script(
        "\\simplify;",
        expected_output="right",
    )

    assert report["execution_status"] == "MATHEMATICAL_DISCREPANCY"
    assert report["independence_class"] == "CROSS_CHECK_FAILED"
    assert report["claim_fingerprint_sha256"] is None


def test_claim_fingerprint_survives_completed_comparison(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits
        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "same",
                "stderr": "",
                "output_fingerprint_sha256": "9" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)
    fingerprint = "a" * 64
    report = adapter.run_cadabra_script("ex := A;", expected_output="same", claim_fingerprint_sha256=fingerprint)
    assert report["independence_class"] == "UNVERIFIED"
    assert report["comparison_target_source"] == "caller_supplied"
    assert report["claim_fingerprint_sha256"] == fingerprint


def test_sandbox_limits_are_recorded(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            assert payload["max_output_bytes"] == limits.max_output_bytes
            return {
                "execution_status": "COMPLETED",
                "stdout": "x",
                "stderr": "",
                "output_fingerprint_sha256": "d" * 64,
            }

    limits = SandboxLimits(max_output_bytes=12345)
    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)

    report = adapter.run_cadabra_script("x;", sandbox_limits=limits)

    assert report["sandbox_limits"]["max_output_bytes"] == 12345


def test_translated_ir_binds_claim_fingerprint(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "ok",
                "stderr": "",
                "output_fingerprint_sha256": "e" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)

    fingerprint = "f" * 64
    report = adapter.run_translated_cadabra({
        "source": "ex := A_{a};",
        "ir_fingerprint_sha256": fingerprint,
    })

    assert report["execution_status"] == "COMPLETED"
    assert report["independence_class"] == "UNVERIFIED"
    assert report["claim_fingerprint_sha256"] == fingerprint


@pytest.mark.adversarial
@pytest.mark.trust_boundary
def test_translated_ir_rejects_missing_or_malformed_fingerprint(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    with pytest.raises(ValueError, match="valid 64-character hexadecimal IR fingerprint"):
        adapter.run_translated_cadabra({"source": "ex := A_{a};", "ir_fingerprint_sha256": "bad"})
    with pytest.raises(ValueError, match="valid 64-character hexadecimal IR fingerprint"):
        adapter.run_translated_cadabra({
            "source": "ex := A_{a};",
            "ir_fingerprint_sha256": "g" * 64,
        })


def test_translated_ir_rejects_empty_source():
    with pytest.raises(ValueError, match="non-empty source"):
        adapter.run_translated_cadabra({
            "source": "",
            "ir_fingerprint_sha256": "f" * 64,
        })


def test_cadabra_provenance_binds_resolved_executable(monkeypatch, tmp_path):
    executable = tmp_path / "cadabra2"
    executable.write_bytes(b"cadabra-test-runtime")
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: str(executable))
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "same",
                "stderr": "",
                "output_fingerprint_sha256": "a" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)
    report = adapter.run_cadabra_script("ex := A;", expected_output="same")

    assert report["runtime_identity"] == "resolved-executable-sha256"
    assert report["executable_path"] == str(executable.resolve())
    assert len(report["executable_fingerprint_sha256"]) == 64
    assert report["adapter_version"] == "v2"
    assert report["provenance_schema_version"] == "v2"
    assert len(report["runtime_environment_fingerprint_sha256"]) == 64
    assert report["runtime_dependency_versions"]
    assert len(report["provenance_fingerprint_sha256"]) == 64


@pytest.mark.adversarial
@pytest.mark.trust_boundary
def test_cadabra_provenance_changes_when_executable_changes(monkeypatch, tmp_path):
    executable = tmp_path / "cadabra2"
    executable.write_bytes(b"runtime-one")
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: str(executable))
    first = adapter._executable_provenance(str(executable))[1]

    executable.write_bytes(b"runtime-two")
    second = adapter._executable_provenance(str(executable))[1]

    assert first != second


def test_external_evidence_rejects_non_hex_fingerprints():
    from automate.core.external_engine import ExternalEngineEvidence

    with pytest.raises(ValueError, match="64-character hexadecimal SHA-256"):
        ExternalEngineEvidence(
            engine="test",
            version="1",
            execution_status="COMPLETED",
            independence_class="UNVERIFIED",
            input_fingerprint_sha256="g" * 64,
            comparison_method="test",
            sandbox_target="test:entry",
        )


@pytest.mark.trust_boundary
def test_cadabra_failure_still_records_runtime_provenance(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FailingSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            raise adapter.SandboxError("worker crashed")

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FailingSandbox)
    report = adapter.run_cadabra_script("ex := A;")

    assert report["execution_status"] == "EXECUTION_FAILED"
    assert report["runtime_identity"] == "resolved-path-only"
    assert report["executable_path"] == "/usr/bin/cadabra2"
    assert report["runtime_environment_fingerprint_sha256"]


@pytest.mark.trust_boundary
def test_cadabra_process_failure_preserves_runtime_provenance(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FailingSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "EXECUTION_FAILED",
                "error": "process exited 7",
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FailingSandbox)
    report = adapter.run_cadabra_script("ex := A;")

    assert report["execution_status"] == "EXECUTION_FAILED"
    assert report["runtime_identity"] == "resolved-path-only"
    assert report["executable_path"] == "/usr/bin/cadabra2"
    assert report["runtime_environment_fingerprint_sha256"]
    assert report["error"] == "process exited 7"


@pytest.mark.adversarial
@pytest.mark.trust_boundary
def test_caller_supplied_target_cannot_be_classified_as_independent(monkeypatch):
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: "/usr/bin/cadabra2")
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "trusted-looking answer",
                "stderr": "",
                "output_fingerprint_sha256": "1" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)
    report = adapter.run_cadabra_script(
        "ex := A;",
        expected_output="trusted-looking answer",
    )

    assert report["execution_status"] == "COMPLETED"
    assert report["independence_class"] == "UNVERIFIED"
    assert report["comparison_target_source"] == "caller_supplied"
    assert report["comparison_target_fingerprint_sha256"]


@pytest.mark.trust_boundary
def test_provenance_fingerprint_changes_with_executable(monkeypatch, tmp_path):
    executable = tmp_path / "cadabra2"
    executable.write_bytes(b"runtime-one")
    monkeypatch.setattr(adapter, "find_cadabra_executable", lambda: str(executable))
    monkeypatch.setattr(adapter, "get_cadabra_version", lambda: "2.test")

    class FakeSandbox:
        def __init__(self, limits):
            self.limits = limits

        def run(self, target, payload):
            return {
                "execution_status": "COMPLETED",
                "stdout": "same",
                "stderr": "",
                "output_fingerprint_sha256": "2" * 64,
            }

    monkeypatch.setattr(adapter, "VerifiedExecutionSandbox", FakeSandbox)
    first = adapter.run_cadabra_script("ex := A;")
    executable.write_bytes(b"runtime-two")
    second = adapter.run_cadabra_script("ex := A;")

    assert first["provenance_fingerprint_sha256"] != second["provenance_fingerprint_sha256"]
    assert first["executable_fingerprint_sha256"] != second["executable_fingerprint_sha256"]
