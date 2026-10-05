"""
Structured Local Rule Registry for Automate.
Exposes rich metadata, required assumptions, side conditions, verification backends,
and automatic verification obligation generation across transformation steps.

Each rule declares:
  allowed_checkers: the set of checkers semantically valid for this rule.
  A proposal using a checker NOT in allowed_checkers will be rejected.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleDefinition(BaseModel):
    """
    Formal transformation rule definition.
    """
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    category: str = Field(
        default="algebra",
        description="Category: algebra, calculus, tensors, variational, differential_equations, numerics, statistics"
    )
    description: str = Field(..., description="Mathematical explanation or citation")
    domain: str = Field(default="general_physics")
    inputs: List[str] = Field(default_factory=list, description="Expected input types/roles")
    outputs: List[str] = Field(default_factory=list, description="Expected output types/roles")
    required_assumptions: List[str] = Field(default_factory=list)
    side_conditions: List[str] = Field(default_factory=list, description="Prerequisite physical conditions")
    default_obligations: List[Dict[str, Any]] = Field(default_factory=list)
    reversible: bool = Field(default=False)
    implementation_backend: str = Field(default="sympy")
    formal_proof_available: bool = Field(default=False)
    symbolic_checker_available: bool = Field(default=True)
    citation: Optional[str] = None

    # Machine-readable checker capabilities.
    # A proposal using a checker NOT in this list will be rejected at the
    # validation stage. An empty list means NO checker is valid (UNSUPPORTED).
    # "dimension" is always auxiliary and never counts as semantic verification.
    allowed_checkers: List[str] = Field(
        default_factory=list,
        description="Checkers that are semantically valid for this rule."
    )

    def generate_obligations(self, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Synthesizes concrete verification obligations given step parameters.
        """
        obligations = list(self.default_obligations)
        params = parameters or {}
        if self.rule_id == "divide_both_sides":
            divisor = params.get("divisor", "x")
            obligations.append({
                "type": "non_zero_constraint",
                "claim": f"{divisor} != 0",
                "description": f"Division requires non-zero denominator '{divisor}'"
            })
        elif self.rule_id == "index_contract":
            pair = params.get("index_pair", ("mu", "mu"))
            obligations.append({
                "type": "index_contraction_legality",
                "claim": f"valid_contraction({pair[0]}, {pair[1]})",
                "description": f"Einstein contraction requires one contravariant and one covariant index on '{pair[0]}'"
            })
        elif self.rule_id == "differentiate_both_sides":
            var = params.get("wrt", "t")
            obligations.append({
                "type": "smoothness_constraint",
                "claim": f"differentiable_wrt({var})",
                "description": f"Differentiating both sides requires target expression to be differentiable wrt '{var}'"
            })
        elif self.rule_id in ("vary_action",):
            field = params.get("field", "phi")
            obligations.append({
                "type": "stationary_action_principle",
                "claim": f"delta_S / delta_{field} == 0",
                "description": "Euler-Lagrange field equation derived from stationary action variation"
            })
        return obligations


