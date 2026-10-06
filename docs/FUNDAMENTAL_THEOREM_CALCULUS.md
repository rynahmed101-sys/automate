# Fundamental Theorem of Calculus

Automate's Stage 1B Fundamental Theorem of Calculus capability verifies two explicit theorem forms through a single rule with a machine-readable mode.

## Evaluation form

For a continuous integrand f on the represented interval and an antiderivative F with F'=f,

    integral_a^b f(t) dt = F(b) - F(a).

The verifier receives the integrand and candidate antiderivative as input nodes, then checks the antiderivative identity symbolically and compares the claimed definite-integral result with the exact endpoint difference.

The result is not obtained by asking a numerical backend to estimate the integral. The candidate is checked against the theorem's structural requirement first.

## Accumulation-function derivative form

For

    F(x) = integral_a^x f(t) dt,

the verifier checks a candidate accumulation function F(x) in two parts:

1. F'(x)=f(x), after explicitly changing the integrand's integration variable to x.
2. F(a)=0, establishing the lower-endpoint anchor for the accumulation function.

The proposed derivative output is then checked against f(x).

The continuity requirement is explicit. The edge must carry the side condition ftc_integrand_continuous_on_interval, and that condition must be backed by an active graph assumption. The checker never treats a free string such as "continuous" as mathematical evidence.

## Representation

The rule is fundamental_theorem_calculus with:

- mode: evaluation or accumulation_derivative
- variable: the theorem's variable
- integration_variable: the explicit dummy integration variable
- lower: lower endpoint
- upper: required only for evaluation

The rule uses two input nodes:

- scalar integrand
- antiderivative or accumulation function

and one scalar output node containing the claimed theorem result.

Keeping the dummy integration variable explicit prevents accidental capture when the antiderivative uses a different symbol.

## Failure semantics

Malformed variables, missing bounds, non-antiderivative candidates, incorrect endpoint evaluations, failed anchoring, unresolved symbolic equalities, and missing continuity obligations do not pass.

A symbolic equality that cannot be decided exactly is classified as UNVERIFIED. The capability does not promote numerical agreement into exact mathematical verification.

## Scope

This capability covers the theorem's core one-variable symbolic forms. It does not claim multivariable FTC statements, differential-form generalizations, measure-theoretic versions, or a proof of continuity itself. Those remain separate capabilities on the Stage 1B ladder.
