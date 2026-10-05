"""
Deterministic Mock LLM Provider for offline integration testing and reproducible AI loops.
Requires no external network connection, no cloud accounts, and no API keys.
"""

from typing import Dict, Any, Optional
import uuid
from automate.ai.base import LLMProvider
from automate.ai.schemas import DerivationProposal, CandidateNode, ProposalOrigin


class MockLLMProvider(LLMProvider):
    """
    Deterministic provider producing structured mathematical proposals.
    """

    def __init__(self, model_name: str = "mock-physicist-v1"):
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def propose(
        self,
        context: Dict[str, Any],
        request: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a valid DerivationProposal dictionary based on context and request.
        """
        req_lower = request.lower()

        # Case 1: Solve harmonic oscillator
        if "solve" in req_lower or "solution" in req_lower or "harmonic" in req_lower:
            input_nodes = ["node_eom"] if "node_eom" in [n.get("id") for n in context.get("nodes", [])] else []
            if not input_nodes and context.get("nodes"):
                input_nodes = [context["nodes"][0]["id"]]

            proposal = DerivationProposal(
                proposal_id=f"mock_prop_{uuid.uuid4().hex[:6]}",
                proposal_type="derivation",
                input_nodes=input_nodes,
                output_nodes=[
                    CandidateNode(
                        id="node_ai_solution",
                        expression="x(t) = A * cos(omega * t + phi)",
                        dimension="L",
                        latex="x(t) = A\\cos(\\omega t + \\phi)",
                        node_kind="equation",
                        domain=context.get("domain", "classical_mechanics")
                    )
                ],
                rule="solve_harmonic_oscillator",
                justification="Linear homogeneous 2nd order ordinary differential equation general ansatz",
                side_conditions=["asm_pos_mass", "asm_pos_k"],
                target_checker="sympy",
                parameters={
                    "omega": "sqrt(k/m)",
                    "coordinates": ["x"],
                    "parameters": {"m": "positive", "k": "positive"},
                },
                origin=ProposalOrigin(
                    type="ai",
                    provider=self.name,
                    model=self._model_name,
                    context_hash=context.get("graph_hash")
                )
            )
            return proposal.to_dict()

        # Case 2: Counterexample proposal
        elif "counterexample" in req_lower or "disprove" in req_lower:
            proposal = DerivationProposal(
                proposal_id=f"mock_counter_{uuid.uuid4().hex[:6]}",
                proposal_type="counterexample",
                input_nodes=[n["id"] for n in context.get("nodes", [])[:1]],
                output_nodes=[
                    CandidateNode(
                        id="node_counterexample_candidate",
                        expression="m = -1.0 kg",
                        dimension="M",
                        node_kind="parameter",
                        domain=context.get("domain", "classical_mechanics")
                    )
                ],
                rule="algebraic_identity",
                justification="Probing stability boundary at negative inertial mass",
                proposed_assumptions=[{
                    "id": "asm_neg_mass_test",
                    "description": "Negative mass test condition",
                    "formal_predicate": "m < 0",
                    "category": "approximation"
                }],
                target_checker="sympy",
                origin=ProposalOrigin(
                    type="ai",
                    provider=self.name,
                    model=self._model_name,
                    context_hash=context.get("graph_hash")
                )
            )
            return proposal.to_dict()

        # Default: Algebraic identity simplification
        input_nodes = [context["nodes"][0]["id"]] if context.get("nodes") else []
        proposal = DerivationProposal(
            proposal_id=f"mock_step_{uuid.uuid4().hex[:6]}",
            proposal_type="derivation",
            input_nodes=input_nodes,
            output_nodes=[
                CandidateNode(
                    id="node_ai_derived",
                    expression="x_dot_dot + (k/m) * x = 0",
                    dimension="L*T^-2",
                    node_kind="equation",
                    domain=context.get("domain", "classical_mechanics")
                )
            ],
            rule="divide_both_sides",
            justification="Divide equation by non-zero mass parameter m",
            side_conditions=["asm_pos_mass"],
            target_checker="sympy",
            parameters={"divisor": "m"},
            origin=ProposalOrigin(
                type="ai",
                provider=self.name,
                model=self._model_name,
                context_hash=context.get("graph_hash")
            )
        )
        return proposal.to_dict()
