"""
Security Validation & Sanitization for Untrusted AI Proposals.
Invariants:
- Never execute eval(), exec(), or arbitrary code.
- Prevent shell injection, path traversal, and secret leakage.
- Enforce strict automate.proposal.v1 schema compliance.
- Validate symbol legality and input node existence before graph mutation.
"""

from typing import Dict, Any, List, Tuple, Optional
import re
from pydantic import ValidationError
from automate.ai.schemas import DerivationProposal
from automate.core.graph import DerivationGraph
from automate.theory.rules import RuleRegistry
from automate.ir.safe_parser import SafeParser, SafeParseError

# Patterns indicative of malicious code or injection attempts
DANGEROUS_PATTERNS = [
    r"__import__",
    r"subprocess",
    r"os\.system",
    r"shutil",
    r"eval\s*\(",
    r"exec\s*\(",
    r"open\s*\(",
    r"read_bytes",
    r"write_bytes",
    r"unlink",
    r"remove",
    r"\.\./",
    r"\.\.\\",
    r";\s*rm\s",
    r";\s*del\s",
    r"`.*`",
    r"\$\(.*\)",
    r"powershell",
    r"/bin/sh",
    r"/bin/bash",
    r"cmd\.exe",
    r"apiKey",
    r"OPENAI_API_KEY",
    r"ghp_"
]

COMPILED_DANGEROUS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]
MAX_PROPOSAL_SIZE_BYTES = 64 * 1024  # 64 KB limit to prevent DoS via giant payload
MAX_EXPRESSION_PARSE_SECONDS = 2.0


class ProposalValidationResult:
    def __init__(self, is_valid: bool, proposal: Optional[DerivationProposal] = None, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.proposal = proposal
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "proposal_id": self.proposal.proposal_id if self.proposal else None,
            "errors": self.errors
        }


