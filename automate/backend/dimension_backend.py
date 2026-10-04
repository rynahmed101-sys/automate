"""
DimensionChecker: Verifies physical dimensional consistency across expressions,
equations, derivatives, and transformations.

The coordinate dimension is no longer hardcoded to Length. Instead it is read from:
The coordinate dimension is read from edge.parameters['coordinate_dimension'].

Supported explicit values:
  - 'length'       → Dimension.length()
  - 'angle'        → Dimension.dimensionless()   (radians are dimensionless)
  - 'dimensionless'→ Dimension.dimensionless()
  - 'action'       → Dimension.action()

Unknown coordinate dimensions are rejected rather than treated as dimensionless.
"""

import time
from typing import Dict, Any, List
from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.ir.dimensions import Dimension


def _require_explicit_dimension(node: Any, role: str) -> Optional[str]:
    """Return a failure message when applicable dimension metadata is missing."""
    expression = getattr(node, "expression", None)
    if expression is None or not getattr(expression, "has_explicit_dimension", False):
        return (
            f"Missing physical dimension metadata for {role}. "
            "Use an explicit dimension such as 'L', 'M*L^2*T^-2', "
            "or 'dimensionless'/'1'."
        )
    return None


def _resolve_coordinate_dimension(coord_dim_str: str) -> Dimension:
    """Map a declared coordinate-dimension descriptor to a Dimension object."""
    mapping = {
        "length": Dimension.length,
        "angle": Dimension.dimensionless,
        "dimensionless": Dimension.dimensionless,
        "action": Dimension.action,
    }
    try:
        factory = mapping[coord_dim_str]
    except KeyError as exc:
        raise ValueError(
            f"Unknown coordinate_dimension '{coord_dim_str}'. "
            f"Expected one of: {', '.join(sorted(mapping))}."
        ) from exc
    return factory()


class DimensionChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "DimensionChecker"

    @property
    def version(self) -> str:
        return "1.0.1"

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

        rule = edge.transformation_rule
        passed = True
        error_msg = None

        try:
            if rule == "euler_lagrange":
                passed, error_msg, details = self._check_euler_lagrange(
                    in_nodes, out_nodes, edge.parameters, details
                )

            elif rule == "conserve_energy":
                # Output dimension must be Energy [M·L²·T⁻²]
                energy_node = out_nodes[0]
                missing = _require_explicit_dimension(energy_node, "energy output")
                if missing:
                    return False, f"UNSUPPORTED: {missing}", details

                energy_dim = energy_node.expression.get_dimension()
                expected_dim = Dimension.energy()

                details["inspected_nodes"][energy_node.id] = repr(energy_dim)
                if energy_dim != expected_dim:
                    passed = False
                    error_msg = (
                        f"Energy dimension mismatch: expected {expected_dim}, got {energy_dim}"
                    )
                else:
                    details["consistency"] = f"Verified: Energy dimension is {energy_dim}"

            elif rule == "solve_harmonic_oscillator":
                # Output should have same dimension as coordinate
                sol_node = out_nodes[0]
                missing = _require_explicit_dimension(sol_node, "trajectory output")
                if missing:
                    return False, f"UNSUPPORTED: {missing}", details

                sol_dim = sol_node.expression.get_dimension()

                # Coordinate dimension from parameters
                coord_dim_str = edge.parameters.get("coordinate_dimension", "length")
                expected_dim = _resolve_coordinate_dimension(coord_dim_str)

                details["inspected_nodes"][sol_node.id] = repr(sol_dim)
                details["coordinate_dimension_used"] = coord_dim_str
                if sol_dim != expected_dim:
                    passed = False
                    error_msg = (
                        f"Trajectory dimension mismatch: expected {expected_dim}, "
                        f"got {sol_dim}"
                    )
                else:
                    details["consistency"] = (
                        f"Verified: Trajectory dimension is {sol_dim}"
                    )

            else:
                # Generic consistency: ensure all output nodes have valid dimensions
                for node in out_nodes:
                    dim = node.expression.get_dimension()
                    details["inspected_nodes"][node.id] = repr(dim)

        except (ValueError, TypeError) as exc:
            passed = False
            error_msg = f"UNSUPPORTED: invalid dimensional metadata: {exc}"

        elapsed = (time.perf_counter() - start_time) * 1000
        status = (
            VerificationStatus.DIMENSIONALLY_CHECKED
            if passed else VerificationStatus.FAILED
        )

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(
                graph.compute_inherited_assumptions(edge.input_nodes[0])
            ) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=[{
                "rule": rule,
                "dimension_check": details.get("consistency", "homogeneous")
            }],
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

    def _check_euler_lagrange(
        self, in_nodes, out_nodes, params: Dict[str, Any], details: Dict[str, Any]
    ):
        """
        Checks [EoM] == [Lagrangian] / [coordinate_dimension].

        coordinate_dimension defaults to 'length' but can be overridden:
          - 'angle'        → dimensionless (pendulum θ)
          - 'dimensionless'→ dimensionless
          - 'length'       → SI length
        """
        passed = True
        error_msg = None

        lagr_node = in_nodes[0]
        eom_node = out_nodes[0]

        missing_lagr = _require_explicit_dimension(lagr_node, "Lagrangian input")
        missing_eom = _require_explicit_dimension(eom_node, "equation-of-motion output")
        if missing_lagr or missing_eom:
            missing = missing_lagr or missing_eom
            return False, f"UNSUPPORTED: {missing}", details

        lagr_dim = lagr_node.expression.get_dimension()
        eom_dim = eom_node.expression.get_dimension()

        details["inspected_nodes"][lagr_node.id] = repr(lagr_dim)
        details["inspected_nodes"][eom_node.id] = repr(eom_dim)

        # Read coordinate dimension from edge parameters
        coord_dim_str = params.get("coordinate_dimension", "length")
        coord_dim = _resolve_coordinate_dimension(coord_dim_str)
        details["coordinate_dimension_used"] = coord_dim_str

        # Explicit dimensionless metadata is valid and is not the same as missing metadata.
        # For dimensionless coordinates (angles), [EoM] = [Lagrangian] / [1] = [Lagrangian]
        if coord_dim.is_dimensionless():
            expected_eom_dim = lagr_dim
        else:
            expected_eom_dim = lagr_dim / coord_dim

        if eom_dim != expected_eom_dim:
            passed = False
            error_msg = (
                f"Dimensional mismatch in Euler-Lagrange: "
                f"expected [EoM] = {expected_eom_dim} "
                f"(Lagrangian {lagr_dim} / coord {coord_dim}), "
                f"got {eom_dim}"
            )
        else:
            details["consistency"] = (
                f"Verified: [EoM] = [L] / [coord] = "
                f"{lagr_dim} / {coord_dim} = {eom_dim}"
            )

        return passed, error_msg, details
