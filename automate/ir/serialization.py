"""
Serialization and deserialization for Automate IR schemas.
Supports JSON and YAML with strict schema versioning.
"""

import json
from typing import Dict, Any
import yaml
from automate.ir.ast import MathematicalExpression, PhysicalConstant
from automate.ir.assumptions import Assumption


CURRENT_SCHEMA_VERSION = "0.1.0"


def serialize_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: serialize_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_to_dict(v) for v in obj]
    return obj


def dump_json(data: Any, indent: int = 2) -> str:
    serialized = serialize_to_dict(data)
    if isinstance(serialized, dict) and "schema_version" not in serialized:
        serialized["schema_version"] = CURRENT_SCHEMA_VERSION
    return json.dumps(serialized, indent=indent)


def load_json(json_str: str) -> Dict[str, Any]:
    return json.loads(json_str)


def dump_yaml(data: Any) -> str:
    serialized = serialize_to_dict(data)
    if isinstance(serialized, dict) and "schema_version" not in serialized:
        serialized["schema_version"] = CURRENT_SCHEMA_VERSION
    return yaml.dump(serialized, sort_keys=False)


def load_yaml(yaml_str: str) -> Dict[str, Any]:
    return yaml.safe_load(yaml_str)
