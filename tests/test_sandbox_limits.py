"""Trust-boundary tests for the shared execution sandbox configuration."""

import pytest

from automate.core.sandbox import SandboxLimits


@pytest.mark.trust_boundary
@pytest.mark.adversarial
def test_sandbox_rejects_non_positive_limits():
    with pytest.raises(ValueError):
        SandboxLimits(wall_clock_seconds=0)
    with pytest.raises(ValueError):
        SandboxLimits(cpu_seconds=0)
    with pytest.raises(ValueError):
        SandboxLimits(memory_bytes=0)
    with pytest.raises(ValueError):
        SandboxLimits(max_input_bytes=0)
    with pytest.raises(ValueError):
        SandboxLimits(max_output_bytes=0)


@pytest.mark.trust_boundary
def test_sandbox_rejects_unbounded_wall_clock_and_cpu():
    with pytest.raises(ValueError):
        SandboxLimits(wall_clock_seconds=3600.1)
    with pytest.raises(ValueError):
        SandboxLimits(cpu_seconds=3600.1)


def test_sandbox_limits_round_trip_as_machine_readable_data():
    limits = SandboxLimits(
        wall_clock_seconds=7,
        cpu_seconds=5,
        memory_bytes=64 * 1024 * 1024,
        max_input_bytes=1024,
        max_output_bytes=2048,
    )
    assert limits.model_dump() == {
        "wall_clock_seconds": 7,
        "cpu_seconds": 5,
        "memory_bytes": 64 * 1024 * 1024,
        "max_input_bytes": 1024,
        "max_output_bytes": 2048,
    }
