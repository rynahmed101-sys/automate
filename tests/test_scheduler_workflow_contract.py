from pathlib import Path


def test_canonical_scheduler_requires_readiness_before_execution():
    workflow = Path(".github/workflows/control-cycle.yml").read_text(encoding="utf-8")
    execution_marker = "Run exactly one bounded control cycle"
    start = workflow.index(execution_marker)
    tail = workflow[start:]
    assert "steps.readiness.outputs.eligible == 'true'" in tail
    assert "fetch-depth: 0" in workflow.split("Checkout authoritative main scheduler", 1)[1].split("id: pin", 1)[0]


def test_canonical_scheduler_has_single_clock():
    workflows = [p.name for p in Path(".github/workflows").glob("*.yml")]
    assert workflows.count("control-cycle.yml") == 1
    assert "autonomous-cycle.yml" not in workflows
