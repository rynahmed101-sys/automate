from automate.dev.identifiers import canonical_json, deterministic_id, sha256


def test_canonical_identity_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert deterministic_id("exp", "x") == deterministic_id("exp", "x")
    assert len(sha256({"x": 1})) == 64
