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

    # 4. Verification backend validation
    allowed_checkers = {"sympy", "lean4", "numerical", "statistical", "dimension", "tensor"}
    if proposal_target := raw_proposal.get("target_checker"):
        if proposal_target not in allowed_checkers:
            errors.append(
                f"Unknown verification backend '{proposal_target}'. "
                f"Must be one of: {', '.join(sorted(allowed_checkers))}."
            )

    # 4. Semantic rule validation against RuleRegistry
    registry = rule_registry or RuleRegistry()
    rule_def = registry.get(proposal.rule)
    if rule_def:
        allowed_for_rule = rule_def.allowed_checkers()
        if proposal.target_checker not in allowed_for_rule:
            errors.append(
                f"Checker '{proposal.target_checker}' cannot verify rule '{proposal.rule}'. "
                f"Allowed checkers: {', '.join(allowed_for_rule)}."
            )
    if not rule_def:
        errors.append(
            f"Unknown transformation rule '{proposal.rule}'. "
            f"Must be one of approved rules: {', '.join(sorted(registry.list_rule_ids()))}."
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
