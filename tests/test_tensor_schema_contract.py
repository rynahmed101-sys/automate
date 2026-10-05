"""Tests keeping the committed Tensor JSON contract aligned with the Pydantic model."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from automate.ir.tensors import TensorEquation, TensorExpression, TensorIndex, TensorProduct, TensorQuantity


def test_committed_tensor_schema_covers_model_surface():
    root = Path(__file__).parents[1]
    committed = json.loads(
        (root / "schemas" / "automate-tensor-v1.json").read_text(encoding="utf-8")
    )
    generated = TensorEquation.model_json_schema()

    assert committed["$id"] == "https://automate.physics/schemas/automate-tensor-v1.json"
    assert set(generated["properties"]) <= set(committed["properties"])
    assert set(generated.get("$defs", {})) <= set(committed.get("$defs", {}))

    for definition_name in ("TensorIndex", "TensorQuantity", "TensorProduct", "TensorExpression"):
        assert definition_name in committed["$defs"]
        assert set(generated["$defs"][definition_name]["properties"]) <= set(
            committed["$defs"][definition_name]["properties"]
        )


def test_committed_tensor_schema_accepts_valid_structured_equation():
    index_i = {"symbol": "i", "position": "upper", "is_dummy": False, "dimension": 4}
    index_j = {"symbol": "j", "position": "lower", "is_dummy": False, "dimension": 4}
    tensor = {
        "lhs": {
            "terms": [[index_i]],
            "products": [{"factors": [{
                "name": "T",
                "indices": [index_i],
                "dimension": "energy"
            }]}]
        },
        "rhs": {
            "terms": [[index_j]],
            "products": [{"factors": [{
                "name": "S",
                "indices": [index_j],
                "dimension": "energy"
            }]}]
        }
    }
    Draft202012Validator.check_schema(committed_schema := json.loads(
        (Path(__file__).parents[1] / "schemas" / "automate-tensor-v1.json").read_text(
            encoding="utf-8"
        )
    ))
    Draft202012Validator(committed_schema).validate(tensor)


def test_tensor_model_exports_match_contract_types():
    assert TensorIndex.model_json_schema()["type"] == "object"
    assert TensorQuantity.model_json_schema()["type"] == "object"
    assert TensorProduct.model_json_schema()["type"] == "object"
    assert TensorExpression.model_json_schema()["type"] == "object"
