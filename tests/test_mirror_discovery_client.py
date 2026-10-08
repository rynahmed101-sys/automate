import json
from unittest.mock import patch

from automate.dev.mirror_discovery_client import (
    MirrorDiscoveryError,
    dispatch_mirror_discovery,
)


def _grant():
    return {
        "schema_version": "automate.mirror_discovery_grant.v1",
        "grant_id": "dgrant_" + "a" * 32,
        "authority": "UNTRUSTED_EXPLORATION_PERMISSION",
        "issuer": "automate",
        "correlation_id": "ctrl_test1234",
        "issued_at": "2026-10-07T08:00:00.000Z",
        "expires_at": "2026-10-07T08:15:00.000Z",
        "max_candidates": 1,
        "allowed_actions": ["research_world", "propose_new_capability"],
        "forbidden_actions": ["mutate_canonical_inventory", "mutate_phase_ledger"],
        "canonical_mutation_allowed": False,
    }


def test_mirror_discovery_dispatch_is_bounded_and_forwards_grant():
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, limit):
            return b'{"success": true}'

    with patch(
        "automate.dev.mirror_discovery_client.urlopen",
        return_value=Response(),
    ) as open_url:
        result = dispatch_mirror_discovery(
            _grant(),
            url="https://mirror.example/internal/discovery",
            token="secret",
            max_tool_steps=99,
        )
    assert result["success"] is True
    req = open_url.call_args.args[0]
    body = json.loads(req.data.decode())
    assert body["discoveryGrant"]["grant_id"].startswith("dgrant_")
    assert body["correlationId"] == "ctrl_test1234"
    assert body["maxToolSteps"] == 8


def test_mirror_discovery_rejects_authority_bypass():
    grant = {**_grant(), "canonical_mutation_allowed": True}
    try:
        dispatch_mirror_discovery(
            grant,
            url="https://mirror.example/internal/discovery",
            token="secret",
        )
    except MirrorDiscoveryError as exc:
        assert "canonical mutation" in str(exc)
    else:
        raise AssertionError("unsafe discovery grant was accepted")