class RuleRegistry:
    """
    Central registry of approved and verified transformation rules.
    """
    def __init__(self):
        self._rules: Dict[str, RuleDefinition] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        # 1. Variational Action Rules
        self.register(RuleDefinition(
            rule_id="euler_lagrange",
            name="Euler-Lagrange Equation",
            category="variational",
            description="Derives equations of motion from action principle: d/dt(dL/dq_dot) - dL/dq = 0",
            domain="classical_mechanics",
            inputs=["Lagrangian"],
            outputs=["Equation of Motion"],
            required_assumptions=["smooth_trajectories", "fixed_endpoints"],
            side_conditions=["asm_smooth_trajectory", "asm_conservative"],
            default_obligations=[{
                "type": "stationary_action",
                "claim": "d/dt(dL/dv) - dL/dx == 0",
                "description": "Hamilton's principle stationary action condition"
            }],
            implementation_backend="sympy",
            formal_proof_available=True,
            symbolic_checker_available=True,
            allowed_checkers=["sympy", "numerical", "lean4"],
            citation="Hamilton's Principle / Calculus of Variations"
        ))

        self.register(RuleDefinition(
            rule_id="vary_action",
            name="Functional Variation of Action",
            category="variational",
            description="Varies action functional with respect to dynamical field: delta S / delta phi = 0",
            domain="field_theory",
            inputs=["Action"],
            outputs=["Field Equation"],
            required_assumptions=["vanishing_boundary_variations"],
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy"],
        ))

        # 2. Conservation Laws
        self.register(RuleDefinition(
            rule_id="conserve_energy",
            name="Noether Energy Conservation",
            category="conservation",
            description=(
                "Derives Jacobi energy function E = sum(p_i * q_dot_i) - L "
                "and verifies dE/dt = 0 on-shell via equations of motion."
            ),
            domain="classical_mechanics",
            inputs=["Lagrangian", "Equation of Motion"],
            outputs=["Conserved Energy"],
            required_assumptions=["time_translation_invariance"],
            side_conditions=["asm_pos_mass", "asm_conservative"],
            default_obligations=[{
                "type": "on_shell_invariance",
                "claim": "dE/dt = 0 along solutions of the equations of motion",
                "description": "Total energy derivative vanishes along equations of motion"
            }],
            implementation_backend="lean4",
            formal_proof_available=True,
            symbolic_checker_available=True,
            allowed_checkers=["sympy", "numerical", "lean4"],
            citation="Noether's Theorem"
        ))

        # 3. Algebraic Rules
        self.register(RuleDefinition(
            rule_id="divide_both_sides",
            name="Divide Both Sides",
            category="algebra",
            description="Divides both sides of an equation by a non-zero algebraic term",
            domain="mathematics",
            reversible=True,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy"],
        ))

        self.register(RuleDefinition(
            rule_id="differentiate_both_sides",
            name="Differentiate Both Sides",
            category="calculus",
            description="Differentiates both sides of an equality with respect to an independent variable",
            domain="mathematics",
            reversible=False,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy"],
        ))

        self.register(RuleDefinition(
            rule_id="substitute",
            name="Substitute Expression",
            category="algebra",
            description="Replaces a symbol or sub-expression with an equivalent known equality",
            domain="mathematics",
            reversible=True,
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy"],
        ))

        self.register(RuleDefinition(
            rule_id="simplify",
            name="Algebraic Simplification",
            category="algebra",
            description="Simplifies an algebraic expression into canonical minimal form",
            domain="mathematics",
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy"],
        ))

        # 4. Tensor & Differential Geometry Rules
        self.register(RuleDefinition(
            rule_id="christoffel_symbols",
            name="Christoffel Symbols of Second Kind",
            category="tensors",
            description="Derives metric connection coefficients Γ^σ_{μν} from metric tensor g_{μν}",
            domain="differential_geometry",
            inputs=["Metric"],
            outputs=["Christoffel Symbols"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
            citation="Riemannian Geometry Connection"
        ))

        self.register(RuleDefinition(
            rule_id="riemann_curvature",
            name="Riemann Curvature Tensor",
            category="tensors",
            description="Computes Riemann curvature tensor R^σ_{ρμν} from Christoffel connection",
            domain="differential_geometry",
            inputs=["Metric"],
            outputs=["Riemann Tensor"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
            citation="Riemannian Curvature"
        ))

        self.register(RuleDefinition(
            rule_id="ricci_curvature",
            name="Ricci Curvature Tensor",
            category="tensors",
            description="Contracts Riemann tensor to form symmetric Ricci tensor R_{μν} = R^σ_{μσν}",
            domain="differential_geometry",
            inputs=["Metric"],
            outputs=["Ricci Tensor"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
        ))

        self.register(RuleDefinition(
            rule_id="ricci_scalar",
            name="Ricci Curvature Scalar",
            category="tensors",
            description="Contracts Ricci tensor with inverse metric R = g^{μν} R_{μν}",
            domain="differential_geometry",
            inputs=["Metric"],
            outputs=["Ricci Scalar"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
        ))

        self.register(RuleDefinition(
            rule_id="einstein_tensor",
            name="Einstein Tensor",
            category="tensors",
            description="Computes trace-reversed Ricci curvature G_{μν} = R_{μν} - (1/2) g_{μν} R",
            domain="general_relativity",
            inputs=["Metric"],
            outputs=["Einstein Tensor"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
            citation="Einstein Field Equations"
        ))

        self.register(RuleDefinition(
            rule_id="geodesic_equations",
            name="Geodesic Equations of Motion",
            category="tensors",
            description="Derives autoparallel curve equations d²x^σ/dτ² + Γ^σ_{μν} (dx^μ/dτ)(dx^ν/dτ) = 0",
            domain="general_relativity",
            inputs=["Metric"],
            outputs=["Geodesic Equations"],
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["tensor"],
        ))

        self.register(RuleDefinition(
            rule_id="index_contract",
            name="Einstein Index Contraction",
            category="tensors",
            description="Contracts one upper and one lower index using Einstein summation convention",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=False,
            allowed_checkers=[],
        ))

        self.register(RuleDefinition(
            rule_id="raise_index",
            name="Raise Tensor Index",
            category="tensors",
            description="Raises a covariant tensor index using the inverse metric g^{mu nu}",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=False,
            allowed_checkers=[],
        ))

        self.register(RuleDefinition(
            rule_id="lower_index",
            name="Lower Tensor Index",
            category="tensors",
            description="Lowers a contravariant tensor index using the metric g_{mu nu}",
            domain="differential_geometry",
            implementation_backend="tensor",
            formal_proof_available=False,
            symbolic_checker_available=False,
            allowed_checkers=[],
        ))



        # 4B. Phase 1A Linear Algebra Core
        for linear_rule in [
            RuleDefinition(rule_id="vector_add", name="Vector Addition", category="linear_algebra",
                description="Adds two vectors componentwise.", domain="mathematics",
                inputs=["Vector", "Vector"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_subtract", name="Vector Subtraction", category="linear_algebra",
                description="Subtracts two vectors componentwise.", domain="mathematics",
                inputs=["Vector", "Vector"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_scalar_multiply", name="Vector Scalar Multiplication", category="linear_algebra",
                description="Multiplies each vector component by an explicit scalar.", domain="mathematics",
                inputs=["Vector"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_dot", name="Vector Dot Product", category="linear_algebra",
                description="Computes the ordinary dot product of equal-length vectors.", domain="mathematics",
                inputs=["Vector", "Vector"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_multiply", name="Matrix Multiplication", category="linear_algebra",
                description="Computes A*B when A.cols equals B.rows.", domain="mathematics",
                inputs=["Matrix", "Matrix"], outputs=["Matrix"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_transpose", name="Matrix Transpose", category="linear_algebra",
                description="Exchanges matrix rows and columns.", domain="mathematics",
                inputs=["Matrix"], outputs=["Matrix"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_determinant", name="Matrix Determinant", category="linear_algebra",
                description="Computes the determinant of a square matrix.", domain="mathematics",
                inputs=["Matrix"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_trace", name="Matrix Trace", category="linear_algebra",
                description="Computes the trace of a square matrix.", domain="mathematics",
                inputs=["Matrix"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_inverse", name="Matrix Inverse", category="linear_algebra",
                description="Computes the exact inverse of an invertible square matrix.", domain="mathematics",
                inputs=["Matrix"], outputs=["Matrix"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_rank", name="Matrix Rank", category="linear_algebra",
                description="Computes exact matrix rank.", domain="mathematics",
                inputs=["Matrix"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_rref", name="Reduced Row-Echelon Form", category="linear_algebra",
                description="Computes reduced row-echelon form through Gaussian elimination.", domain="mathematics",
                inputs=["Matrix"], outputs=["Matrix"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="linear_system_solve", name="Linear System Solver", category="linear_algebra",
                description="Solves unique square systems Ax=b and records elimination evidence.", domain="mathematics",
                inputs=["Matrix", "Vector"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_inner_product", name="Vector Inner Product", category="linear_algebra",
                description="Computes the exact inner product of equal-length vectors; Hermitian conjugation of the first vector is enabled by default.", domain="mathematics",
                inputs=["Vector", "Vector"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_norm", name="Euclidean Vector Norm", category="linear_algebra",
                description="Computes the exact Euclidean 2-norm of a vector.", domain="mathematics",
                inputs=["Vector"], outputs=["Scalar"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_orthogonal", name="Vector Orthogonality", category="linear_algebra",
                description="Verifies an orthogonality claim using the Hermitian inner product; output indicator is 1 for orthogonal and 0 otherwise.", domain="mathematics",
                inputs=["Vector", "Vector"], outputs=["Scalar Indicator"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_projection", name="Vector Projection", category="linear_algebra",
                description="Computes the orthogonal projection of one vector onto a non-zero target vector using the Hermitian inner product.", domain="mathematics",
                inputs=["Vector", "Target Vector"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="vector_gram_schmidt", name="Gram-Schmidt Orthogonalization", category="linear_algebra",
                description="Orthogonalizes a sequence of equal-dimensional vectors, optionally producing an orthonormal sequence; dependent inputs are rejected.", domain="mathematics",
                inputs=["Vector..."], outputs=["Vector..."], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"]),
            RuleDefinition(rule_id="matrix_characteristic_polynomial", name="Characteristic Polynomial", category="linear_algebra",
                description="Computes det(lam*I - A) for a square matrix using an explicit polynomial generator.", domain="mathematics",
                inputs=["Matrix"], outputs=["Scalar Polynomial"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"], citation="SymPy MatrixBase.charpoly"),
            RuleDefinition(rule_id="matrix_eigenvalues", name="Matrix Eigenvalues", category="linear_algebra",
                description="Computes the complete eigenvalue multiset of a square matrix, preserving algebraic multiplicity.", domain="mathematics",
                inputs=["Matrix"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"], citation="SymPy MatrixBase.eigenvals"),
            RuleDefinition(rule_id="matrix_eigenvector", name="Matrix Eigenvector", category="linear_algebra",
                description="Verifies a non-zero vector v satisfies A*v = lambda*v for an explicit eigenvalue lambda.", domain="mathematics",
                inputs=["Matrix"], outputs=["Vector"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"], citation="SymPy Matrix eigenvector semantics"),
            RuleDefinition(rule_id="matrix_diagonalize", name="Matrix Diagonalization", category="linear_algebra",
                description="Verifies A = P*D*P^-1 with square invertible P and diagonal D.", domain="mathematics",
                inputs=["Matrix"], outputs=["Matrix P", "Diagonal Matrix D"], implementation_backend="linear_algebra",
                allowed_checkers=["linear_algebra"], citation="SymPy MatrixBase.diagonalize"),
        ]:
            self.register(linear_rule)

        # 4C. Phase 2A Vector Calculus
        for vector_rule in [
            RuleDefinition(rule_id="scalar_field", name="Scalar Field", category="vector_calculus",
                description="Declares an explicit scalar expression as a scalar field in Cartesian coordinates.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Scalar Field"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="vector_field", name="Vector Field", category="vector_calculus",
                description="Declares an explicit vector expression as a vector field in Cartesian coordinates.",
                domain="mathematics", inputs=["Vector Field"], outputs=["Vector Field"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="gradient", name="Gradient", category="vector_calculus",
                description="Computes the Cartesian gradient of a scalar field.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Vector Field"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="directional_derivative", name="Directional Derivative", category="vector_calculus",
                description="Computes the directional derivative of a scalar field along a non-zero direction, normalized to a unit direction.",
                domain="mathematics", inputs=["Scalar Field", "Direction Vector"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="divergence", name="Divergence", category="vector_calculus",
                description="Computes the Cartesian divergence of a vector field.",
                domain="mathematics", inputs=["Vector Field"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="curl", name="Curl", category="vector_calculus",
                description="Computes the three-dimensional Cartesian curl of a vector field.",
                domain="mathematics", inputs=["Vector Field"], outputs=["Vector Field"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="laplacian", name="Laplacian", category="vector_calculus",
                description="Computes the scalar Cartesian Laplacian as the sum of second partial derivatives.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="conservative_field", name="Conservative Field / Potential", category="vector_calculus",
                description="Checks whether a vector field equals the gradient of a supplied scalar potential; output 1 means yes and 0 means no.",
                domain="mathematics", inputs=["Vector Field", "Potential"], outputs=["Scalar Indicator"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="line_integral_scalar", name="Scalar Line Integral", category="vector_calculus",
                description="Computes a scalar line integral along an explicit parameterized Cartesian curve.",
                domain="mathematics", inputs=["Scalar Field", "Curve"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="line_integral_vector", name="Vector Line Integral", category="vector_calculus",
                description="Computes the work integral of a vector field along an explicit parameterized Cartesian curve.",
                domain="mathematics", inputs=["Vector Field", "Curve"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="surface_integral_scalar", name="Scalar Surface Integral", category="vector_calculus",
                description="Computes a scalar surface integral over an explicit two-parameter Cartesian surface.",
                domain="mathematics", inputs=["Scalar Field", "Surface"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="surface_flux", name="Surface Flux Integral", category="vector_calculus",
                description="Computes oriented flux of a vector field through an explicit parameterized surface.",
                domain="mathematics", inputs=["Vector Field", "Surface"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="volume_integral", name="Volume Integral", category="vector_calculus",
                description="Computes a scalar volume integral over explicit Cartesian bounds.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Scalar"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="curl_gradient_identity", name="Curl of Gradient Identity", category="vector_calculus",
                description="Verifies curl(grad f)=0 for a scalar Cartesian field.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Scalar Residual"],
                required_assumptions=["second_partial_derivatives_exist"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="divergence_curl_identity", name="Divergence of Curl Identity", category="vector_calculus",
                description="Verifies div(curl F)=0 for a 3D Cartesian vector field.",
                domain="mathematics", inputs=["3D Vector Field"], outputs=["Scalar Residual"],
                required_assumptions=["second_partial_derivatives_exist"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="laplacian_identity", name="Laplacian Identity", category="vector_calculus",
                description="Verifies equivalent Cartesian scalar Laplacian definitions.",
                domain="mathematics", inputs=["Scalar Field"], outputs=["Scalar Residual"],
                required_assumptions=["second_partial_derivatives_exist"],
                implementation_backend="vector_calculus", allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="green_theorem", name="Green's Theorem", category="vector_calculus",
                description="Verifies circulation around an explicitly oriented Cartesian rectangle equals the double integral of planar curl.",
                domain="mathematics", inputs=["2D Vector Field"], outputs=["Scalar Equality Residual"],
                required_assumptions=["continuous_first_partial_derivatives_on_rectangle"],
                side_conditions=["ccw_boundary", "explicit_cartesian_rectangle"],
                implementation_backend="vector_calculus", formal_proof_available=False, symbolic_checker_available=True,
                allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="divergence_theorem", name="Divergence Theorem", category="vector_calculus",
                description="Verifies outward flux through an explicit Cartesian box equals the volume integral of divergence.",
                domain="mathematics", inputs=["3D Vector Field"], outputs=["Scalar Equality Residual"],
                required_assumptions=["continuous_first_partial_derivatives_on_box"],
                side_conditions=["outward_orientation", "explicit_cartesian_box"],
                implementation_backend="vector_calculus", formal_proof_available=False, symbolic_checker_available=True,
                allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="stokes_theorem", name="Stokes' Theorem", category="vector_calculus",
                description="Verifies circulation around an explicitly oriented planar Cartesian rectangle equals the surface integral of curl.",
                domain="mathematics", inputs=["3D Vector Field"], outputs=["Scalar Equality Residual"],
                required_assumptions=["continuous_first_partial_derivatives_on_surface"],
                side_conditions=["ccw_positive_normal_orientation", "explicit_cartesian_planar_surface"],
                implementation_backend="vector_calculus", formal_proof_available=False, symbolic_checker_available=True,
                allowed_checkers=["vector_calculus"]),
            RuleDefinition(rule_id="continuous_charge_field", name="Continuous Charge Field Kernel", category="electrostatics",
                description="Verifies a bounded differential contribution to electric field from an explicit charge-density sample.",
                domain="electromagnetism", inputs=["Charge Density", "Displacement Vector"], outputs=["Electric Field Contribution"],
                required_assumptions=["nonzero_separation", "explicit_density_measure"],
                side_conditions=["cartesian_displacement"],
                implementation_backend="electrostatics", allowed_checkers=["electrostatics"]),
            RuleDefinition(rule_id="continuous_charge_potential", name="Continuous Charge Potential Kernel", category="electrostatics",
                description="Verifies a bounded differential contribution to electric potential from an explicit charge-density sample.",
                domain="electromagnetism", inputs=["Charge Density", "Displacement Vector"], outputs=["Potential Contribution"],
                required_assumptions=["nonzero_separation", "explicit_density_measure"],
                side_conditions=["cartesian_displacement"],
                implementation_backend="electrostatics", allowed_checkers=["electrostatics"]),
            RuleDefinition(rule_id="coulomb_force", name="Coulomb Force", category="electromagnetism",
                description="Verifies the vector force between two point charges in an explicit Cartesian displacement.",
                domain="electromagnetism", inputs=["Charge", "Charge", "Position Vector", "Position Vector"], outputs=["Force Vector"],
                required_assumptions=["point_charges", "noncoincident_positions"],
                implementation_backend="electrostatics", allowed_checkers=["electrostatics"]),
            RuleDefinition(rule_id="point_charge_field", name="Point-Charge Electric Field", category="electromagnetism",
                description="Verifies the electric field of a point charge at a nonzero displacement.",
                domain="electromagnetism", inputs=["Charge", "Displacement Vector"], outputs=["Electric Field Vector"],
                required_assumptions=["point_charge", "nonzero_displacement"],
                implementation_backend="electrostatics", allowed_checkers=["electrostatics"]),
            RuleDefinition(rule_id="point_charge_potential", name="Point-Charge Electric Potential", category="electromagnetism",
                description="Verifies the electric potential of a point charge at a nonzero displacement.",
                domain="electromagnetism", inputs=["Charge", "Displacement Vector"], outputs=["Electric Potential"],
                required_assumptions=["point_charge", "nonzero_displacement"],
                implementation_backend="electrostatics", allowed_checkers=["electrostatics"]),
        ]:
            self.register(vector_rule)

        # 5. Differential Equations & Solutions
        self.register(RuleDefinition(
            rule_id="solve_harmonic_oscillator",
            name="Harmonic Oscillator General Solution",
            category="differential_equations",
            description=(
                "Verifies that a proposed solution satisfies the harmonic oscillator ODE "
                "m*x_ddot + k*x = 0 by substitution. "
                "Expects ODE in shorthand (x_ddot) or function notation (diff(x(t),t,2))."
            ),
            domain="classical_mechanics",
            inputs=["Equation of Motion"],
            outputs=["Analytical Solution"],
            required_assumptions=["asm_pos_mass", "asm_pos_k"],
            side_conditions=["asm_pos_mass", "asm_pos_k"],
            default_obligations=[{
                "type": "ode_substitution",
                "claim": "residual of ODE after substituting candidate solution == 0",
                "description": "Candidate solution satisfies the equation of motion"
            }],
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy", "numerical"],
            citation="Linear Ordinary Differential Equations"
        ))

        self.register(RuleDefinition(
            rule_id="verify_ode_solution",
            name="General ODE Solution Verifier",
            category="differential_equations",
            description=(
                "Verifies a proposed solution to a general ODE by substitution. "
                "Supports first- and second-order ODEs, arbitrary dependent variables, "
                "shorthand notation (x_ddot) and function notation (x(t), diff(x(t),t,2)). "
                "Does NOT hardcode harmonic oscillator assumptions."
            ),
            domain="mathematics",
            inputs=["ODE"],
            outputs=["Analytical Solution"],
            required_assumptions=[],
            default_obligations=[{
                "type": "ode_substitution",
                "claim": "residual after substituting candidate into ODE == 0",
                "description": "Candidate solution satisfies the ODE by substitution"
            }],
            implementation_backend="sympy",
            formal_proof_available=False,
            symbolic_checker_available=True,
            allowed_checkers=["sympy", "numerical"],
        ))

        self.register(RuleDefinition(
            rule_id="algebraic_identity",
            name="Algebraic Identity",
            category="algebra",
            description="Symbolic simplification, expansion, or algebraic equality",
            domain="mathematics",
            implementation_backend="sympy",
            formal_proof_available=True,
            symbolic_checker_available=True,
            allowed_checkers=["sympy", "lean4"],
        ))

        # 6. Computational & Experimental
        self.register(RuleDefinition(
            rule_id="numerical_simulation",
            name="Numerical IVP Integration",
            category="numerics",
            description="Numerical integration of equations of motion using Runge-Kutta ODE solver",
            domain="computational_physics",
            implementation_backend="numerical",
            formal_proof_available=False,
            symbolic_checker_available=False,
            allowed_checkers=["numerical"],
        ))

        self.register(RuleDefinition(
            rule_id="empirical_inference",
            name="Empirical Parameter Estimation",
            category="statistics",
            description="Non-linear least squares parameter estimation against observational data",
            domain="experimental_physics",
            implementation_backend="statistical",
            formal_proof_available=False,
            symbolic_checker_available=False,
            allowed_checkers=["statistical"],
        ))

    def register(self, rule: RuleDefinition) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Optional[RuleDefinition]:
        return self._rules.get(rule_id)

    def get_rule(self, rule_id: str) -> Optional[RuleDefinition]:
        return self.get(rule_id)

    def list_rules(self) -> List[RuleDefinition]:
        return list(self._rules.values())

    def list_rule_ids(self) -> List[str]:
        return list(self._rules.keys())

    def is_checker_allowed(self, rule_id: str, checker_name: str) -> bool:
        """Returns True if checker_name is semantically valid for rule_id."""
        rule = self.get(rule_id)
        if rule is None:
            return False
        return checker_name in rule.allowed_checkers

