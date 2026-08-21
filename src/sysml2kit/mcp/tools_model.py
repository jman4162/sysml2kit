"""Model inspection and conversion tools.

Rules (family convention): tool name is ``domain_verb``; inputs are flat
scalars with units in the Field description; outputs are JSON-safe dicts
with a "status" key; errors are returned, never raised; heavy imports live
inside function bodies; every path argument passes reject_path_traversal
first.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from pydantic import Field

from sysml2kit.mcp._common import load_model_file
from sysml2kit.mcp.server import get_mcp

logger = logging.getLogger(__name__)
mcp = get_mcp()

ModelPath = Annotated[str, Field(description="Model file path: .json interchange or .sysml text")]
OutPath = Annotated[str, Field(description="Output file path; parent dirs are created")]

_DIFF_ENTRY_CAP = 200

_load = load_model_file


@mcp.tool()
async def model_show(
    path: ModelPath,
    traceability: Annotated[
        bool, Field(description="Include the requirement-to-part trace matrix")
    ] = False,
) -> dict[str, Any]:
    """Summarize a model file: element tree, kind counts, optional trace matrix."""
    logger.info("model_show %s", path)
    try:
        model = _load(path)
        counts: dict[str, int] = {}
        lines = []
        for element in model.iter_elements():
            counts[type(element).__name__] = counts.get(type(element).__name__, 0) + 1
            depth = 0
            current = model.owner.get(element.element_id)
            while current is not None:
                depth += 1
                current = model.owner.get(current)
            lines.append("    " * depth + f"{type(element).__name__}: {element.label}")
        result: dict[str, Any] = {
            "status": "ok",
            "element_count": len(model.elements),
            "kinds": counts,
            "tree": "\n".join(lines),
        }
        if traceability:
            from sysml2kit.query import trace_matrix

            result["trace_matrix"] = trace_matrix(model).render()
        logger.info("model_show ok: %d elements", len(model.elements))
        return result
    except Exception as e:
        logger.exception("model_show failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def model_validate(path: ModelPath) -> dict[str, Any]:
    """Validate a model file against the S2K rule set."""
    logger.info("model_validate %s", path)
    try:
        from sysml2kit.validation import validate

        issues = validate(_load(path))
        payload = [
            {
                "severity": i.severity,
                "rule_id": i.rule_id,
                "message": i.message,
                "element_id": str(i.element_id) if i.element_id else None,
            }
            for i in issues
        ]
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        logger.info("model_validate: %d errors, %d warnings", errors, warnings)
        return {
            "status": "ok" if errors == 0 else "issues",
            "issues": payload,
            "error_count": errors,
            "warning_count": warnings,
        }
    except Exception as e:
        logger.exception("model_validate failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def model_diff(
    path_a: ModelPath,
    path_b: ModelPath,
    by_name: Annotated[
        bool, Field(description="Match elements by qualified name instead of element id")
    ] = False,
) -> dict[str, Any]:
    """Compare two model files element by element."""
    logger.info("model_diff %s %s", path_a, path_b)
    try:
        from sysml2kit.diff import diff_models

        entries = diff_models(_load(path_a), _load(path_b), by_name=by_name)
        payload = [
            {"kind": e.kind, "qualified_name": e.qualified_name, "detail": e.detail}
            for e in entries[:_DIFF_ENTRY_CAP]
        ]
        logger.info("model_diff: %d entries", len(entries))
        return {
            "status": "ok",
            "identical": not entries,
            "entry_count": len(entries),
            "entries": payload,
            "entries_truncated": len(entries) > _DIFF_ENTRY_CAP,
        }
    except Exception as e:
        logger.exception("model_diff failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def model_export(
    path: ModelPath,
    out: OutPath,
    to: Annotated[str, Field(description="Output format: json or sysml")] = "json",
    stable_ids: Annotated[
        bool, Field(description="Rewrite ids as UUIDv5 name hashes before export")
    ] = False,
) -> dict[str, Any]:
    """Convert a model file to interchange JSON or textual notation."""
    logger.info("model_export %s -> %s (%s)", path, out, to)
    try:
        from pathlib import Path

        from sysml2kit.workspace import reject_path_traversal

        out_path = reject_path_traversal(out)
        model = _load(path)
        if stable_ids:
            model.assign_stable_ids()
        if to == "json":
            import json

            from sysml2kit.interchange import model_to_json

            text = json.dumps(model_to_json(model), indent=2) + "\n"
        elif to == "sysml":
            from sysml2kit.text import write_model

            text = write_model(model)
        else:
            raise ValueError("to must be 'json' or 'sysml'")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text)
        logger.info("model_export ok: %s", out_path)
        return {
            "status": "ok",
            "out": str(out_path),
            "format": to,
            "element_count": len(model.elements),
        }
    except Exception as e:
        logger.exception("model_export failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def model_diagram(
    path: ModelPath,
    out: OutPath,
    kind: Annotated[
        str, Field(description="Diagram view: trace (requirements) or tree (ownership)")
    ] = "trace",
) -> dict[str, Any]:
    """Write a mermaid diagram (.mmd) of a model file."""
    logger.info("model_diagram %s -> %s (%s)", path, out, kind)
    try:
        from pathlib import Path

        from sysml2kit.views import to_mermaid_trace, to_mermaid_tree
        from sysml2kit.workspace import reject_path_traversal

        out_path = reject_path_traversal(out)
        model = _load(path)
        if kind == "trace":
            text = to_mermaid_trace(model)
        elif kind == "tree":
            text = to_mermaid_tree(model)
        else:
            raise ValueError("kind must be 'trace' or 'tree'")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text)
        logger.info("model_diagram ok: %s", out_path)
        return {"status": "ok", "out": str(out_path), "kind": kind}
    except Exception as e:
        logger.exception("model_diagram failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def library_load(
    name: Annotated[
        str, Field(description="Packaged model name, e.g. rf-library or satcom-terminal-t3001")
    ] = "rf-library",
    out: OutPath = "library.json",
) -> dict[str, Any]:
    """Write a packaged sysml2kit-rf-library model as an interchange JSON file."""
    logger.info("library_load %s -> %s", name, out)
    try:
        from pathlib import Path

        from sysml2kit.workspace import reject_path_traversal

        out_path = reject_path_traversal(out)
        try:
            from sysml2kit_rf_library import load_model
        except ImportError as exc:
            raise ImportError(
                "the model library is not installed: pip install sysml2kit-rf-library"
            ) from exc
        from sysml2kit.interchange import write_json

        model = load_model(name)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        write_json(model, out_path)
        logger.info("library_load ok: %s", out_path)
        return {"status": "ok", "out": str(out_path), "element_count": len(model.elements)}
    except Exception as e:
        logger.exception("library_load failed")
        return {"error": str(e), "status": "failed"}
