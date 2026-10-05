"""Evidence-oriented numerical mathematics primitives."""
from .core import (
    numerical_root, numerical_derivative, numerical_integral, interpolate_linear,
    minimize_scalar, eigenproblem, fft, monte_carlo_mean, parameter_sweep,
)
__all__=["numerical_root","numerical_derivative","numerical_integral","interpolate_linear",
"minimize_scalar","eigenproblem","fft","monte_carlo_mean","parameter_sweep"]
