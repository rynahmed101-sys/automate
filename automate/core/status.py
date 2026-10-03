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

    # Step has not yet been subjected to any verification backend
    UNVERIFIED = "UNVERIFIED"

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

    @property
    def is_verified(self) -> bool:
        """True if the node has passed at least one mathematical verification check."""
        return self in {
            VerificationStatus.SYMBOLIC_CHECKED,
            VerificationStatus.NUMERICALLY_CHECKED,
            VerificationStatus.STATISTICALLY_CHECKED,
            VerificationStatus.FORMALLY_PROVED,
        }

    @property
    def rank(self) -> int:
        """Ordinal rank of verification strength for visual sorting."""
        ranks = {
            VerificationStatus.FAILED: 0,
            VerificationStatus.UNVERIFIED: 1,
            VerificationStatus.PARSED: 2,
            VerificationStatus.CONDITIONAL: 3,
            VerificationStatus.STATISTICALLY_CHECKED: 4,
            VerificationStatus.NUMERICALLY_CHECKED: 5,
            VerificationStatus.SYMBOLIC_CHECKED: 6,
            VerificationStatus.FORMALLY_PROVED: 7,
        }
        return ranks.get(self, 0)
