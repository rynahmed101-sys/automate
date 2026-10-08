"""Tests for isolated worker branch publishing."""

from pathlib import Path
from unittest.mock import patch

import pytest

from automate.dev.publisher import WorkerExecutionError, worker_branch_name


def test_worker_branch_name_is_deterministic():
    assert worker_branch_name("stage1b.improper_integrals") == "feat/stage1b.improper_integrals"


@pytest.mark.parametrize("value", ["", "../escape", "stage1b;rm -rf /", "SPACE"])
def test_worker_branch_name_rejects_unsafe_ids(value):
    with pytest.raises(WorkerExecutionError):
        worker_branch_name(value)


def test_publisher_module_is_importable():
    assert Path("automate/dev/publisher.py").is_file()


def test_worker_branch_name_is_not_a_general_git_branch_helper():
    assert worker_branch_name("stage1b.improper_integrals").startswith("feat/")


def test_worker_branch_name_binds_base_sha():
    from automate.dev.publisher import worker_branch_name

    base = "a" * 40
    assert worker_branch_name("stage1b.series_expansions", base) == "feat/stage1b.series_expansions-" + "a" * 12


def test_worker_branch_name_rejects_bad_sha():
    from automate.dev.executor import WorkerExecutionError
    from automate.dev.publisher import worker_branch_name

    try:
        worker_branch_name("stage1b.series_expansions", "bad")
    except WorkerExecutionError as exc:
        assert "base sha" in str(exc)
    else:
        raise AssertionError("invalid base SHA must not produce a worker branch")
