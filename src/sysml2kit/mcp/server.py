"""MCP server singleton.

Ordering rule: the singleton is assigned before tool modules are imported,
so their module-level ``get_mcp()`` re-enters and receives the partially
built instance instead of recursing.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_server: Any = None  # typed loosely: the class differs between MCP SDK generations


def get_mcp() -> Any:
    """Return the process-wide FastMCP instance, building it on first call."""
    return _get_server()


def _get_server() -> Any:
    global _server
    if _server is not None:
        return _server

    try:
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            from mcp.server import MCPServer as FastMCP  # type: ignore[attr-defined, no-redef]
    except ImportError as exc:
        raise ImportError(
            "the MCP server needs the 'mcp' extra: pip install sysml2kit[mcp]"
        ) from exc

    _server = FastMCP(
        name="sysml2kit",
        instructions=(
            "Work with SysML v2 models: inspect, validate, diff, export, and "
            "diagram model files, and extract machine-checkable requirements "
            "with their traceability. Inputs are .json interchange files "
            "(always supported) or .sysml text (needs the parse extra). "
            "Artifacts are returned as file paths, not payloads."
        ),
    )

    import sysml2kit.mcp.tools_model
    import sysml2kit.mcp.tools_requirements  # noqa: F401

    return _server


def run_server(transport: str = "stdio") -> None:
    """Run the MCP server on the given transport."""
    _get_server().run(transport=transport)