def validate_ai_proposal(
    raw_proposal: Any,
    graph: Optional[DerivationGraph] = None,
    rule_registry: Optional[RuleRegistry] = None
) -> ProposalValidationResult:
    """
    Strictly validates and sanitizes an untrusted AI proposal.
    Returns ProposalValidationResult with detailed diagnostics.
    """
    errors: List[str] = []

    # 1. Payload type and size bounds
    if not isinstance(raw_proposal, dict):
        return ProposalValidationResult(False, None, ["Proposal must be a JSON object dictionary."])

    import json
    try:
        dumped = json.dumps(raw_proposal)
    except Exception as e:
        return ProposalValidationResult(False, None, [f"Proposal is not serializable JSON: {e}"])

    if len(dumped.encode("utf-8")) > MAX_PROPOSAL_SIZE_BYTES:
        return ProposalValidationResult(
            False, None,
            [f"Proposal exceeds maximum allowed size of {MAX_PROPOSAL_SIZE_BYTES} bytes."]
        )

    # 2. Security scan against malicious patterns
    for pat in COMPILED_DANGEROUS:
        if pat.search(dumped):
            return ProposalValidationResult(
                False, None,
                [f"Security violation: Proposal contains disallowed pattern '{pat.pattern}'."]
            )

    # 3. Check that proposal does not attempt to assign forbidden verification statuses
    raw_status = raw_proposal.get("status")
    if raw_status and raw_status in ("FORMALLY_PROVED", "SYMBOLIC_CHECKED", "NUMERICALLY_CHECKED", "STATISTICALLY_CHECKED", "VERIFIED"):
        return ProposalValidationResult(
            False, None,
            [f"Forbidden: AI proposal cannot self-assign status '{raw_status}'. "
             "All AI proposals are assigned 'AI_PROPOSED' until evaluated by backends."]
        )

    # 4. Pydantic schema validation (automate.proposal.v1)
    try:
        proposal = DerivationProposal(**raw_proposal)
    except ValidationError as ve:
        schema_errs = [f"{e['loc']}: {e['msg']}" for e in ve.errors()]
        return ProposalValidationResult(False, None, [f"Schema validation error: {'; '.join(schema_errs)}"])

    # 4. Semantic rule/checker validation against RuleRegistry
    # Keep checker identity validation separate from rule capability validation:
    # an unknown checker must be reported as unknown rather than as a
    # rule/checker compatibility error.
    registry = rule_registry or RuleRegistry()
    rule_def = registry.get(proposal.rule)
    if not rule_def:
        errors.append(
            f"Unknown transformation rule '{proposal.rule}'. "
            f"Must be one of approved rules: {', '.join(sorted(registry.list_rule_ids()))}."
        )
    else:
        checker_name = proposal.target_checker
        known_checkers = {"sympy", "lean4", "numerical", "statistical", "dimension", "tensor", "linear_algebra"}
        if not isinstance(checker_name, str) or not checker_name.strip():
            errors.append("A non-empty target_checker is required.")
        elif checker_name not in known_checkers:
            errors.append(
                f"Unknown checker '{checker_name}'. "
                f"Must be one of: {', '.join(sorted(known_checkers))}. "
                "No fallback to a different checker is permitted."
            )
        elif checker_name not in rule_def.allowed_checkers:
            errors.append(
                f"Checker '{checker_name}' is not allowed for rule '{proposal.rule}'. "
                f"Allowed semantic checkers: {', '.join(rule_def.allowed_checkers) or 'none'}."
            )

    # 5. Graph dependency validation (if graph is provided)
    if graph:
        for in_id in proposal.input_nodes:
            if in_id not in graph.nodes:
                errors.append(f"Referenced input node '{in_id}' does not exist in derivation graph.")

        for out_node in proposal.output_nodes:
            if out_node.id in graph.nodes:
                errors.append(f"Proposed output node ID '{out_node.id}' already exists in derivation graph.")

            # Validate basic expression string non-emptiness
            if not out_node.expression or not out_node.expression.strip():
                errors.append(f"Proposed output node '{out_node.id}' has empty expression.")

    # 6. Parse proposed mathematical output in an isolated process before any
    # semantic backend sees it. This provides a killable wall-clock boundary for
    # untrusted AI-generated expressions/equations.
    parser = SafeParser(max_seconds=MAX_EXPRESSION_PARSE_SECONDS)
    for out_node in proposal.output_nodes:
        try:
            if proposal.rule in {
                "vector_add", "vector_subtract", "vector_scalar_multiply", "vector_dot",
                "matrix_multiply", "matrix_transpose", "matrix_determinant", "matrix_trace",
                "matrix_inverse", "matrix_rank", "matrix_rref", "matrix_eigenvalues",
                "matrix_eigenvector", "matrix_characteristic_polynomial", "matrix_diagonalize", "linear_system_solve",
            }:
                from automate.ir.linear_algebra import parse_linear_algebra_expression
                parse_linear_algebra_expression(out_node.expression)
            elif "=" in out_node.expression and "==" not in out_node.expression:
                parser.parse_equation_isolated(
                    out_node.expression,
                    timeout=MAX_EXPRESSION_PARSE_SECONDS,
                )
            else:
                parser.parse_isolated(
                    out_node.expression,
                    timeout=MAX_EXPRESSION_PARSE_SECONDS,
                )
        except SafeParseError as exc:
            errors.append(
                f"Unsafe mathematical expression in proposed output node "
                f"'{out_node.id}': {exc}"
            )

    # 6. Check that proposal does not attempt to assign forbidden verification statuses
    raw_status = raw_proposal.get("status")
    if raw_status and raw_status in ("FORMALLY_PROVED", "SYMBOLIC_CHECKED", "NUMERICALLY_CHECKED", "STATISTICALLY_CHECKED", "VERIFIED"):
        errors.append(
            f"Forbidden: AI proposal cannot self-assign status '{raw_status}'. "
            "All AI proposals are assigned 'AI_PROPOSED' until evaluated by backends."
        )

    is_valid = len(errors) == 0
    return ProposalValidationResult(
        is_valid=is_valid,
        proposal=proposal if is_valid else None,
        errors=errors
    )
