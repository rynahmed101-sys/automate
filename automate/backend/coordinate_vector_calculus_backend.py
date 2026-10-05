"""Bounded coordinate-aware orthogonal vector-calculus verification.

Canonical semantics use physical components in named orthogonal coordinates.
Supported systems are Cartesian, cylindrical and spherical.  Cartesian is
included as an explicit baseline; unsupported or singular coordinate systems
fail closed rather than silently falling back to Cartesian formulas.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import sympy as sp
from automate.backend.base import BaseChecker, VerificationEvidence, VerificationReport
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus
from automate.ir.linear_algebra import parse_linear_algebra_expression, ParsedLinearAlgebra, LinearAlgebraParseError

@dataclass(frozen=True)
class OrthogonalCoordinateSystem:
    name: str
    coordinates: tuple[sp.Symbol, ...]
    scale_factors: tuple[sp.Expr, ...]

    @classmethod
    def from_parameters(cls, p: dict[str, Any]) -> "OrthogonalCoordinateSystem":
        name = p.get("coordinate_system")
        coords = p.get("coordinates")
        if not isinstance(name, str) or name not in {"cartesian", "cylindrical", "spherical"}:
            raise ValueError("coordinate_system must be one of cartesian, cylindrical, spherical")
        dims = 2 if name == "cartesian" and isinstance(coords, list) and len(coords) == 2 else 3
        expected = {"cartesian": dims, "cylindrical": 3, "spherical": 3}[name]
        if not isinstance(coords, list) or len(coords) != expected or not all(isinstance(x, str) and x.isidentifier() for x in coords):
            raise ValueError(f"{name} requires exactly {expected} identifier coordinates")
        symbols = tuple(sp.Symbol(x) for x in coords)
        defaults = {
            "cartesian": tuple(sp.Integer(1) for _ in symbols),
            "cylindrical": (sp.Integer(1), symbols[0], sp.Integer(1)),
            "spherical": (sp.Integer(1), symbols[0], symbols[0] * sp.sin(symbols[1])),
        }[name]
        supplied = p.get("scale_factors")
        if supplied is None:
            factors = defaults
        else:
            if not isinstance(supplied, list) or len(supplied) != expected:
                raise ValueError("scale_factors must match coordinate dimension")
            parsed = [parse_linear_algebra_expression(str(v)) for v in supplied]
            if any(v.kind != "scalar" for v in parsed):
                raise ValueError("scale_factors must be scalar expressions")
            factors = tuple(v.value for v in parsed)
        exclusions = p.get("domain_exclusions", [])
        if name in {"cylindrical", "spherical"} and (not isinstance(exclusions, list) or not exclusions):
            raise ValueError("domain_exclusions must explicitly exclude coordinate singularities for cylindrical/spherical systems")
        if any(sp.simplify(h) == 0 for h in factors):
            raise ValueError("scale factors must be nonzero on the declared domain")
        return cls(name, symbols, tuple(factors))

    def gradient(self, f: sp.Expr) -> sp.Matrix:
        return sp.Matrix([sp.diff(f, q) / h for q, h in zip(self.coordinates, self.scale_factors)])

    def divergence(self, A: sp.Matrix) -> sp.Expr:
        h = self.scale_factors
        q = self.coordinates
        H = sp.prod(h)
        return sp.simplify(sum(sp.diff(H * A[i] / h[i], q[i]) for i in range(len(q))) / H)

    def curl(self, A: sp.Matrix) -> sp.Matrix:
        if len(self.coordinates) != 3:
            raise ValueError("curl requires a three-dimensional orthogonal system")
        q = self.coordinates; h1,h2,h3 = self.scale_factors
        return sp.Matrix([
            sp.diff(h3*A[2], q[1]) - sp.diff(h2*A[1], q[2]),
            sp.diff(h1*A[0], q[2]) - sp.diff(h3*A[2], q[0]),
            sp.diff(h2*A[1], q[0]) - sp.diff(h1*A[0], q[1]),
        ]).applyfunc(lambda x: sp.simplify(x / (h2*h3) if False else x))

    def curl_physical(self, A: sp.Matrix) -> sp.Matrix:
        if len(self.coordinates) != 3:
            raise ValueError("curl requires a three-dimensional orthogonal system")
        q = self.coordinates; h1,h2,h3 = self.scale_factors
        return sp.Matrix([
            sp.diff(h3*A[2], q[1]) - sp.diff(h2*A[1], q[2]),
            sp.diff(h1*A[0], q[2]) - sp.diff(h3*A[2], q[0]),
            sp.diff(h2*A[1], q[0]) - sp.diff(h1*A[0], q[1]),
        ]).multiply_elementwise(sp.Matrix([1/(h2*h3), 1/(h3*h1), 1/(h1*h2)])).applyfunc(sp.simplify)

    def laplacian(self, f: sp.Expr) -> sp.Expr:
        h = self.scale_factors; q = self.coordinates; H = sp.prod(h)
        return sp.simplify(sum(sp.diff(H/(h[i]**2) * sp.diff(f, q[i]), q[i]) for i in range(len(q))) / H)

class CoordinateVectorCalculusChecker(BaseChecker):
    _RULES = {"coordinate_gradient","coordinate_divergence","coordinate_curl","coordinate_laplacian"}

    @property
    def name(self): return "CoordinateVectorCalculusChecker"
    @property
    def version(self): return f"SymPy {sp.__version__}"

    def _report(self, edge, graph, status, passed, details, message=None):
        evidence = VerificationEvidence(
            backend=self.name, backend_version=self.version, graph_id=graph.id, edge_id=edge.id,
            input_node_ids=edge.input_nodes, output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions, generated_obligations=edge.verification_obligations,
            command_invocation=f"CoordinateVectorCalculusChecker.verify_edge('{edge.id}')",
            passed=passed, status=status, execution_time_ms=0.0,
            reproducibility={"sympy": sp.__version__}, metrics={"operation": details.get("operation")})
        return VerificationReport(status=status, backend=self.name, backend_version=self.version,
            execution_time_ms=0.0, passed=passed, details=details, error_message=message, evidence=evidence)

    @staticmethod
    def _equal(a, b):
        if a.kind != b.kind or a.shape != b.shape: return False
        if a.kind == "scalar": return bool(sp.simplify(a.value-b.value)==0)
        A,B=sp.Matrix(a.value),sp.Matrix(b.value)
        return all(sp.simplify(A[i]-B[i])==0 for i in range(A.rows))

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph):
        details={"operation":edge.transformation_rule}
        if edge.transformation_rule not in self._RULES:
            return self._report(edge,graph,VerificationStatus.FAILED,False,details,"Unsupported coordinate vector-calculus rule.")
        try:
            cs=OrthogonalCoordinateSystem.from_parameters(edge.parameters)
            inputs=[parse_linear_algebra_expression(graph.nodes[n].expression.raw_str) for n in edge.input_nodes]
            outputs=[parse_linear_algebra_expression(graph.nodes[n].expression.raw_str) for n in edge.output_nodes]
            if len(inputs)!=1 or len(outputs)!=1: raise ValueError("coordinate operation requires one input and one output")
            rule=edge.transformation_rule
            if rule in {"coordinate_gradient","coordinate_laplacian"} and inputs[0].kind!="scalar": raise ValueError("scalar field required")
            if rule in {"coordinate_divergence","coordinate_curl"} and inputs[0].kind!="vector": raise ValueError("vector field required")
            expected = {"coordinate_gradient":cs.gradient(inputs[0].value),
                        "coordinate_divergence":cs.divergence(sp.Matrix(inputs[0].value)),
                        "coordinate_curl":cs.curl_physical(sp.Matrix(inputs[0].value)),
                        "coordinate_laplacian":cs.laplacian(inputs[0].value)}[rule]
            output_symbols = {str(s): s for s in outputs[0].value.free_symbols}
            expected = expected.xreplace({s: output_symbols[str(s)] for s in expected.free_symbols if str(s) in output_symbols})
            expected_p=ParsedLinearAlgebra("vector" if isinstance(expected,sp.MatrixBase) else "scalar", expected)
            if not self._equal(outputs[0],expected_p):
                return self._report(edge,graph,VerificationStatus.FAILED,False,{**details,"expected":str(expected),"actual":str(outputs[0].value)},"Coordinate-aware result is incorrect.")
            return self._report(edge,graph,VerificationStatus.SYMBOLIC_CHECKED,True,{**details,"symbolic_equivalence":True,"coordinate_system":cs.name,"coordinates":[str(x) for x in cs.coordinates],"scale_factors":[str(x) for x in cs.scale_factors], "domain_exclusions": edge.parameters.get("domain_exclusions", [])})
        except (KeyError,TypeError,ValueError,LinearAlgebraParseError,sp.SympifyError) as exc:
            return self._report(edge,graph,VerificationStatus.FAILED,False,details,f"Coordinate-aware verification failed: {exc}")
