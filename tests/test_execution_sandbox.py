"""Tests for the shared verification execution sandbox."""

import time

import pytest

from automate.core.sandbox import (
    EvaluationBudget,
    SandboxError,
    SandboxLimits,
    VerifiedExecutionSandbox,
)


def _return_payload(payload):
    return payload


def _sleep_forever(payload):
    time.sleep(float(payload.get("seconds", 10)))
    return {"done": True}


def test_sandbox_roundtrip_and_input_output_limits():
    limits = SandboxLimits(
        wall_clock_seconds=5,
        cpu_seconds=5,
        memory_bytes=512 * 1024 * 1024,
        max_input_bytes=1024,
        max_output_bytes=1024,
    )
    result = VerifiedExecutionSandbox(limits).run(
        "tests.test_execution_sandbox:_return_payload",
        {"claim": "novel", "value": 42},
    )
    assert result["value"] == 42

    with pytest.raises(SandboxError, match="input-size limit"):
        VerifiedExecutionSandbox(
            limits.model_copy(update={"max_input_bytes": 16})
        ).run(
            "tests.test_execution_sandbox:_return_payload",
            {"large": "x" * 1024},
        )


def test_sandbox_enforces_parent_wall_clock_limit():
    limits = SandboxLimits(
        wall_clock_seconds=0.5,
        cpu_seconds=5,
        memory_bytes=512 * 1024 * 1024,
        max_input_bytes=1024,
        max_output_bytes=1024,
    )
    with pytest.raises(SandboxError, match="wall-clock"):
        VerifiedExecutionSandbox(limits).run(
            "tests.test_execution_sandbox:_sleep_forever",
            {"seconds": 5},
        )


def test_evaluation_budget_is_hard_and_reportable():
    budget = EvaluationBudget(3)
    budget.consume()
    budget.consume(2)
    assert budget.used == 3
    assert budget.remaining == 0
    with pytest.raises(SandboxError, match="Evaluation budget exceeded"):
        budget.consume()


def test_limits_reject_invalid_values():
    with pytest.raises(ValueError):
        SandboxLimits(wall_clock_seconds=0)
    with pytest.raises(ValueError):
        SandboxLimits(cpu_seconds=0)
    with pytest.raises(ValueError):
        SandboxLimits(memory_bytes=0)
