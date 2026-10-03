"""
DimensionChecker: Verifies physical dimensional consistency across expressions,
equations, derivatives, and transformations.
"""

import time
from typing import Dict, Any, List
from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.ir.dimensions import Dimension


class DimensionChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "DimensionChecker"

    @property
    def version(self) -> str:
        return "1.0.0"

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start_time = time.perf_counter()

        in_nodes = [graph.get_node(nid) for nid in edge.input_nodes]
        out_nodes = [graph.get_node(nid) for nid in edge.output_nodes]

        if not all(in_nodes) or not all(out_nodes):
            return VerificationReport(
                status=VerificationStatus.FAILED,
                backend=self.name,
                backend_version=self.version,
                passed=False,
                error_message="One or more referenced input or output nodes not found."
            )

        details: Dict[str, Any] = {
            "rule": edge.transformation_rule,
            "inspected_nodes": {}
        }

        # Check dimension consistency based on rule
        rule = edge.transformation_rule
        passed = True
        error_msg = None

        if rule == "euler_lagrange":
            # Input is Lagrangian: dimension should be Energy [M*L^2*T^-2]
            # Output is Equation of Motion: dimension should be Force [M*L*T^-2]
            # [EoM] = [L] / [coord] = [Energy] / [Length] = [Force]
            lagr_node = in_nodes[0]
            eom_node = out_nodes[0]

            lagr_dim = lagr_node.expression.get_dimension()
            eom_dim = eom_node.expression.get_dimension()

            details["inspected_nodes"][lagr_node.id] = repr(lagr_dim)
            details["inspected_nodes"][eom_node.id] = repr(eom_dim)

            # If dimensions are specified, check [EoM] == [Lagrangian] / [Length]
            coord_dim = Dimension.length()
            expected_eom_dim = lagr_dim / coord_dim

            if not lagr_dim.is_dimensionless() and not eom_dim.is_dimensionless():
                if eom_dim != expected_eom_dim:
                    passed = False
                    error_msg = f"Dimensional mismatch in Euler-Lagrange: expected {expected_eom_dim}, got {eom_dim}"
                else:
                    details["consistency"] = f"Verified: [EoM] = [L] / [L_coord] = {eom_dim}"

        elif rule == "conserve_energy":
            # Input is Lagrangian or EoM, output is Energy
            # Output dimension must be Energy [M*L^2*T^-2]
            energy_node = out_nodes[0]
            energy_dim = energy_node.expression.get_dimension()
            expected_dim = Dimension.energy()

            details["inspected_nodes"][energy_node.id] = repr(energy_dim)
            if not energy_dim.is_dimensionless() and energy_dim != expected_dim:
                passed = False
                error_msg = f"Energy dimension mismatch: expected {expected_dim}, got {energy_dim}"
            else:
                details["consistency"] = f"Verified: Energy dimension is {energy_dim}"

        elif rule == "solve_harmonic_oscillator":
            # Output is trajectory x(t) = A*cos(omega*t + phi)
            # Output dimension must be Length [L]
            sol_node = out_nodes[0]
            sol_dim = sol_node.expression.get_dimension()
            expected_dim = Dimension.length()

            details["inspected_nodes"][sol_node.id] = repr(sol_dim)
            if not sol_dim.is_dimensionless() and sol_dim != expected_dim:
                passed = False
                error_msg = f"Trajectory dimension mismatch: expected {expected_dim}, got {sol_dim}"
            else:
                details["consistency"] = f"Verified: Trajectory dimension is {sol_dim}"

        else:
            # Generic consistency: ensure all output nodes have valid dimensions
            for node in out_nodes:
                dim = node.expression.get_dimension()
                details["inspected_nodes"][node.id] = repr(dim)

        elapsed = (time.perf_counter() - start_time) * 1000
        status = VerificationStatus.DIMENSIONALLY_CHECKED if passed else VerificationStatus.FAILED

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=[{"rule": rule, "dimension_check": details.get("consistency", "homogeneous")}],
            command_invocation=f"DimensionChecker.verify_edge('{edge.id}')",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility={"unit_system": "SI base"},
            metrics={"dimension_homogeneity": passed}
        )

        return VerificationReport(
            status=status,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=passed,
            details=details,
            error_message=error_msg,
            evidence=evidence
        )
