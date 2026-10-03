# Automate Canonical IR Specification (v0.2)

Automate Intermediate Representation (IR) is a strongly typed, mathematically rigorous representation of physics equations, variational principles, differential geometry, and derivation graphs.

---

## 1. Mathematical Expression AST (`automate.ir.ast`)

Automate models mathematical expressions not as opaque text strings, but as structured abstract syntax trees (ASTs) while preserving human-readable and projection strings (`raw_str`, `latex`, `sympy_str`, `lean_str`).

### Core Expression Nodes

| Node Type | `kind` | Key Fields | Mathematical Physics Meaning |
| :--- | :--- | :--- | :--- |
| **`ScalarNode`** | `scalar` | `value`, `dimension`, `is_constant` | Numerical or symbolic scalar quantity (e.g. mass $m$, charge $e$, $c$) |
| **`VariableNode`** | `variable` | `name`, `dimension`, `domain` | Coordinate, state variable, or field variable |
| **`BinaryOpNode`** | `binary_op` | `op`, `left`, `right` | Binary arithmetic operation (`add`, `sub`, `mul`, `div`, `pow`, `eq`) |
| **`UnaryOpNode`** | `unary_op` | `op`, `operand` | Unary functions (`neg`, `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`) |
| **`DerivativeNode`** | `derivative` | `target`, `wrt`, `order`, `deriv_type`, `connection_symbol` | Differentiations: total ($d/dt$), partial ($\partial/\partial x$), time dot ($\dot{x}, \ddot{x}$), covariant ($\nabla_\mu$), functional ($\delta/\delta \phi$), directional |
| **`IntegralNode`** | `integral` | `integrand`, `variable`, `lower_bound`, `upper_bound`, `definite`, `measure` | Definite or indefinite integral |
| **`TensorNode`** | `tensor` | `name`, `indices`, `contravariant`, `symmetry`, `dimension` | Multilinear tensor quantity |
| **`ActionNode`** | `action` | `name`, `lagrangian_density`, `measure`, `boundary_terms`, `dimension` | Spacetime action functional $S = \int d^4x \sqrt{-g} \mathcal{L}$ |
| **`MeasureNode`** | `measure` | `coordinates`, `metric_determinant`, `dimension` | Invariant integration volume measure |
| **`FieldNode`** | `field` | `name`, `field_type`, `spacetime_coordinates`, `indices` | Dynamical field $\phi(x)$, $A_\mu(x)$, $g_{\mu\nu}(x)$ |
| **`OperatorNode`** | `operator` | `name`, `symbol` | Differential or quantum mechanical operator ($\hat{H}, \hat{p}, \nabla^2$) |
| **`SumNode`** | `sum` | `summand`, `index`, `lower_bound`, `upper_bound` | Explicit summation $\sum_{i=1}^N$ |
| **`ProductNode`** | `product` | `factor`, `index`, `lower_bound`, `upper_bound` | Explicit product $\prod_{i=1}^N$ |
| **`LimitNode`** | `limit` | `expression`, `variable`, `target`, `direction` | Mathematical limit $\lim_{x \to 0}$ |
| **`PropositionNode`** | `proposition` | `claim`, `hypotheses`, `formal_statement` | Formally checkable mathematical proposition or lemma |

---

## 2. Tensor Semantics & Einstein Summation (`automate.ir.tensors`)

Automate enforces the strict algebraic and geometric rules of tensor calculus:

### 2.1 Index Definitions
Each tensor index is represented by `TensorIndex`:
- `symbol`: The index label (e.g. `'mu'`, `'nu'`, `'i'`, `'0'`).
- `position`: Either `'upper'` (contravariant) or `'lower'` (covariant).
- `is_dummy`: Boolean indicating whether the index is summed over.
- `variance`: Property returning `'contravariant'` or `'covariant'`.

