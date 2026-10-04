"""
Shared execution sandbox for resource-bounded verification work.

The sandbox is deliberately backend-agnostic. It isolates a trusted, named
Python entrypoint in a spawned process and enforces the limits that can be
expressed at the process boundary. Mathematical correctness remains the
backend's job; this module only constrains execution.
"""

from __future__ import annotations

import importlib
import math
import multiprocessing
import os
import pickle
import time
from dataclasses import dataclass
from typing import Any, Dict

from pydantic import BaseModel


class SandboxError(RuntimeError):
    """Raised when an isolated verification task cannot complete safely."""


class SandboxLimits(BaseModel):
    wall_clock_seconds: float = 30.0
    cpu_seconds: float = 20.0
    memory_bytes: int = 1024 * 1024 * 1024
    max_input_bytes: int = 16 * 1024 * 1024
    max_output_bytes: int = 4 * 1024 * 1024

    def validate_limits(self) -> None:
        if not (0 < self.wall_clock_seconds <= 3600):
            raise ValueError("wall_clock_seconds must be in (0, 3600].")
        if not (0 < self.cpu_seconds <= 3600):
            raise ValueError("cpu_seconds must be in (0, 3600].")
        if self.memory_bytes <= 0:
            raise ValueError("memory_bytes must be positive.")
        if self.max_input_bytes <= 0:
            raise ValueError("max_input_bytes must be positive.")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive.")


@dataclass
class EvaluationBudget:
    """Explicit callback/evaluation budget for solver or fitter hot paths."""

    maximum: int
    used: int = 0

    def __post_init__(self) -> None:
        if self.maximum <= 0:
            raise ValueError("Evaluation budget must be positive.")

    def consume(self, amount: int = 1) -> None:
        if amount <= 0:
            raise ValueError("Evaluation amount must be positive.")
        self.used += amount
        if self.used > self.maximum:
            raise SandboxError(
                f"Evaluation budget exceeded: {self.maximum} calls allowed."
            )

    @property
    def remaining(self) -> int:
        return max(0, self.maximum - self.used)


def _apply_resource_limits(limits: SandboxLimits) -> None:
    """Apply best-effort POSIX resource limits inside the child process."""
    try:
        import resource
    except (ImportError, OSError):
        return

    try:
        cpu_limit = max(1, int(math.ceil(limits.cpu_seconds)))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
    except (AttributeError, OSError, ValueError):
        pass

    try:
        resource.setrlimit(
            resource.RLIMIT_AS,
            (limits.memory_bytes, limits.memory_bytes),
        )
    except (AttributeError, OSError, ValueError):
        pass


def _worker(send_conn: Any, target: str, payload_blob: bytes, limits_dict: Dict[str, Any]) -> None:
    limits = SandboxLimits(**limits_dict)
    _apply_resource_limits(limits)

    # Avoid accidental thread explosions in BLAS/OpenMP-backed scientific
    # libraries inside the constrained worker.
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ.setdefault(variable, "1")

    try:
        payload = pickle.loads(payload_blob)
        module_name, function_name = target.rsplit(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        result = function(payload)
        output_blob = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
        if len(output_blob) > limits.max_output_bytes:
            raise SandboxError(
                "Sandbox result exceeded output-size limit of "
                f"{limits.max_output_bytes} bytes."
            )
        send_conn.send(("ok", output_blob))
    except BaseException as exc:
        error_blob = pickle.dumps(
            f"{type(exc).__name__}: {exc}",
            protocol=pickle.HIGHEST_PROTOCOL,
        )
        if len(error_blob) > limits.max_output_bytes:
            error_blob = pickle.dumps(
                "Sandbox worker failed and the error payload exceeded its output limit.",
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        try:
            send_conn.send(("error", error_blob))
        except Exception:
            pass
    finally:
        send_conn.close()


class VerifiedExecutionSandbox:
    """Run a named verification entrypoint inside a bounded child process."""

    def __init__(self, limits: SandboxLimits | None = None):
        self.limits = limits or SandboxLimits()
        self.limits.validate_limits()

    def run(self, target: str, payload: Any) -> Any:
        if not isinstance(target, str) or ":" not in target:
            raise ValueError(
                "Sandbox target must be a fully-qualified entrypoint such as "
                "'automate.backend.numerical_backend:_run_numerical_verification'."
            )

        try:
            payload_blob = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as exc:
            raise SandboxError(
                f"Sandbox input could not be serialized: {type(exc).__name__}: {exc}"
            ) from exc

        if len(payload_blob) > self.limits.max_input_bytes:
            raise SandboxError(
                "Sandbox input exceeded input-size limit of "
                f"{self.limits.max_input_bytes} bytes."
            )

        ctx = multiprocessing.get_context("spawn")
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        process = ctx.Process(
            target=_worker,
            args=(send_conn, target, payload_blob, self.limits.model_dump()),
            daemon=True,
        )

        try:
            process.start()
        except Exception as exc:
            recv_conn.close()
            send_conn.close()
            raise SandboxError(
                f"Could not start sandbox worker: {type(exc).__name__}: {exc}"
            ) from exc

        send_conn.close()
        deadline = time.monotonic() + self.limits.wall_clock_seconds
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate(process)
                    raise SandboxError(
                        "Verification sandbox wall-clock limit exceeded: "
                        f"{self.limits.wall_clock_seconds}s."
                    )

                if recv_conn.poll(min(0.1, remaining)):
                    status, result_blob = recv_conn.recv()
                    if len(result_blob) > self.limits.max_output_bytes:
                        raise SandboxError(
                            "Sandbox worker output exceeded output-size limit of "
                            f"{self.limits.max_output_bytes} bytes."
                        )
                    result = pickle.loads(result_blob)
                    if status == "error":
                        raise SandboxError(str(result))
                    if status != "ok":
                        raise SandboxError(f"Sandbox returned unknown status '{status}'.")
                    return result

                if not process.is_alive():
                    raise SandboxError(
                        "Verification sandbox worker terminated before returning a result."
                    )
        except (EOFError, OSError) as exc:
            raise SandboxError(
                f"Verification sandbox communication failed: {type(exc).__name__}: {exc}"
            ) from exc
        finally:
            recv_conn.close()
            if process.is_alive():
                self._terminate(process)
            process.join(timeout=1.0)

    @staticmethod
    def _terminate(process: multiprocessing.Process) -> None:
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.0)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(timeout=1.0)
