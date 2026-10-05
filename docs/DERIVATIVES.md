# Derivatives and Higher-Order Derivatives

Automate's Stage 1B derivative primitive verifies scalar symbolic derivatives with an explicit differentiation variable and arbitrary positive integer derivative order.

## Representation

A differentiate edge has one scalar expression input and one scalar derivative output.

- variable: explicit differentiation variable; wrt is accepted as a compatibility alias.
- order: positive integer derivative order; defaults to 1.
- assumptions: optional explicit SafeParser/SymPy assumptions (real, positive, negative, nonzero, integer).

The same rule handles first and higher derivatives. There is no hard-coded first/second/third-order feature and no arbitrary mathematical order ceiling in the rule semantics.

## Verification

The checker parses source and claimed derivative through SafeParser, computes the expected derivative with SymPy, and compares the claim by symbolic simplification.

- An established mismatch is FAILED.
- If symbolic comparison cannot establish equality, the result is UNVERIFIED.
- Numerical sampling is not used as proof.

The existing differentiate_both_sides rule remains the equation-level transformation primitive. differentiate operates on a scalar expression and is reusable by later calculus capabilities.

## Domains and singularities

The verifier records best-effort real-domain metadata for the source and derivative expressions. Domain analysis is evidence and does not turn an unresolved domain question into success.

For example, differentiating 1/x produces -1/x**2 while retaining the singularity at x=0.

Pointwise differentiability at a specified target, one-sided derivatives, and multivariable partial derivatives are intentionally separate capabilities and are not claimed here.

## Fail-closed behavior

Malformed variables, invalid orders, unsupported assumptions, unsafe expressions, and incorrect derivative claims fail closed. Symbolic comparisons that remain undecidable become UNVERIFIED.

## Research basis

SymPy's differentiation machinery is used only as the symbolic backend; Automate retains its own rule, input contract, evidence, and failure semantics. No external source code is copied.

Roadmap status is intentionally unchanged; implementation and CI are not certification.


## Explicit composite differentiation

The Stage 1B calculus layer also exposes dedicated verification rules for:
- `chain_rule`: verifies an explicit composition using (f'(g(x))g'(x));
- `product_rule`: verifies the product rule for two or more factors;
- `quotient_rule`: verifies the quotient rule for a numerator and denominator.

These rules construct the mathematical derivative from the named components and compare the proposed result. They are deliberately separate from generic `differentiate`, so an agent can state the intended calculus transformation rather than hiding it inside a final derivative.

## Implicit differentiation

`implicit_differentiate` verifies a proposed (dy/dx) from an explicit relation (F(x,y)=0) using

[
\frac{dy}{dx}=-\frac{F_x}{F_y}.
]

The verifier rejects an identically zero (F_y) denominator and otherwise records the local nonzero-partial condition as an explicit verification detail. It does not claim a global implicit-function theorem result, pointwise (F_y\ne0) proof, or branch/domain theorem unless those semantics are separately represented.

Malformed inputs, invalid variables, zero denominators, incorrect derivatives, and unresolved symbolic comparisons fail closed rather than being guessed.


## Integration

The `integrate` rule verifies both indefinite and definite scalar symbolic integration. For indefinite integration, the candidate is differentiated back to the integrand, allowing arbitrary integration constants (and for repeated integration, the corresponding lower-order integration polynomial) rather than comparing against one backend-specific primitive.

For definite integration, explicit lower and upper bounds are required and the symbolic result is compared directly. An unevaluated `Integral` is classified as UNVERIFIED rather than treated as failure or success.

The current integration primitive supports an explicit positive integer `order` for repeated **indefinite** integration. Repeated definite/multiple nested integration is deliberately left for the subsequent repeated/nested-integration capability so that its representation can be made explicit rather than inferred.
