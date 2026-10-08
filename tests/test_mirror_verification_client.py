import json
from unittest.mock import patch

from automate.dev.mirror_verification_client import (
    MirrorVerificationError,
    run_mirror_verification,
)


def _request():
    return {
        "schema_version": "mirror.verification_request.v1",
        "request_id": "ver_" + "a" * 32,
        "action_cycle_id": "cycle_test123",
        "capability_id": "stage1b.series_expansions",
        "source_revision": "b" * 40,
        "experiment_type": "convergence_stability",
        "hypothesis": "independent convergence check",
        "inputs": {"integrand": "1/(1+x**2)"},
        "assumptions": [],
        "budget": {
            "max_precision": 80,
            "max_truncation": 8,
            "max_runtime_ms": 30000,
        },
        "requirements": ["return observations, not certification"],
    }


def test_mirror_verification_client_binds_request_identity():
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, limit):
            return json.dumps({
                "schema_version": "mirror.verification_result.v1",
                "authority": "UNTRUSTED_EXPERIMENTAL_OBSERVATION",
                "experiment_id": "exp_12345678",
                "request_id": _request()["request_id"],
                "action_cycle_id": "cycle_test123",
                "capability_id": "stage1b.series_expansions",
                "source_revision": _request()["source_revision"],
                "status": "REPRODUCED",
                "hypothesis": "independent convergence check",
                "inputs": {"integrand": "1/(1+x**2)"},
                "assumptions": [],
                "observations": [],
                "diagnostics": {
                    "runtime_ms": 10,
                    "max_precision_used": 40,
                    "route_disagreement_max": None,
                    "source_fingerprint": "c" * 64,
                    "limitations": [],
                },
            }).encode()

    with patch(
        "automate.dev.mirror_verification_client.urlopen",
        return_value=Response(),
    ) as open_url:
        result = run_mirror_verification(
            _request(),
            url="https://mirror.example/api/verification/experiment",
            token="secret",
        )
    assert result["request_id"] == _request()["request_id"]
    assert result["source_revision"] == _request()["source_revision"]
    assert open_url.call_args.args[0].headers["Authorization"] == "Bearer secret"


def test_mirror_verification_rejects_authority_claim():
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, limit):
            return b'{"authority":"CERTIFIED","request_id":"ver_' + b'a'*32 + b'"}'

    with patch(
        "automate.dev.mirror_verification_client.urlopen",
        return_value=Response(),
    ):
        try:
            run_mirror_verification(_request(), url="https://mirror.example", token="secret")
        except MirrorVerificationError as exc:
            assert "authority" in str(exc)
        else:
            raise AssertionError("unexpected Mirror authority was accepted")
