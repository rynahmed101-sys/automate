# Stage 1C ODE Foundation

Automate's Stage 1C implementation provides reusable ordinary-differential-equation
representation and verification through the existing derivation graph and SafeParser
boundaries.

## Representation

ODE equations remain ordinary mathematical-expression nodes. The edge parameters
identify the independent variable and dependent function when needed:

- \`variable\`: independent-variable name, default \`t\`
- \`function\`: dependent-function name, default \`y\`
- \`domain\`: optional domain metadata retained in verification evidence
- \`assumptions\`: optional assumption metadata

Higher derivatives are represented with the existing function notation, for example
\`diff(y(t), t, 4)\`. Coupled systems are represented as tuples of equations and
tuple-valued proposed solutions. Phase-space systems use tuples of state RHS
expressions.

## Capabilities

The ODE engine currently provides:

- generic proposed-solution verification with inferred derivative order;
- separable first-order equations \`y' = f(x)g(y)\`;
- linear first-order equations \`y' + P(x)y = Q(x)\` with integrating-factor construction;
- Bernoulli equations with explicit \`v = y^(1-n)\` transformation;
- exact first-order differential forms \`M dx + N dy = 0\` with exactness and potential checks;
- homogeneous linear constant-coefficient ODEs of inferred order;
- characteristic-polynomial construction and root classification for real, repeated,
  and complex roots where the roots are computationally tractable;
- initial-value verification, including higher-order derivative conditions;
- boundary-value verification without silently converting the problem into an IVP;
- coupled first-order system verification;
- phase-space conversion from higher-order scalar ODEs.

## Verification semantics

Every proposed solution is checked by substitution into the represented equation and
exact symbolic residual reduction. A non-zero residual is a failure.

If the backend cannot establish that a residual is zero or non-zero, the result is
\`UNVERIFIED\`; symbolic uncertainty is never promoted to a verified claim.

Initial and boundary conditions are independently substituted into the proposed
solution. A candidate that satisfies the ODE but violates a condition is rejected.

Separable and Bernoulli transformations carry explicit nonzero/domain obligations.
Bernoulli values \`n=0\` and \`n=1\` are not silently treated as generic Bernoulli
cases.

## Constant-coefficient families

The implementation infers the represented order from the highest derivative. It
does not impose a second-order ceiling. For homogeneous linear equations it forms

\`a_n lambda^n + ... + a_1 lambda + a_0\`

and records root multiplicities. Repeated real roots generate the standard
\`t^k exp(r t)\` basis; complex-conjugate roots are represented through the real
\`exp(a t) t^k {cos(bt), sin(bt)}\` family where the backend can establish the
root structure.

Forced/nonlinear constant-coefficient equations are outside this rule's current
homogeneous family and fail closed rather than being mislabeled.

## Coupled systems and phase space

System verification substitutes all proposed component functions simultaneously.
For an nth-order scalar ODE, phase-space conversion introduces states
\`z_0 = y, z_1 = y', ..., z_(n-1) = y^(n-1)\` and isolates the highest derivative
when the represented equation permits a unique symbolic isolation.

## Independent backend evidence

The implementation follows mature SymPy ODE conventions for function-valued
equations, arbitrary derivative order, initial conditions, systems, and exact
residual checking. SymPy's \`dsolve\` and \`checkodesol\` are treated as backend
reference evidence rather than semantic authority. SciPy numerical integration is
not used to upgrade an exact symbolic claim; numerical ODE evidence remains the
responsibility of the numerical backend.

## Known boundaries

- General symbolic ODE solving is not claimed for arbitrary nonlinear equations.
- Exact equations currently verify a proposed potential function directly rather
  than searching arbitrary integrating factors.
- Constant-coefficient machinery currently targets homogeneous linear equations.
- Phase-space conversion requires the highest derivative to be uniquely isolatable.
- Domain metadata is preserved and reported, but general real-domain theorem
  proving is not inferred from strings alone.
