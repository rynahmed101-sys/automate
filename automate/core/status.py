"""
Verification status enumeration and taxonomy for Automate.
"""

from enum import Enum


class VerificationStatus(str, Enum):
    """
    Verification status of a derivation step or node.
    Strictly distinguishes formal proofs, symbolic checks, numerical validations,
    and statistical inferences.
    """
    # Expression has been successfully parsed into canonical IR
    PARSED = "PARSED"

    # Graph structure, acyclicity, and identifier integrity validated
    STRUCTURALLY_VALID = "STRUCTURALLY_VALID"

    # Dimensional homogeneity verified across base SI dimensions
    DIMENSIONALLY_CHECKED = "DIMENSIONALLY_CHECKED"

    # Step has not yet been subjected to any verification backend
    UNVERIFIED = "UNVERIFIED"

    # Tensor-index structure verified under Einstein summation semantics
    TENSOR_CHECKED = "TENSOR_CHECKED"

    # Verified algebraically or via computer algebra calculus (e.g. SymPy)
    SYMBOLIC_CHECKED = "SYMBOLIC_CHECKED"

    # Tested against numerical integration, simulation, or error bounds (e.g. SciPy)
    NUMERICALLY_CHECKED = "NUMERICALLY_CHECKED"

    # Tested against empirical/synthetic data with parameter estimation/residuals
    STATISTICALLY_CHECKED = "STATISTICALLY_CHECKED"

    # Formally verified using a sound interactive theorem prover (e.g. Lean 4)
    FORMALLY_PROVED = "FORMALLY_PROVED"

    # Dependent upon unproven or active assumptions/approximations
    CONDITIONAL = "CONDITIONAL"

    # Verification failed (algebraic contradiction, formal proof failure, etc.)
    FAILED = "FAILED"

    # Step mathematically disproved or counterexample discovered
    DISPROVED = "DISPROVED"

    # Verification exceeded resource or timeout limits
    TIMEOUT = "TIMEOUT"

    # Step not applicable for formal check
    NOT_APPLICABLE = "NOT_APPLICABLE"

    # Step or hypothesis proposed by an AI agent (unverified proposal)
    AI_PROPOSED = "AI_PROPOSED"

    @property
    def is_verified(self) -> bool:
        """True if the node has passed at least one mathematical verification check."""
        return self in {
            VerificationStatus.DIMENSIONALLY_CHECKED,
            VerificationStatus.SYMBOLIC_CHECKED,
            VerificationStatus.TENSOR_CHECKED,
            VerificationStatus.NUMERICALLY_CHECKED,
            VerificationStatus.STATISTICALLY_CHECKED,
            VerificationStatus.FORMALLY_PROVED,
        }

    @property
    def rank(self) -> int:
        """Ordinal rank of verification strength for visual sorting."""
        ranks = {
            VerificationStatus.FAILED: 0,
            VerificationStatus.AI_PROPOSED: 1,
            VerificationStatus.UNVERIFIED: 1,
            VerificationStatus.PARSED: 2,
            VerificationStatus.STRUCTURALLY_VALID: 3,
            VerificationStatus.CONDITIONAL: 4,
            VerificationStatus.DIMENSIONALLY_CHECKED: 5,
            VerificationStatus.STATISTICALLY_CHECKED: 7,
            VerificationStatus.TENSOR_CHECKED: 8,
            VerificationStatus.NUMERICALLY_CHECKED: 9,
            VerificationStatus.SYMBOLIC_CHECKED: 10,
            VerificationStatus.FORMALLY_PROVED: 11,
        }
        return ranks.get(self, 0)
