"""
TensorChecker: structural Einstein-index verification backend.

This backend deliberately verifies index algebra, not numerical tensor component
values. It consumes structured tensor-index parameters produced by an AI agent
and checks contractions, sums, equations, and index raising/lowering.
"""

import time
from typing import Any, Dict, List, Optional

from automate.backend.base import BaseChecker, VerificationReport, VerificationEvidence
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus
from automate.ir.tensors import (
    TensorIndex,
    validate_einstein_product,
    validate_tensor_sum,
    validate_tensor_equation,
)


class TensorChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "TensorChecker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _indices(value: Any, field_name: str) -> List[TensorIndex]:
        if not isinstance(value, list):
            raise ValueError(f"{field_name} must be a list of tensor-index objects.")
        result: List[TensorIndex] = []
        for item in value:
            if isinstance(item, TensorIndex):
                result.append(item)
            elif isinstance(item, dict):
                result.append(TensorIndex.model_validate(item))
            else:
                raise ValueError(f"{field_name} contains an invalid tensor index: {item!r}")
        return result

    @staticmethod
    def _result(
        edge: DerivationEdge,
        graph: DerivationGraph,
        passed: bool,
        details: Dict[str, Any],
        error: Optional[str],
        elapsed: float,
        steps: List[Dict[str, Any]],
    ) -> VerificationReport:
        status = VerificationStatus.SYMBOLIC_CHECKED if passed else VerificationStatus.FAILED
        evidence = VerificationEvidence(
            backend="TensorChecker",
            backend_version="1.0.0",
            graph_id=graph.id,
            edge_id=edge.id,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(
                graph.compute_inherited_assumptions(edge.input_nodes[0])
            ) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations or [{
                "rule": edge.transformation_rule,
                "index_structure": details.get("index_structure", "not supplied"),
            }],
            command_invocation=f"TensorChecker.verify_edge('{edge.id}')",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility={"index_semantics": "Einstein", "backend_version": "1.0.0"},
            metrics={"index_structure_valid": passed},
        )
        edge.status = status
        edge.checker = "tensor"
        edge.evidence = evidence.to_dict()
        if not passed:
            edge.failed_reason = error
        else:
            edge.certificate = DerivationCertificate(
                rule_name=edge.transformation_rule,
                steps=steps,
                backend_version="TensorChecker 1.0.0",
                execution_time_ms=elapsed,
                metrics={"index_structure_valid": True},
            )
        return VerificationReport(
            status=status,
            backend="TensorChecker",
            backend_version="1.0.0",
            execution_time_ms=elapsed,
            passed=passed,
            details=details,
            error_message=error,
            certificates=steps,
            evidence=evidence,
        )

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start = time.perf_counter()

        try:
            referenced_ids = edge.input_nodes + edge.output_nodes
            if any(graph.get_node(node_id) is None for node_id in referenced_ids):
                return self._result(
                    edge,
                    graph,
                    False,
                    {"rule": edge.transformation_rule},
                    "Referenced nodes missing from derivation graph.",
                    (time.perf_counter() - start) * 1000,
                    [],
                )

            rule = edge.transformation_rule
            if rule == "index_contract":
                indices = self._indices(edge.parameters.get("indices"), "indices")
                result = validate_einstein_product(indices)
                details = {
                    "rule": rule,
                    "index_structure": [i.model_dump() for i in indices],
                    "free_indices": [i.model_dump() for i in result.free_indices],
                    "dummy_indices": result.dummy_indices,
                    "resultant_rank": result.resultant_rank,
                    "validation": result.model_dump(),
                }
                error = "; ".join(result.errors) if result.errors else None
                steps = [{
                    "step": 1,
                    "operation": "validate_einstein_product",
                    "resultant_rank": result.resultant_rank,
                    "dummy_indices": result.dummy_indices,
                }]

            elif rule in {"tensor_sum", "index_sum"}:
                terms = edge.parameters.get("terms_indices")
                if terms is None:
                    raise ValueError("tensor_sum requires 'terms_indices'.")
                parsed_terms = [self._indices(v, f"terms_indices[{i}]") for i, v in enumerate(terms)]
                result = validate_tensor_sum(parsed_terms)
                details = {
                    "rule": rule,
                    "terms": [[i.model_dump() for i in t] for t in parsed_terms],
                    "resultant_rank": result.resultant_rank,
                    "free_indices": [i.model_dump() for i in result.free_indices],
                    "validation": result.model_dump(),
                }
                error = "; ".join(result.errors) if result.errors else None
                steps = [{
                    "step": 1,
                    "operation": "validate_tensor_sum",
                    "resultant_rank": result.resultant_rank,
                }]

            elif rule in {"tensor_equation", "index_equation"}:
                lhs = self._indices(edge.parameters.get("lhs_indices"), "lhs_indices")
                rhs = self._indices(edge.parameters.get("rhs_indices"), "rhs_indices")
                result = validate_tensor_equation(lhs, rhs)
                details = {
                    "rule": rule,
                    "lhs_indices": [i.model_dump() for i in lhs],
                    "rhs_indices": [i.model_dump() for i in rhs],
                    "resultant_rank": result.resultant_rank,
                    "free_indices": [i.model_dump() for i in result.free_indices],
                    "validation": result.model_dump(),
                }
                error = "; ".join(result.errors) if result.errors else None
                steps = [{
                    "step": 1,
                    "operation": "validate_tensor_equation",
                    "resultant_rank": result.resultant_rank,
                }]

            elif rule in {"raise_index", "lower_index"}:
                source = self._indices(edge.parameters.get("source_indices"), "source_indices")
                result_indices = self._indices(
                    edge.parameters.get("result_indices"), "result_indices"
                )
                target = str(edge.parameters.get("index", ""))
                if not target:
                    raise ValueError("Index raising/lowering requires parameter 'index'.")

                source_map = {i.symbol: i for i in source}
                result_map = {i.symbol: i for i in result_indices}
                if target not in source_map or target not in result_map:
                    raise ValueError(f"Target index '{target}' must appear in both source and result.")
                expected = "upper" if rule == "raise_index" else "lower"
                forbidden = "lower" if rule == "raise_index" else "upper"
                if source_map[target].position != forbidden or result_map[target].position != expected:
                    return self._result(
                        edge, graph, False,
                        {"rule": rule, "target_index": target,
                         "source_position": source_map[target].position,
                         "result_position": result_map[target].position},
                        f"{rule} requires '{target}' to change from {forbidden} to {expected}.",
                        (time.perf_counter() - start) * 1000, [],
                    )

                source_free = [(i.symbol, i.position) for i in source]
                result_free = [(i.symbol, i.position) for i in result_indices]
                source_without = [(s, p) for s, p in source_free if s != target]
                result_without = [(s, p) for s, p in result_free if s != target]
                passed = source_without == result_without
                details = {
                    "rule": rule,
                    "target_index": target,
                    "source_indices": source_free,
                    "result_indices": result_free,
                    "only_target_variance_changed": passed,
                }
                error = None if passed else "Raising/lowering changed indices other than the target index."
                steps = [{
                    "step": 1,
                    "operation": rule,
                    "target_index": target,
                    "from": source_map[target].position,
                    "to": result_map[target].position,
                }]
            else:
                return self._result(
                    edge, graph, False, {"rule": rule}, 
                    f"Unsupported tensor transformation rule: {rule}",
                    (time.perf_counter() - start) * 1000, [],
                )

            return self._result(
                edge, graph,
                result.is_valid if "result" in locals() else passed,
                details, error, (time.perf_counter() - start) * 1000, steps
            )
        except Exception as exc:
            return self._result(
                edge, graph, False, {"rule": edge.transformation_rule},
                f"Tensor verification error: {type(exc).__name__}: {exc}",
                (time.perf_counter() - start) * 1000, [],
            )
