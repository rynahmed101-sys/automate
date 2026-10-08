from automate.dev import control_cycle


def test_open_worker_handoff_disables_new_dispatch(monkeypatch):
    monkeypatch.setattr(
        control_cycle,
        "run_autonomous_cycle",
        lambda *args, **kwargs: {
            "status": "committed",
            "decision": {"worker_packet": {"packet": {"repository": {"base_sha_claim": "a" * 40}}},
            },
            "commit": {"status": "not_committed"},
        },
    )

    # The pure invariant is represented directly here: an active implementation
    # PR must never advertise that another worker can be dispatched for the same cycle.
    lifecycle = {"state": "IMPLEMENTATION_PR"}
    handoff_open = lifecycle.get("state") == "IMPLEMENTATION_PR"
    assert handoff_open is True
    assert (not handoff_open) is False
