# Stage 2E — Statistical / Data Analysis Foundation

Automate's statistical backend is an evidence-producing checker, not a generic numerical fitting wrapper.

## Implemented

- Explicit parametric model selection and graph-to-model binding.
- Observational-data requirement for statistically checked inference.
- Dataset SHA-256 fingerprints and caller-declared provenance.
- Nonlinear least-squares fitting with bounded execution budget.
- Symbolic parameter-sensitivity Jacobian and local identifiability checks.
- Parameter standard errors and Student-t confidence intervals.
- Residual sum of squares, R², residual mean/std, lag-1 autocorrelation, and a normality diagnostic.
- Chi-square compatibility intervals and p-values only when the error model assumptions are explicitly declared.
- Machine-readable distinction between STATISTICALLY_CHECKED, UNVERIFIED, NOT_APPLICABLE, and FAILED.

## Explicit chi-square assumptions

A positive noise_std is only a numerical scale; it does not establish a statistical error model.

For a chi-square goodness-of-fit claim, the edge must explicitly declare:

- independent_errors
- normal_errors
- finite_variance
- known_error_scale

Without these premises, fitting may still be useful as numerical parameter estimation, but the chi-square claim is UNVERIFIED rather than silently accepted.

## Evidence boundary

The backend does not authenticate caller-declared data provenance, prove independence or normality from a p-value, or upgrade a fitted curve to a scientific truth claim. Residual normality is diagnostic evidence, not an automatic assumption validator.

## Intentionally incomplete

- Generalized heteroscedastic/correlated covariance matrices.
- Robust regression families.
- Bayesian inference and posterior evidence.
- Causal inference.
- Automatic provenance authentication.
- General nonparametric hypothesis-test selection.
