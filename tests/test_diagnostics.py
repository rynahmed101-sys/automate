from automate.dev.diagnostics import diagnose_failure


def test_diagnosis_preserves_competing_failure_hypotheses():
    result = diagnose_failure(
        message="test expected output differs after backend precision/truncation change",
        evidence_kinds=["test", "backend", "truncation", "precision"],
    )
    assert len(result) >= 2
    assert result[0]["failure_class"] in {
        "backend_mismatch",
        "numerical_precision_problem",
        "test_defect",
        "truncation_discretization_problem",
    }
