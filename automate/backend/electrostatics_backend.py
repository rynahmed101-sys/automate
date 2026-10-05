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

    _RULES = {"coulomb_force", "point_charge_field", "point_charge_potential", "continuous_charge_field", "continuous_charge_potential", "uniform_line_charge_potential", "gauss_law_box", "conductor_boundary_field", "parallel_plate_field", "parallel_plate_capacitance", "capacitor_energy"}

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
            elif rule == "gauss_law_box":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("gauss_law_box requires electric field, charge density, and one flux output.")
                field, rho = inputs
                if field.kind != "vector" or rho.kind != "scalar" or outputs[0].kind != "scalar" or len(field.value) != 3:
                    raise ValueError("gauss_law_box requires a 3D vector field, scalar charge density, and scalar flux output.")
                if edge.parameters.get("coordinates") != ["x", "y", "z"]:
                    raise ValueError("gauss_law_box is bounded to Cartesian x,y,z coordinates.")
                raw_bounds = edge.parameters.get("bounds")
                if not isinstance(raw_bounds, list) or len(raw_bounds) != 3:
                    raise ValueError("gauss_law_box requires three explicit [lower, upper] bounds.")
                bounds = []
                for pair in raw_bounds:
                    if not isinstance(pair, list) or len(pair) != 2:
                        raise ValueError("Each gauss_law_box bound must be a [lower, upper] pair.")
                    lo, hi = self._parse(str(pair[0])), self._parse(str(pair[1]))
                    if lo.kind != "scalar" or hi.kind != "scalar":
                        raise ValueError("Gauss-law box bounds must be scalar expressions.")
                    if sp.ask(sp.Q.positive(sp.simplify(hi.value - lo.value))) is not True:
                        raise ValueError("Gauss-law box bounds must define provably positive finite intervals.")
                    bounds.append((lo.value, hi.value))
                epsilon = self._parse(str(edge.parameters.get("epsilon0", "epsilon0")))
                if epsilon.kind != "scalar" or not epsilon.value.is_commutative:
                    raise ValueError("epsilon0 must be an explicit scalar commutative factor.")
                if edge.parameters.get("orientation") != "outward":
                    raise ValueError("gauss_law_box requires explicit outward orientation.")
                x, y, z = sp.symbols("x y z")
                F = sp.Matrix(field.value)
                (x0, x1), (y0, y1), (z0, z1) = bounds
                flux = (
                    sp.integrate(sp.integrate(-F[0].subs(x, x0), (z, z0, z1)), (y, y0, y1)) +
                    sp.integrate(sp.integrate(F[0].subs(x, x1), (z, z0, z1)), (y, y0, y1)) +
                    sp.integrate(sp.integrate(-F[1].subs(y, y0), (z, z0, z1)), (x, x0, x1)) +
                    sp.integrate(sp.integrate(F[1].subs(y, y1), (z, z0, z1)), (x, x0, x1)) +
                    sp.integrate(sp.integrate(-F[2].subs(z, z0), (y, y0, y1)), (x, x0, x1)) +
                    sp.integrate(sp.integrate(F[2].subs(z, z1), (y, y0, y1)), (x, x0, x1))
                )
                enclosed_charge = sp.integrate(sp.integrate(sp.integrate(rho.value, (z, z0, z1)), (y, y0, y1)), (x, x0, x1))
                expected_flux = sp.simplify(enclosed_charge / epsilon.value)
                actual_flux = ParsedLinearAlgebra("scalar", flux)
                if not self._equal(outputs[0], actual_flux):
                    raise ValueError("Reported closed-surface flux does not match the field's actual box flux.")
                if not self._equal(actual_flux, ParsedLinearAlgebra("scalar", expected_flux)):
                    raise ValueError("Gauss-law equality fails: closed-surface flux is not enclosed_charge / epsilon0.")
                details["flux"] = str(sp.simplify(flux))
                details["enclosed_charge"] = str(sp.simplify(enclosed_charge))
                details["expected_flux"] = str(expected_flux)
                details["symbolic_equivalence"] = True
                details["contract"] = {"geometry":"closed Cartesian rectangular box","orientation":"outward","law":"surface_flux(E) = enclosed_charge / epsilon0"}
                details["independent_evidence"] = {"available":True,"independence_class":"TWO_INTEGRALS_SYMBOLIC","claim":"Closed-surface flux and enclosed charge were independently integrated and compared."}
                return VerificationReport(status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name, backend_version=self.version, execution_time_ms=(time.perf_counter()-start)*1000, passed=True, details=details)
            elif rule == "conductor_boundary_field":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("conductor_boundary_field requires electric field, conductor normal, and one tangential-field output.")
                field, normal = inputs
                if field.kind != "vector" or normal.kind != "vector" or outputs[0].kind != "vector":
                    raise ValueError("conductor_boundary_field requires vector field, vector normal, and vector output.")
                if len(field.value) != 3 or len(normal.value) != 3:
                    raise ValueError("conductor_boundary_field is bounded to 3D Cartesian vectors.")
                if edge.parameters.get("coordinates") != ["x", "y", "z"]:
                    raise ValueError("conductor_boundary_field requires explicit Cartesian coordinates.")
                n = sp.Matrix(normal.value)
                n2 = sp.simplify(n.dot(n))
                if n2 == 0:
                    raise ValueError("Conductor surface normal must be nonzero.")
                nonzero = [sp.simplify(component) != 0 for component in n]
                if sum(bool(v) for v in nonzero) != 1:
                    raise ValueError("Conductor boundary normal must be axis-aligned for the bounded Cartesian model.")
                n_hat = n / sp.sqrt(n2)
                F = sp.Matrix(field.value)
                tangential = sp.simplify(F - n_hat * (n_hat.dot(F)))
                expected_parsed = ParsedLinearAlgebra("vector", tangential)
                if not self._equal(outputs[0], expected_parsed):
                    raise ValueError("Reported tangential electric field does not match the boundary projection.")
                if not self._equal(expected_parsed, ParsedLinearAlgebra("vector", sp.zeros(3, 1))):
                    raise ValueError("Ideal conductor boundary requires zero tangential electric field.")
                details["boundary_condition"] = "E_tangential = 0"
                details["normal"] = [str(v) for v in n]
                details["coordinates"] = ["x", "y", "z"]
                details["symbolic_equivalence"] = True
                return VerificationReport(status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name, backend_version=self.version,
                    execution_time_ms=(time.perf_counter()-start)*1000, passed=True, details=details)
            elif rule == "parallel_plate_field":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("parallel_plate_field requires surface charge density, permittivity, and one field output.")
                sigma, epsilon = inputs
                if sigma.kind != "scalar" or epsilon.kind != "scalar" or outputs[0].kind != "vector":
                    raise ValueError("parallel_plate_field requires scalar sigma, scalar epsilon, and vector output.")
                if edge.parameters.get("coordinates") != ["x", "y", "z"] or edge.parameters.get("model") != "ideal_parallel_plates":
                    raise ValueError("parallel_plate_field requires the bounded ideal Cartesian parallel-plate model.")
                normal_raw = edge.parameters.get("plate_normal")
                if normal_raw is None:
                    raise ValueError("parallel_plate_field requires an explicit plate_normal.")
                normal = self._parse(str(normal_raw))
                if normal.kind != "vector" or len(normal.value) != 3:
                    raise ValueError("plate_normal must be a 3D vector.")
                n = sp.Matrix(normal.value)
                n2 = sp.simplify(n.dot(n))
                if n2 == 0:
                    raise ValueError("plate_normal must be nonzero.")
                if sum(bool(sp.simplify(v) != 0) for v in n) != 1:
                    raise ValueError("plate_normal must be axis-aligned for the bounded Cartesian model.")
                if epsilon.value == 0:
                    raise ValueError("Permittivity must be nonzero.")
                expected_parsed = ParsedLinearAlgebra("vector", (sigma.value / epsilon.value) * n / sp.sqrt(n2))
                if not self._equal(outputs[0], expected_parsed):
                    details.update({"expected": self._display(expected_parsed), "actual": self._display(outputs[0])})
                    return VerificationReport(passed=False, status=VerificationStatus.FAILED, backend=self.name,
                        backend_version=self.version, details=details, error_message="Parallel-plate electric field is mathematically incorrect.",
                        execution_time_ms=(time.perf_counter()-start)*1000)
                details["relation"] = "E = sigma / epsilon * n_hat"
                details["model"] = "ideal_parallel_plates"
                details["symbolic_equivalence"] = True
                return VerificationReport(status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name, backend_version=self.version,
                    execution_time_ms=(time.perf_counter()-start)*1000, passed=True, details=details)
            elif rule == "parallel_plate_capacitance":
                if len(inputs) != 3 or len(outputs) != 1:
                    raise ValueError("parallel_plate_capacitance requires permittivity, plate area, separation, and one capacitance output.")
                epsilon, area, separation = inputs
                if any(value.kind != "scalar" for value in inputs) or outputs[0].kind != "scalar":
                    raise ValueError("parallel_plate_capacitance requires scalar permittivity, area, separation, and output.")
                if edge.parameters.get("coordinates") != ["x", "y", "z"] or edge.parameters.get("geometry") != "parallel_rectangular_plates":
                    raise ValueError("parallel_plate_capacitance requires explicit Cartesian parallel rectangular plates.")
                if edge.parameters.get("fringing") != "neglected":
                    raise ValueError("The bounded capacitor relation requires the explicit negligible-fringing idealization.")
                if sp.ask(sp.Q.positive(area.value)) is not True or sp.ask(sp.Q.positive(separation.value)) is not True:
                    raise ValueError("Plate area and separation must be provably positive.")
                if epsilon.value == 0:
                    raise ValueError("Permittivity must be nonzero.")
                expected_parsed = ParsedLinearAlgebra("scalar", epsilon.value * area.value / separation.value)
                if not self._equal(outputs[0], expected_parsed):
                    details.update({"expected": self._display(expected_parsed), "actual": self._display(outputs[0])})
                    return VerificationReport(passed=False, status=VerificationStatus.FAILED, backend=self.name,
                        backend_version=self.version, details=details, error_message="Parallel-plate capacitance is mathematically incorrect.",
                        execution_time_ms=(time.perf_counter()-start)*1000)
                details["relation"] = "C = epsilon * A / d"
                details["geometry"] = "parallel_rectangular_plates"
                details["fringing"] = "neglected"
                details["symbolic_equivalence"] = True
                return VerificationReport(status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name, backend_version=self.version,
                    execution_time_ms=(time.perf_counter()-start)*1000, passed=True, details=details)
            elif rule == "capacitor_energy":
                if len(inputs) != 2 or len(outputs) != 1:
                    raise ValueError("capacitor_energy requires capacitance, voltage, and one energy output.")
                capacitance, voltage = inputs
                if capacitance.kind != "scalar" or voltage.kind != "scalar" or outputs[0].kind != "scalar":
                    raise ValueError("capacitor_energy requires scalar capacitance, voltage, and output.")
                if edge.parameters.get("model") != "electrostatic_capacitor":
                    raise ValueError("capacitor_energy requires the explicit electrostatic capacitor model.")
                expected_parsed = ParsedLinearAlgebra("scalar", sp.Rational(1, 2) * capacitance.value * voltage.value**2)
                if not self._equal(outputs[0], expected_parsed):
                    details.update({"expected": self._display(expected_parsed), "actual": self._display(outputs[0])})
                    return VerificationReport(passed=False, status=VerificationStatus.FAILED, backend=self.name,
                        backend_version=self.version, details=details, error_message="Capacitor stored energy is mathematically incorrect.",
                        execution_time_ms=(time.perf_counter()-start)*1000)
                details["relation"] = "U = 1/2 * C * V**2"
                details["model"] = "electrostatic_capacitor"
                details["symbolic_equivalence"] = True
                return VerificationReport(status=VerificationStatus.SYMBOLIC_CHECKED, backend=self.name, backend_version=self.version,
                    execution_time_ms=(time.perf_counter()-start)*1000, passed=True, details=details)
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
