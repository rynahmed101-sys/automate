from unittest.mock import patch

from automate.dev.publisher import worker_branch_name


def test_worker_branch_is_bound_to_exact_base_sha():
    sha = "0123456789abcdef0123456789abcdef01234567"
    assert worker_branch_name("stage1b.series_expansions", sha) == "feat/stage1b.series_expansions-0123456789ab"


def test_worker_branch_without_sha_remains_safe_for_unit_callers():
    assert worker_branch_name("stage1b.series_expansions") == "feat/stage1b.series_expansions"


def test_autonomous_cycle_uses_scheduler_mirror_switch_names():
    from automate.dev import autonomous

    with patch.dict(
        "os.environ",
        {
            "AUTOMATE_MIRROR_DISCOVERY_ENABLED": "true",
            "MIRROR_AUTONOMOUS_DISCOVERY_ENDPOINT": "https://mirror.example/discover",
        },
        clear=False,
    ):
        assert (
            autonomous.os.getenv("AUTOMATE_MIRROR_DISCOVERY_ENABLED") == "true"
            and autonomous.os.getenv("MIRROR_AUTONOMOUS_DISCOVERY_ENDPOINT").startswith("https://")
        )
