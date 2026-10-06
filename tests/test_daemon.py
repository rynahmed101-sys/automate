from automate.dev.daemon import run_bounded_loop


def test_bounded_autonomous_loop_runs_exact_requested_cycles():
    seen = []

    def fake_cycle(repository, **kwargs):
        seen.append((repository, kwargs))
        return {"status": "stopped"}

    results = run_bounded_loop(
        "rynahmed101-sys/automate",
        max_cycles=3,
        cycle_fn=fake_cycle,
    )
    assert [x["cycle"] for x in results] == [1, 2, 3]
    assert len(seen) == 3


def test_bounded_autonomous_loop_stops_after_failure():
    calls = []

    def fake_cycle(repository, **kwargs):
        calls.append(repository)
        raise RuntimeError("worker unavailable")

    results = run_bounded_loop(
        "rynahmed101-sys/automate",
        max_cycles=10,
        cycle_fn=fake_cycle,
    )
    assert len(calls) == 1
    assert results == [{
        "cycle": 1,
        "status": "error",
        "error": "worker unavailable",
    }]
