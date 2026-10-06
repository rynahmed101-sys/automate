from pathlib import Path

from automate.dev.learning import LearningStore
from automate.dev.learning_events import (
    record_ci_result,
    record_reconciliation_result,
    record_verification_result,
)


def test_ci_failure_becomes_structured_learning_experience(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        eid = record_ci_result(
            store,
            action_cycle_id="ci-cycle-1",
            task_target="pr-135",
            strategy_id="test-strategy",
            conclusion="failure",
            run_id=1234,
            details="assertion failed in supervisor test",
        )
        exp = store.get_experience(eid)
        assert exp is not None
        assert exp["outcome"] == "failure"
        assert exp["failure_class"] == "test_defect"
    finally:
        store.close()


def test_reconciliation_stale_revision_is_learned(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        eid = record_reconciliation_result(
            store,
            action_cycle_id="reconcile-1",
            task_target="stage1b.improper_integrals",
            strategy_id="reconcile",
            findings=[{
                "kind": "stale_revision",
                "detail": "requested abc, live def",
            }],
            ready=False,
            revision="a" * 40,
        )
        exp = store.get_experience(eid)
        assert exp["failure_class"] == "stale_revision"
    finally:
        store.close()


def test_contradiction_remains_distinct_from_failure(tmp_path: Path):
    store = LearningStore(tmp_path / "learning.db")
    try:
        eid = record_verification_result(
            store,
            action_cycle_id="verification-1",
            task_target="candidate.physics",
            strategy_id="mirror-check",
            evidence_state="CONTRADICTED",
            evidence_refs=[{"id": "mirror-run", "kind": "mirror"}],
        )
        exp = store.get_experience(eid)
        assert exp["outcome"] == "contradiction"
        assert exp["failure_class"] == "genuine_contradiction"
    finally:
        store.close()
