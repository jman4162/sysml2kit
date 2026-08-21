from pathlib import Path

import pytest

from sysml2kit.workspace import reject_path_traversal, validate_path_within


def test_plain_paths_pass():
    assert reject_path_traversal("models/a.json") == Path("models/a.json")
    assert reject_path_traversal("/abs/path.sysml") == Path("/abs/path.sysml")


def test_traversal_rejected():
    with pytest.raises(ValueError, match="traversal"):
        reject_path_traversal("../../etc/passwd")
    with pytest.raises(ValueError, match="traversal"):
        reject_path_traversal("a/../b.json")


def test_containment(tmp_path):
    inside = tmp_path / "sub" / "f.json"
    assert validate_path_within(inside, tmp_path) == inside.resolve()
    with pytest.raises(ValueError, match="escapes"):
        validate_path_within(tmp_path.parent / "other.json", tmp_path)
