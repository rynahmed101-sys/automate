"""Adversarial tests for isolated change-of-basis semantics."""
from automate.change_of_basis import coordinates_in_basis, verify_basis_matrix

def test_coordinates_in_nonstandard_basis():
    r=coordinates_in_basis("Matrix([[1, 1], [1, -1]])","Vector([3, 1])")
    assert r.status=="SYMBOLIC_CHECKED"; assert r.coordinates==("2","1"); assert r.reconstructed_vector==("3","1"); assert r.residual==("0","0"); assert r.numpy_cross_check["passed"]

def test_nontrivial_three_dimensional_basis():
    r=coordinates_in_basis("Matrix([[1, 0, 1], [0, 1, 1], [1, 1, 0]])","Vector([4, 5, 3])")
    assert r.status=="SYMBOLIC_CHECKED"; assert r.coordinates==("1","2","3")

def test_singular_basis_fails_closed():
    r=coordinates_in_basis("Matrix([[1, 2], [2, 4]])","Vector([3, 6])")
    assert r.status=="FAILED"; assert "singular" in (r.error or "").lower()

def test_symbolically_unresolved_basis_fails_closed():
    r=coordinates_in_basis("Matrix([[a, 0], [0, 1]])","Vector([1, 2])")
    assert r.status=="UNVERIFIED"

def test_dimension_mismatch_fails_closed():
    r=coordinates_in_basis("Matrix([[1, 0], [0, 1]])","Vector([1, 2, 3])")
    assert r.status=="FAILED"

def test_rectangular_basis_is_rejected():
    r=coordinates_in_basis("Matrix([[1, 0, 0], [0, 1, 0]])","Vector([1, 2])")
    assert r.status=="FAILED"

def test_verify_basis_distinguishes_independence():
    assert verify_basis_matrix("Matrix([[1, 0], [0, 2]])")["status"]=="SYMBOLIC_CHECKED"
    assert verify_basis_matrix("Matrix([[1, 1], [1, 1]])")["status"]=="FAILED"
    assert verify_basis_matrix("Matrix([[a, 0], [0, 1]])")["status"]=="UNVERIFIED"

def test_invalid_expression_fails_closed():
    assert coordinates_in_basis("Matrix([[1, 0], [0, 1]])","not_a_vector").status=="FAILED"