### 2.2 Product & Contraction Rules (`validate_einstein_product`)
For any product of tensors:
1. **Multiplicity Bound**: Any index symbol may appear at most **twice**. An index appearing 3 or more times is illegal and immediately rejected with `ValueError`.
2. **Variance Pairing**: If an index appears twice, exactly one occurrence must be in the `'upper'` position and one in the `'lower'` position. Two upper or two lower indices produce a contraction error.
3. **Free Index Preservation**: Any index appearing exactly once is a free index.
4. **Resultant Rank**: The rank of the product is strictly the count of free indices:
   $$\text{Rank}(R_{\mu\nu} g^{\mu\nu}) = 0 \quad (\text{Ricci Scalar } R)$$
   $$\text{Rank}(T^\mu_{\ \nu} v^\nu) = 1 \quad (\text{Vector } w^\mu)$$

### 2.3 Addition & Equality Rules (`validate_tensor_sum`, `validate_tensor_equation`)
1. **Rank Homogeneity**: Tensors being summed or equated must have identical ranks.
2. **Index Structure Homogeneity**: The set of free indices (including their exact upper/lower positions) must match exactly across all terms in a sum and across the LHS and RHS of an equation:
   $$G_{\mu\nu} + \Lambda g_{\mu\nu} = 8\pi G T_{\mu\nu} \quad \checkmark \text{ (All rank 2, lower } \mu, \nu)$$
   $$G_{\mu\nu} = 8\pi G T_\mu \quad \times \text{ (Rank mismatch: 2 vs 1)}$$
   $$R_{\mu\nu} + R^{\mu}_{\ \nu} \quad \times \text{ (Position mismatch: (lower, lower) vs (upper, lower))}$$

---

## 3. Field Theory & Differential Geometry Primitives (`automate.ir.actions`)

Automate provides first-class primitives for classical field theory and general relativity:

### Differential Geometry Objects
- `Manifold`: Smooth manifold characterized by dimension ($n=4$) and signature ($(-,+,+,+)$ or $(+,-,-,-)$).
- `CoordinateChart`: Local patch coordinates (e.g. $[t, x, y, z]$ or $[r, \theta, \phi, t]$).
- `MetricTensor`: $g_{\mu\nu}$ with symmetric property and inverse metric $g^{\mu\nu}$.
- `ChristoffelSymbols`: $\Gamma^\rho_{\mu\nu} = \frac{1}{2} g^{\rho\sigma} (\partial_\mu g_{\nu\sigma} + \partial_\nu g_{\mu\sigma} - \partial_\sigma g_{\mu\nu})$, symmetric in lower indices.
- `RiemannTensor`: $R^\rho_{\sigma\mu\nu}$ (rank 4), antisymmetric in $[\mu, \nu]$.
- `RicciTensor`: $R_{\mu\nu} = R^\rho_{\mu\rho\nu}$ (rank 2 symmetric).
- `RicciScalar`: $R = g^{\mu\nu} R_{\mu\nu}$ (rank 0 scalar).
- `EinsteinTensor`: $G_{\mu\nu} = R_{\mu\nu} - \frac{1}{2} R g_{\mu\nu}$, identically divergence-free ($\nabla^\mu G_{\mu\nu} = 0$).

### Action Functionals & Euler-Lagrange Equations
- `IntegrationMeasure`: Invariant volume element $d^n x \sqrt{-g}$.
- `LagrangianDensity`: $\mathcal{L}(\phi, \partial_\mu \phi, g_{\mu\nu})$ with kinetic, potential, and interaction terms.
- `ActionFunctional`:
  $$S = \int_{\mathcal{M}} d^4x \sqrt{-g} \left( \frac{1}{16\pi G} R + \mathcal{L}_{\text{matter}} \right) + S_{\text{boundary}}$$
- `FunctionalDerivative`: $\frac{\delta S}{\delta \phi_a} = \frac{\partial \mathcal{L}}{\partial \phi_a} - \partial_\mu \left( \frac{\partial \mathcal{L}}{\partial (\partial_\mu \phi_a)} \right)$.
- `FieldEquation`: $\frac{\delta S}{\delta \phi_a} = 0$ yielding equations of motion (e.g. Einstein field equations, Klein-Gordon equation, Dirac equation).
