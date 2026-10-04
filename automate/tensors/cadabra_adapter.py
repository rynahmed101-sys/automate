"""Bounded Cadabra2 external-engine adapter.

Cadabra is treated strictly as an external oracle. This module does not vendor
Cadabra or import its Python runtime. Execution failures never become
mathematical contradictions.

The initial boundary is deliberately narrow: explicitly supplied Cadabra source,
optional exact expected stdout, no shell interpolation, bounded execution, and
deterministic fingerprints. Without a comparison target, successful execution
is evidence gathering only and remains UNVERIFIED.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional

from automate.core.external_engine import ExternalEngineEvidence
from automate.core.sandbox import SandboxError, SandboxLimits, VerifiedExecutionSandbox

_CADABRA_BINARY_NAMES = ("cadabra2", "cadabra2-cli")
_CADABRA_VERSION_TIMEOUT = 5.0
_SUPPORTED_SCRIPT_MAX_BYTES = 512 * 1024
_TARGET = "automate.tensors.cadabra_adapter:_run_cadabra_cli"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def find_cadabra_executable() -> Optional[str]:
    """Return a Cadabra executable found on PATH, without invoking a shell."""
    for name in _CADABRA_BINARY_NAMES:
        executable = shutil.which(name)
        if executable:
            return executable
    return None


def is_cadabra_available() -> bool:
    return find_cadabra_executable() is not None


def get_cadabra_version() -> str:
    """Return a bounded version probe result, or Not Installed."""
    executable = find_cadabra_executable()
    if executable is None:
        return "Not Installed"

    try:
        result = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=_CADABRA_VERSION_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"Unavailable: {type(exc).__name__}"

    output = (result.stdout or "").strip()
    if not output:
        return f"Unknown (exit {result.returncode})"
    return output[:512]


def _validate_supported_script(source: str) -> None:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Cadabra source must be a non-empty string.")

    size = len(source.encode("utf-8"))
    if size > _SUPPORTED_SCRIPT_MAX_BYTES:
        raise ValueError(
            "Cadabra source exceeds the supported input limit of "
            f"{_SUPPORTED_SCRIPT_MAX_BYTES} bytes."
        )

    # Do not expose Cadabra's external-control/file-loading constructs through
    # this adapter. The initial boundary accepts source text only.
    forbidden = ("@import", "@include", "system(", "exec(")
    lowered = source.lower()
    for token in forbidden:
        if token in lowered:
            raise ValueError(
                f"Cadabra source uses unsupported external-control construct: {token}"
            )


def _run_cadabra_cli(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn-safe worker that executes Cadabra without a shell."""
    executable = payload["executable"]
    source = payload["source"]
    max_output_bytes = int(payload["max_output_bytes"])
    timeout = float(payload["wall_clock_seconds"])

    with tempfile.TemporaryDirectory(prefix="automate-cadabra-") as directory:
        source_path = os.path.join(directory, "input.cdb")
        stdout_path = os.path.join(directory, "stdout.txt")
        stderr_path = os.path.join(directory, "stderr.txt")

        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(source)

        try:
            with open(stdout_path, "wb") as stdout_handle, open(
                stderr_path, "wb"
            ) as stderr_handle:
                process = subprocess.Popen(
                    [executable, source_path],
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    shell=False,
                )
                deadline = time.monotonic() + timeout
                return_code = None
                while return_code is None:
                    if __import__("time").monotonic() >= deadline:
                        process.kill()
                        process.wait(timeout=1.0)
                        return {
                            "execution_status": "EXECUTION_FAILED",
                            "error": "Cadabra process exceeded the sandbox wall-clock limit.",
                        }

                    current_output = (
                        os.path.getsize(stdout_path) + os.path.getsize(stderr_path)
                    )
                    if current_output > max_output_bytes:
                        process.kill()
                        process.wait(timeout=1.0)
                        return {
                            "execution_status": "EXECUTION_FAILED",
                            "error": (
                                "Cadabra output exceeded the sandbox output-size "
                                f"limit of {max_output_bytes} bytes."
                            ),
                        }

                    return_code = process.poll()
                    if return_code is None:
                        time.sleep(0.02)
        except OSError as exc:
            return {
                "execution_status": "EXECUTION_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }

        stdout_size = os.path.getsize(stdout_path)
        stderr_size = os.path.getsize(stderr_path)
        if stdout_size + stderr_size > max_output_bytes:
            return {
                "execution_status": "EXECUTION_FAILED",
                "error": (
                    "Cadabra output exceeded the sandbox output-size limit of "
                    f"{max_output_bytes} bytes."
                ),
            }

        with open(stdout_path, "rb") as handle:
            stdout = handle.read().decode("utf-8", errors="replace")
        with open(stderr_path, "rb") as handle:
            stderr = handle.read().decode("utf-8", errors="replace")

    return {
        "execution_status": "COMPLETED" if return_code == 0 else "EXECUTION_FAILED",
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
        "output_fingerprint_sha256": hashlib.sha256(
            (stdout + "\n" + stderr).encode("utf-8")
        ).hexdigest(),
        "error": None if return_code == 0 else f"Cadabra exited with status {return_code}.",
    }

def run_translated_cadabra(
    translation: Dict[str, Any],
    *,
    expected_output: Optional[str] = None,
    sandbox_limits: Optional[SandboxLimits] = None,
) -> Dict[str, Any]:
    """Execute deterministic translator output while binding evidence to its IR fingerprint."""
    if not isinstance(translation, dict):
        raise TypeError("translation must be a dictionary returned by a Cadabra translator.")
    source = translation.get("source")
    fingerprint = translation.get("ir_fingerprint_sha256")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("translation must contain non-empty source.")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("translation must contain a valid 64-character IR fingerprint.")
    return run_cadabra_script(
        source,
        expected_output=expected_output,
        sandbox_limits=sandbox_limits,
        claim_fingerprint_sha256=fingerprint,
    )


def run_cadabra_script(
    source: str,
    *,
    expected_output: Optional[str] = None,
    sandbox_limits: Optional[SandboxLimits] = None,
    claim_fingerprint_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a supported Cadabra script and return auditable evidence."""
    input_fingerprint = _sha256_text(source)
    version = get_cadabra_version()
    executable = find_cadabra_executable()
    limits = sandbox_limits or SandboxLimits()
    comparison_method = "exact stdout comparison when expected_output is supplied"

    try:
        _validate_supported_script(source)
    except ValueError as exc:
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version, execution_status="UNSUPPORTED",
            independence_class="UNVERIFIED", input_fingerprint_sha256=input_fingerprint,
            claim_fingerprint_sha256=claim_fingerprint_sha256,
            comparison_method=comparison_method, sandbox_target=_TARGET,
            sandbox_limits=limits.model_dump(), error=str(exc),
            notes=["Only bounded source execution is supported."],
        ).to_report()

    if executable is None:
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version, execution_status="UNAVAILABLE",
            independence_class="NOT_RUN", input_fingerprint_sha256=input_fingerprint,
            comparison_method=comparison_method, sandbox_target=_TARGET,
            sandbox_limits=limits.model_dump(),
            notes=["Cadabra2 is not installed on the execution host."],
        ).to_report()

    payload = {
        "executable": executable,
        "source": source,
        "max_output_bytes": limits.max_output_bytes,
        "wall_clock_seconds": limits.wall_clock_seconds,
    }

    try:
        result = VerifiedExecutionSandbox(limits).run(_TARGET, payload)
    except SandboxError as exc:
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version, execution_status="EXECUTION_FAILED",
            independence_class="CROSS_CHECK_FAILED",
            input_fingerprint_sha256=input_fingerprint,
            comparison_method=comparison_method, sandbox_target=_TARGET,
            sandbox_limits=limits.model_dump(),
            error=f"{type(exc).__name__}: {exc}",
        ).to_report()

    if result["execution_status"] != "COMPLETED":
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version, execution_status="EXECUTION_FAILED",
            independence_class="CROSS_CHECK_FAILED",
            input_fingerprint_sha256=input_fingerprint,
            claim_fingerprint_sha256=claim_fingerprint_sha256,
            output_fingerprint_sha256=result.get("output_fingerprint_sha256"),
            comparison_method=comparison_method, sandbox_target=_TARGET,
            sandbox_limits=limits.model_dump(),
            error=result.get("error") or result.get("stderr"),
        ).to_report()

    stdout = result.get("stdout", "")
    if expected_output is None:
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version, execution_status="COMPLETED",
            independence_class="UNVERIFIED",
            input_fingerprint_sha256=input_fingerprint,
            claim_fingerprint_sha256=claim_fingerprint_sha256,
            output_fingerprint_sha256=result.get("output_fingerprint_sha256"),
            comparison_method="no comparison target supplied", sandbox_target=_TARGET,
            sandbox_limits=limits.model_dump(),
            notes=["Execution alone is not mathematical verification."],
        ).to_report()

    if stdout.strip() != expected_output.strip():
        return ExternalEngineEvidence(
            engine="Cadabra2", version=version,
            execution_status="MATHEMATICAL_DISCREPANCY",
            independence_class="CROSS_CHECK_FAILED",
            input_fingerprint_sha256=input_fingerprint,
            claim_fingerprint_sha256=claim_fingerprint_sha256,
            output_fingerprint_sha256=result.get("output_fingerprint_sha256"),
            comparison_method="exact normalized stdout equality",
            sandbox_target=_TARGET, sandbox_limits=limits.model_dump(),
            checks_performed=1,
            error="Cadabra output did not match the supplied comparison target.",
        ).to_report()

    return ExternalEngineEvidence(
        engine="Cadabra2", version=version, execution_status="COMPLETED",
        independence_class="DIFFERENT_ENGINE",
        input_fingerprint_sha256=input_fingerprint,
        claim_fingerprint_sha256=claim_fingerprint_sha256,
        output_fingerprint_sha256=result.get("output_fingerprint_sha256"),
        comparison_method="exact normalized stdout equality",
        sandbox_target=_TARGET, sandbox_limits=limits.model_dump(),
        checks_performed=1,
        notes=["Agreement is independent computational evidence, not formal proof."],
    ).to_report()
