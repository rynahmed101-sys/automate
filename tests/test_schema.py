"""
Tests for Automate IR JSON Schema v0.1 validation.
"""

from pathlib import Path
import json
import pytest
import jsonschema
from jsonschema import Draft202012Validator

from automate.theory.parser import parse_theory_file
from automate.core.graph import DerivationGraph


def test_schema_validity():
    schema_path = Path(__file__).parent.parent / "schemas" / "automate-ir-v0.1.json"
    assert schema_path.exists(), "Schema file must exist"
    
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    # Verify the schema itself is a valid Draft 2020-12 JSON schema
    Draft202012Validator.check_schema(schema)


def test_validate_harmonic_oscillator_graph_against_schema():
    schema_path = Path(__file__).parent.parent / "schemas" / "automate-ir-v0.1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    theory_path = Path(__file__).parent.parent / "examples" / "harmonic_oscillator.yaml"
    graph = parse_theory_file(theory_path)

    graph_dict = graph.model_dump()
    
    # Must validate cleanly without exception
    jsonschema.validate(instance=graph_dict, schema=schema)


def test_schema_rejects_invalid_graph():
    schema_path = Path(__file__).parent.parent / "schemas" / "automate-ir-v0.1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Missing required 'nodes' field
    invalid_graph = {
        "id": "invalid_test",
        "name": "Invalid Graph",
        "edges": {}
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_graph, schema=schema)
