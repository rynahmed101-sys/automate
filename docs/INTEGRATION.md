# Integration Techniques

Stage 1B exposes explicit symbolic verification rules for common integration techniques. These rules are transformation-aware: SymPy is used as a symbolic backend, but a backend-generated antiderivative is not by itself sufficient evidence for a PASS.

## Rules

### integration_by_substitution

Parameters: variable, substitution_variable, substitution_expression, transformed_integrand.

The verifier computes du/dx, restores the differential factor, and checks the represented transformed integrand against the original integrand. It also differentiates the proposed antiderivative against the original integrand.

An identically zero du/dx, missing required fields, unsafe expressions, or an established mismatch fails closed. Symbolic equality that cannot be established is UNVERIFIED. The verifier does not infer global one-to-one invertibility from a symbolic substitution.

### integration_by_parts

Parameters: variable, u, dv, v.

The verifier checks dv = d(v)/dx, checks that the input integrand is u*dv, and constructs the explicit relation integral(u dv) = u*v - integral(v du). The proposed result is accepted when it differs from the represented integration-by-parts result by a constant, implemented by differentiating their difference.

### partial_fractions_integrate

Parameters: variable, decomposition.

The input must be a nontrivial rational function of the integration variable. The proposed decomposition is checked against the original rational function and against the backend's canonical apart representation. The proposed antiderivative is then differentiated against the original integrand.

The verifier records the original denominator as a domain restriction q(x) != 0. It does not erase poles merely because algebraic cancellation is possible in a transformed expression. A zero denominator, malformed decomposition, or incorrect candidate fails closed.

### trigonometric_integrate

This is a deliberately scoped tractable path for common trigonometric and hyperbolic forms. It uses SymPy manual integration as backend evidence and independently differentiates both the backend primitive and the proposed candidate.

Supported input must actually contain one of the supported trigonometric or hyperbolic functions. If the backend leaves the integral unevaluated, the result is UNVERIFIED, not a failure or success.

## General integration

The existing integrate rule remains the general scalar integration primitive. It already supports common rational, exponential, and trigonometric forms where SymPy can produce a symbolic result. Its candidate is differentiated back to the original integrand for indefinite integration. The new technique rules make the requested transformation explicit rather than hiding it behind a final integrate() call.

## Verification status

- PASS / SYMBOLIC_CHECKED: the represented transformation and candidate result were symbolically verified.
- FAIL / FAILED: a malformed input, invalid structural condition, or demonstrably incorrect mathematical result was established.
- UNVERIFIED: symbolic computation or equality could not establish the claim. Numerical sampling is not promoted to proof.

## Domain and assumptions

The calculus verifier operates on expressions accepted by SafeParser. Domain restrictions are recorded when they are explicit in the rational denominator. Symbolic branch, logarithm, root, and global substitution-domain questions are not silently resolved. When the represented algebraic or differential identity is sufficient for the stated local antiderivative relation, the verifier does not manufacture a stronger global theorem.

## Backend basis

The implementation follows the repository's existing rule, IR, and checker boundary and uses SymPy only as the symbolic computation backend. SymPy documents integrate() for definite and indefinite integration, manual integration for tractable hand-like integration, and apart() for rational partial-fraction decomposition. Automate adds its own representation, validation, residual checks, and fail-closed status semantics.

Roadmap status remains a reconciliation responsibility of the primary agent; this PR does not modify the authoritative phase ledger.