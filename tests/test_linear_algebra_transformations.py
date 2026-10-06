"""Focused acceptance tests for isolated orthogonal/unitary matrix semantics."""

from automate.linear_algebra_transformations import (
    verify_matrix_property,
    verify_orthogonal_matrix,
    verify_unitary_matrix,
)


def test_exact_real_orthogonal_rotation():
    report = verify_orthogonal_matrix("Matrix([[0, -1], [1, 0]])")
    assert report.passed
    assert report.status == "SYMBOLIC_CHECKED"
    assert report.numpy_cross_check["available"] is True
    assert report.numpy_cross_check["independence_class"] == "DIFFERENT_ENGINE"


def test_exact_complex_unitary_matrix():
    report = verify_unitary_matrix(
        "Matrix([[1/sqrt(2), I/sqrt(2)], [I/sqrt(2), 1/sqrt(2)]])"
    )
    assert report.passed
    assert report.status == "SYMBOLIC_CHECKED"
    assert report.numpy_cross_check["passed"] is True


def test_real_orthogonal_reflective_matrix():
    report = verify_orthogonal_matrix(
        "Matrix([[1, 0, 0], [0, -1, 0], [0, 0, 1]])"
    )
    assert report.passed


def test_non_orthogonal_matrix_is_rejected():
    report = verify_orthogonal_matrix("Matrix([[1, 1], [0, 1]])")
    assert not report.passed
    assert report.status == "FAILED"


def test_non_unitary_complex_matrix_is_rejected():
    report = verify_unitary_matrix("Matrix([[1, I], [0, 1]])")
    assert not report.passed
    assert report.status == "FAILED"


def test_non_square_matrix_is_rejected():
    report = verify_orthogonal_matrix("Matrix([[1, 0, 0], [0, 1, 0]])")
    assert not report.passed
    assert report.status == "FAILED"


def test_complex_orthogonal_claim_fails_closed():
    report = verify_orthogonal_matrix("Matrix([[I, 0], [0, I]])")
    assert not report.passed
    assert report.status == "FAILED"


def test_symbolic_reality_boundary_is_unverified():
    report = verify_orthogonal_matrix("Matrix([[a, 0], [0, 1]])")
    assert not report.passed
    assert report.status == "UNVERIFIED"


def test_symbolic_unitary_boundary_is_unverified():
    report = verify_unitary_matrix("Matrix([[a, 0], [0, 1]])")
    assert not report.passed
    assert report.status == "UNVERIFIED"


def test_wrong_property_is_not_silently_accepted():
    try:
        verify_matrix_property("Matrix([[1, 0], [0, 1]])", "not-a-property")
    except ValueError as exc:
        assert "property" in str(exc)
    else:
        raise AssertionError("unsupported matrix property was silently accepted")
