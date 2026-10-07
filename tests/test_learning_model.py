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
