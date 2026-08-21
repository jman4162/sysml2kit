"""Requirement traceability and extraction tools.

Same rules as tools_model: flat scalar inputs, "status" key on every return,
errors returned not raised, traversal-checked paths.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from pydantic import Field

from sysml2kit.mcp._common import load_model_file as _load
from sysml2kit.mcp.server import get_mcp

logger = logging.getLogger(__name__)
mcp = get_mcp()

ModelPath = Annotated[str, Field(description="Model file path: .json interchange or .sysml text")]


@mcp.tool()
async def requirements_trace(path: ModelPath) -> dict[str, Any]:
    """Report requirement traceability: matrix, unsatisfied, unverified."""
    logger.info("requirements_trace %s", path)
    try:
        from sysml2kit.query import (
            parts_of,
            requirements_in,
            trace_matrix,
            unsatisfied_requirements,
            unverified_requirements,
        )

        model = _load(path)
        result = {
            "status": "ok",
            "requirement_count": len(requirements_in(model)),
            "part_count": len(parts_of(model)),
            "matrix": trace_matrix(model).render(),
            "unsatisfied": [
                r.declared_short_name or r.label for r in unsatisfied_requirements(model)
            ],
            "unverified": [
                r.declared_short_name or r.label for r in unverified_requirements(model)
            ],
        }
        logger.info(
            "requirements_trace: %d requirements, %d unsatisfied",
            result["requirement_count"],
            len(result["unsatisfied"]),  # type: ignore[arg-type]
        )
        return result
    except Exception as e:
        logger.exception("requirements_trace failed")
        return {"error": str(e), "status": "failed"}


@mcp.tool()
async def requirements_extract(path: ModelPath) -> dict[str, Any]:
    """Extract machine-checkable requirements (the metricKey convention) as specs."""
    logger.info("requirements_extract %s", path)
    try:
        from sysml2kit.interop import extract_requirements

        specs = extract_requirements(_load(path))
        logger.info("requirements_extract: %d specs", len(specs))
        return {
            "status": "ok",
            "count": len(specs),
            "requirements": [spec.model_dump() for spec in specs],
        }
    except Exception as e:
        logger.exception("requirements_extract failed")
        return {"error": str(e), "status": "failed"}
