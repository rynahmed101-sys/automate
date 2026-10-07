from automate.dev.learning_model import LearningModelError, generate_candidate_lessons


def test_model_output_remains_untrusted_candidate(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.learning_model._request_model",
        lambda **_: {
            "lessons": [{
                "lesson_type": "strategy",
                "statement": "Explicit endpoint assumptions reduce repeated failures.",
                "scope": {"task_kind": "calculus", "task_target": "integral"},
                "preconditions": ["domain is known"],
                "expected_effect": "fewer boundary mistakes",
                "supporting_experience_ids": ["exp_" + "a" * 32],
            }]
        },
    )
    candidates = generate_candidate_lessons(
        [{
            "experience_id": "exp_" + "a" * 32,
            "task": {"kind": "calculus", "target": "integral"},
            "outcome": "failure",
            "observation": {"summary": "boundary mistake", "reproducible": True},
            "strategy": {"strategy_id": "s", "name": "s"},
        }],
        endpoint="http://local",
    )
    assert len(candidates) == 1
    assert candidates[0]["status"] == "CANDIDATE"


def test_model_invalid_candidate_is_discarded(monkeypatch):
    monkeypatch.setattr(
        "automate.dev.learning_model._request_model",
        lambda **_: {"lessons": [{"statement": "", "supporting_experience_ids": ["bad"]}]},
    )
    candidates = generate_candidate_lessons(
        [{"experience_id": "exp_" + "a" * 32}],
        endpoint="http://local",
    )
    assert candidates == []

def test_model_prompt_is_bounded(monkeypatch):
    from automate.dev.learning_model import LearningModelError, generate_candidate_lessons

    monkeypatch.setattr(
        "automate.dev.learning_model._request_model",
        lambda **_: {"lessons": []},
    )
    huge = {
        "experience_id": "exp_" + "a" * 32,
        "outcome": "failure",
        "task": {"kind": "calculus", "target": "integral"},
        "strategy": {"strategy_id": "s", "name": "s"},
        "observation": {"summary": "x" * 5000, "reproducible": True},
    }
    candidates = generate_candidate_lessons([huge] * 1000, endpoint="http://local")
    assert candidates == []


def test_model_response_size_has_a_hard_limit(monkeypatch):
    from automate.dev.learning_model import LearningModelError, _request_model

    class HugeResponse:
        def read(self, size):
            return b"x" * (1_500_001)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(*_args, **_kwargs):
        return HugeResponse()

    monkeypatch.setattr("automate.dev.learning_model.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "automate.dev.learning_model.reasoning_endpoint",
        lambda *_: "http://local",
    )
    import pytest
    with pytest.raises(LearningModelError, match="response exceeds"):
        _request_model(
            endpoint="http://local",
            token=None,
            model="local",
            prompt="{}",
        )
