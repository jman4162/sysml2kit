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


@mcp.tool()
async def requirements_verify(
    path: ModelPath,
    report_out: Annotated[
        str, Field(description="Where to write the VerificationRun JSON report")
    ] = "verification_run.json",
    write_back_out: Annotated[
        str, Field(description="Optional path for the results-annotated model JSON; empty skips")
    ] = "",
    policy: Annotated[str, Field(description="Rung selection: all, cheapest, or escalate")] = "all",
    budget_s: Annotated[
        float, Field(description="Wall-clock budget for escalate, in seconds; 0 = unlimited")
    ] = 0.0,
) -> dict[str, Any]:
    """Run bound analyses (verificationBinding metadata) and check their requirements."""
    logger.info("requirements_verify %s", path)
    try:
        from datetime import UTC, datetime
        from pathlib import Path

        from sysml2kit.verify import EngineRegistry, apply_results, run_verification
        from sysml2kit.workspace import reject_path_traversal

        report_path = reject_path_traversal(report_out)
        model = _load(path)
        if policy not in ("all", "cheapest", "escalate"):
            raise ValueError("policy must be all, cheapest, or escalate")
        run = run_verification(
            model,
            model_path=Path(path),
            registry=EngineRegistry.discover(),
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            policy=policy,  # type: ignore[arg-type]
            budget_s=budget_s or None,
        )
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(run.model_dump_json(indent=2) + "\n")
        result: dict[str, Any] = {
            "status": "ok",
            "passed": run.passed,
            "report": str(report_path),
            "must_failures": [
                v.requirement_id
                for v in run.requirements
                if v.severity == "must" and v.status != "pass"
            ],
            "analysis_errors": [a.analysis for a in run.analyses if a.error],
            "seconds_by_fidelity": run.seconds_by_fidelity,
        }
        if write_back_out:
            import json

            from sysml2kit.interchange import model_to_json

            out_path = reject_path_traversal(write_back_out)
            apply_results(model, run)
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(json.dumps(model_to_json(model), indent=2) + "\n")
            result["write_back"] = str(out_path)
        logger.info("requirements_verify: passed=%s", run.passed)
        return result
    except Exception as e:
        logger.exception("requirements_verify failed")
        return {"error": str(e), "status": "failed"}
