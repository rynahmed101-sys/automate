"""Deterministic translation from canonical tensor IR to Cadabra source.

The translator accepts only structured TensorProduct/TensorExpression objects.
It never accepts arbitrary Cadabra snippets as a substitute for translation.
The generated source is intended for bounded external execution and records
the IR fingerprint so the resulting evidence can be tied to the exact input.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Iterable, List

from automate.ir.tensors import TensorExpression, TensorIndex, TensorProduct

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _validate_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsupported tensor identifier: {value!r}")
    return value


def _index_text(index: TensorIndex) -> str:
    symbol = _validate_identifier(index.symbol)
    return f"^{{{symbol}}}" if index.position == "upper" else f"_{{{symbol}}}"


def tensor_factor_to_cadabra(factor) -> str:
    name = _validate_identifier(factor.name)
    indices = "".join(_index_text(index) for index in factor.indices)
    return f"{name}{indices}"


def tensor_product_to_cadabra(product: TensorProduct) -> str:
    validation = product.validate_structure()
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))
    return " ".join(tensor_factor_to_cadabra(factor) for factor in product.factors)


def tensor_expression_to_cadabra(expression: TensorExpression) -> str:
    """Translate each structured product term into a Cadabra expression."""
    if expression.products is None:
        raise ValueError(
            "Cadabra translation requires TensorExpression.products so tensor "
            "factor names are preserved; legacy index-only terms are not translatable."
        )
    validation = expression.validate_structure()
    if not validation.is_valid:
        raise ValueError("; ".join(validation.errors))
    return " + ".join(tensor_product_to_cadabra(product) for product in expression.products)


def cadabra_declarations(expression: TensorExpression) -> List[str]:
    """Return no implicit Cadabra properties.

    Index spaces and tensor symmetries require domain-specific metadata that
    cannot safely be inferred from the current IR. The translator therefore
    emits only the mathematically explicit indexed expression.
    """
    if expression.products is None:
        raise ValueError("Structured tensor products are required for Cadabra translation.")
    return []


def translate_expression(expression: TensorExpression) -> dict:
    """Return deterministic Cadabra source plus a canonical IR fingerprint."""
    source_expression = tensor_expression_to_cadabra(expression)
    declarations = cadabra_declarations(expression)
    source = "\n".join(declarations + [f"{{{source_expression}}};"])
    canonical = expression.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "engine": "Cadabra2",
        "source": source,
        "ir_fingerprint_sha256": fingerprint,
        "translation": "canonical TensorExpression.products -> Cadabra syntax",
    }
