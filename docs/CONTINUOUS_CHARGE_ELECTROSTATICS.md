# Continuous Charge Electrostatics

Bounded Phase 2B batch for differential continuous-charge kernels.

Implemented:
- electric-field contribution from an explicit charge-density sample and displacement vector
- electric-potential contribution from an explicit charge-density sample and displacement vector
- explicit nonzero-separation contract
- explicit, required density-measure contract
- symbolic acceptance and false-claim rejection

This is deliberately not a claim of arbitrary volume/surface/line integration, automatic charge-distribution discovery, or Gauss-law verification. The next distribution batch can build explicit bounded integrals on top of this kernel.


All caller-supplied scalar parameters are parsed through Automate's restricted mathematical parser rather than SymPy string evaluation.