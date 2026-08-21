"""Shared helpers for the MCP tool modules."""

from __future__ import annotations

from typing import Any


def load_model_file(path_text: str) -> Any:
    """Load a traversal-checked .json or .sysml model file."""
    from pathlib import Path

    from sysml2kit.workspace import reject_path_traversal

    path = reject_path_traversal(path_text)
    if path.suffix == ".json":
        from sysml2kit.interchange import model_from_json

        return model_from_json(Path(path))
    if path.suffix == ".sysml":
        from sysml2kit.backends import get_backend

        return get_backend("sysmlpy").parse(path.read_text(), filename=str(path))
    raise ValueError(f"unsupported file type: {path} (expected .json or .sysml)")
