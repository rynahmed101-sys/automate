"""Verification backend for the bounded Phase 2B electrostatics core."""

from __future__ import annotations

import time
from typing import Any

import sympy as sp

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus
from automate.ir.linear_algebra import ParsedLinearAlgebra, parse_linear_algebra_expression


class ElectrostaticsChecker(BaseChecker):
    """Verify exact point-charge electrostatics claims in Cartesian coordinates."""

    _RULES = {"coulomb_force", "point_charge_field", "point_charge_potential", "continuous_charge_field", "continuous_charge_potential", "uniform_line_charge_potential"}

    @property
    def name(self) -> str:
        return "ElectrostaticsChecker"

    @property
    def version(self) -> str:
        return f"SymPy {sp.__version__}"

    @staticmethod
    def _parse(text: str) -> ParsedLinearAlgebra:
        return parse_linear_algebra_expression(text)

    @staticmethod
    def _equal(a: ParsedLinearAlgebra, b: ParsedLinearAlgebra) -> bool:
        if a.kind != b.kind or a.shape != b.shape:
            return False
        if a.kind == "scalar":
            difference = sp.simplify(a.value - b.value)
            return bool(difference == 0 or difference.equals(0) is True)
        am, bm = sp.Matrix(a.value), sp.Matrix(b.value)
        return all(
            bool((difference := sp.simplify(am[i, 0] - bm[i, 0])) == 0 or difference.equals(0) is True)
            for i in range(am.rows)
        )

    @staticmethod
    def _display(v: ParsedLinearAlgebra) -> Any:
        if v.kind == "scalar":
            return str(v.value)
        return [str(x) for x in sp.Matrix(v.value)]

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start = time.perf_counter()
        details: dict[str, Any] = {"operation": edge.transformation_rule}
        try:
            rule = edge.transformation_rule
            if rule not in self._RULES:
                raise ValueError(f"Unsupported electrostatics rule: {rule}")
            inputs = [self._parse(graph.nodes[nid].expression.raw_str) for nid in edge.input_nodes]
            outputs = [self._parse(graph.nodes[nid].expression.raw_str) for nid in edge.output_nodes]
            k_parsed = self._parse(str(edge.parameters.get("k", "k")))
            if k_parsed.kind != "scalar":
                raise ValueError("k must be a scalar commutative factor.")
            k = k_parsed.value
            if rule in {"continuous_charge_field", "continuous_charge_potential"}:
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError(f"{rule} requires charge density and displacement sample.")
                rho, displacement = inputs
                if rho.kind != "scalar" or displacement.kind != "vector":
                    raise ValueError(f"{rule} requires scalar density and vector displacement.")
                d = sp.Matrix(displacement.value)
                r2_norm = sp.simplify(d.dot(d))
                if r2_norm == 0:
                    raise ValueError("Continuous charge kernel is undefined at zero separation.")
                if "density_measure" not in edge.parameters:
                    raise ValueError("density_measure is required explicitly.")
                density_measure_parsed = self._parse(str(edge.parameters["density_measure"]))
                if density_measure_parsed.kind != "scalar":
                    raise ValueError("density_measure must be a scalar commutative factor.")
                density_measure = density_measure_parsed.value
                if not density_measure.is_commutative:
                    raise ValueError("density_measure must be a scalar commutative factor.")
                kernel = density_measure * rho.value
                if rule == "continuous_charge_field":
                    if outputs[0].kind != "vector":
                        raise ValueError("continuous_charge_field requires vector output.")
                    expected_parsed = ParsedLinearAlgebra("vector", k*kernel*d/(r2_norm**sp.Rational(3,2)))
                else:
                    if outputs[0].kind != "scalar":
                        raise ValueError("continuous_charge_potential requires scalar output.")
                    expected_parsed = ParsedLinearAlgebra("scalar", k*kernel/sp.sqrt(r2_norm))
            elif rule == "coulomb_force":
                if len(inputs) != 4 or len(outputs) != 1:
                    raise ValueError("coulomb_force requires q1, q2, r1, r2 and one vector output.")
                q1,q2,r1,r2 = inputs
                if q1.kind != "scalar" or q2.kind != "scalar" or r1.kind != "vector" or r2.kind != "vector":
                    raise ValueError("coulomb_force requires two scalar charges and two position vectors.")
                if len(r1.value) != len(r2.value) or outputs[0].kind != "vector":
                    raise ValueError("Position and force vectors must have matching dimensions.")
                displacement = sp.Matrix(r2.value) - sp.Matrix(r1.value)
                r2_norm = sp.simplify(displacement.dot(displacement))
                if r2_norm == 0:
                    raise ValueError("Coulomb force is undefined for coincident charges.")
                expected = k*q1.value*q2.value*displacement/(r2_norm**sp.Rational(3,2))
                expected_parsed = ParsedLinearAlgebra("vector", expected)
            elif rule == "uniform_line_charge_potential":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("uniform_line_charge_potential requires linear density, observation position, and one scalar output.")
                lam, observation = inputs
                if lam.kind != "scalar" or observation.kind != "vector" or outputs[0].kind != "scalar":
                    raise ValueError("uniform_line_charge_potential requires scalar density, vector observation, and scalar output.")
                axis = edge.parameters.get("axis")
                bounds = edge.parameters.get("source_bounds")
                coordinates = edge.parameters.get("coordinates")
                if axis not in {"x", "y", "z"} or coordinates != ["x", "y", "z"]:
                    raise ValueError("Line charge is bounded to a Cartesian x/y/z axis with coordinates [x,y,z].")
                if not isinstance(bounds, list) or len(bounds) != 2:
                    raise ValueError("source_bounds must contain [lower, upper].")
                parsed_bounds = [self._parse(str(bound)) for bound in bounds]
                if any(bound.kind != "scalar" for bound in parsed_bounds):
                    raise ValueError("source_bounds must contain scalar mathematical expressions.")
                lo, hi = (bound.value for bound in parsed_bounds)
                interval = sp.simplify(hi - lo)
                if sp.ask(sp.Q.positive(interval)) is not True:
                    raise ValueError("source_bounds must define a provably positive finite interval.")
                obs = sp.Matrix(observation.value)
                axis_index = {"x": 0, "y": 1, "z": 2}[axis]
                transverse = [obs[i] for i in range(3) if i != axis_index]
                transverse_sq = sp.simplify(sum(component**2 for component in transverse))
                if transverse_sq == 0:
                    source_coordinate = obs[axis_index]
                    if not (source_coordinate.is_number and lo.is_number and hi.is_number):
                        raise ValueError("Observation must be explicitly off the source segment when its transverse distance is zero.")
                    if bool(source_coordinate >= lo and source_coordinate <= hi):
                        raise ValueError("Observation point must be off the finite line-charge segment.")
                parameter = sp.Symbol(f"source_{axis}")
                source = sp.zeros(3, 1)
                source[axis_index] = parameter
                distance_sq = sp.simplify((obs - source).dot(obs - source))
                integrand = k * lam.value / sp.sqrt(distance_sq)
                expected_parsed = ParsedLinearAlgebra("scalar", sp.integrate(integrand, (parameter, lo, hi)))
            elif rule == "point_charge_field":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("point_charge_field requires charge and observation-minus-source displacement.")
                q, displacement = inputs
                if q.kind != "scalar" or displacement.kind != "vector" or outputs[0].kind != "vector":
                    raise ValueError("point_charge_field requires scalar charge, vector displacement, and vector output.")
                d = sp.Matrix(displacement.value)
                r2_norm = sp.simplify(d.dot(d))
                if r2_norm == 0:
                    raise ValueError("Point-charge field is undefined at the charge location.")
                expected_parsed = ParsedLinearAlgebra("vector", k*q.value*d/(r2_norm**sp.Rational(3,2)))
            else:
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("point_charge_potential requires charge and displacement.")
                q, displacement = inputs
                if q.kind != "scalar" or displacement.kind != "vector" or outputs[0].kind != "scalar":
                    raise ValueError("point_charge_potential requires scalar charge, vector displacement, and scalar output.")
                d = sp.Matrix(displacement.value)
                r2_norm = sp.simplify(d.dot(d))
                if r2_norm == 0:
                    raise ValueError("Point-charge potential is undefined at the charge location.")
                expected_parsed = ParsedLinearAlgebra("scalar", k*q.value/sp.sqrt(r2_norm))
            if not self._equal(outputs[0], expected_parsed):
                details.update({"expected": self._display(expected_parsed), "actual": self._display(outputs[0])})
                return VerificationReport(
                    passed=False, status=VerificationStatus.FAILED,
                    backend="electrostatics", backend_version=self.version,
                    details=details,
                    error_message=f"{rule} result is mathematically incorrect.",
                    execution_time_ms=(time.perf_counter()-start)*1000,
                )
            details["symbolic_equivalence"] = True
            details["constant_contract"] = {"k": str(k), "interpretation": "Coulomb constant or equivalent unit-system constant"}
            return VerificationReport(
                passed=True, status=VerificationStatus.SYMBOLIC_CHECKED,
                backend="electrostatics", backend_version=self.version,
                details=details,
                execution_time_ms=(time.perf_counter()-start)*1000,
            )
        except (KeyError, TypeError, ValueError, sp.SympifyError) as exc:
            return VerificationReport(
                passed=False, status=VerificationStatus.FAILED,
                backend="electrostatics", backend_version=self.version,
                details=details,
                error_message=f"Electrostatics verification failed: {exc}",
                execution_time_ms=(time.perf_counter()-start)*1000,
            )
