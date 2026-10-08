from pathlib import Path
import subprocess

import pytest

from mirror_lab.workspace import WorkspaceTool


def test_workspace_run_allows_only_bounded_verification(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    tool = WorkspaceTool(tmp_path)
    result = tool.run(["git", "status", "--short"])
    assert result["returncode"] == 0
    with pytest.raises(ValueError):
        tool.run(["python", "-c", "open('pwned','w').write('x')"])
    with pytest.raises(ValueError):
        tool.run(["git", "push", "origin", "main"])
