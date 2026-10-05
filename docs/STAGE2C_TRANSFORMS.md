# Stage 2C Transform Foundation

This implementation establishes reusable transform representations rather than standalone calculator functions.

## Canonical conventions

Fourier uses angular frequency: F(w)=∫f(x)e^(-iwx)dx and inverse f(x)=1/(2π)∫F(w)e^(iwx)dw. The convention must be explicitly declared by callers.

Laplace uses the unilateral integral F(s)=∫_0^∞ f(t)e^(-st)dt. The backend only certifies cases where symbolic evaluation establishes a result; unresolved convergence or transform evaluation is not certified.

## Current bounded capability

- reusable TransformNode and FourierSeriesNode/ConvolutionNode IR objects;
- symbolic Fourier forward and inverse verification for tractable expressions;
- symbolic Laplace forward and inverse verification for tractable expressions;
- continuous convolution evaluation for tractable expressions;
- explicit transform conventions and fail-closed unresolved cases.

Fourier-series coefficient/reconstruction verification and the convolution theorem rule remain intentionally unimplemented in the backend despite registry placeholders; these require a more complete series/paired-transform representation. No Green-function implementation is included in this PR.