"""Path-safety helpers shared by the MCP tools (and any future file surface)."""

from __future__ import annotations

from pathlib import Path


def reject_path_traversal(path: str | Path) -> Path:
    """Return the path, refusing any that contains a ``..`` segment."""
    candidate = Path(path)
    if ".." in candidate.parts:
        raise ValueError(f"path traversal rejected: {path}")
    return candidate


def validate_path_within(path: str | Path, root: str | Path) -> Path:
    """Resolve both paths and require containment; returns the resolved path."""
    resolved = Path(path).resolve()
    resolved_root = Path(root).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"path {path} escapes {root}")
    return resolved
