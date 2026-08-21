"""Run bound analyses and check requirements against their metrics.

The runner executes each analysis's engine (errors are captured per
analysis, never raised), then evaluates every metricKey requirement whose
verify link points at a run analysis. ``apply_results`` writes results back
into the model with provenance, opt-in.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

import sysml2kit
from sysml2kit.interop.requirements import Op, RequirementSpec, Severity, extract_requirements
from sysml2kit.model import builder
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.verify.binding import VerificationBinding, build_payload, extract_bindings
from sysml2kit.verify.engines import EngineRegistry

VERDICT_NAME = "verificationVerdict"
_RESULT_SOURCE_PREFIX = "sysml2kit.verify"


class AnalysisResult(BaseModel):
    """Metrics (or the captured error) from one bound analysis."""

    analysis: str
    engine: str
    config_ref: str | None = None
    metrics: dict[str, float | int | str | bool | None] = {}
    error: str | None = None


class RequirementVerdict(BaseModel):
    """One requirement checked against one analysis's metrics."""

    requirement_id: str
    metric_key: str
    analysis: str
    op: Op | None = None
    threshold: float | None = None
    units: str | None = None
    actual: float | None = None
    margin: float | None = None
    status: Literal["pass", "fail", "unknown"]
    severity: Severity = "must"


class VerificationRun(BaseModel):
    """The full result of one verification run."""

    model_path: str | None = None
    timestamp: str | None = None
    sysml2kit_version: str = sysml2kit.__version__
    engine_versions: dict[str, str] = {}
    analyses: list[AnalysisResult] = []
    requirements: list[RequirementVerdict] = []

    @property
    def passed(self) -> bool:
        """True when no analysis errored and every must-requirement passes."""
        if any(a.error for a in self.analyses):
            return False
        return all(v.status == "pass" for v in self.requirements if v.severity == "must")


def _margin(op: Op, threshold: float, actual: float) -> float:
    if op in (">=", ">"):
        return actual - threshold
    if op in ("<=", "<"):
        return threshold - actual
    return -abs(actual - threshold)


def _check(op: Op, threshold: float, actual: float) -> bool:
    return {
        ">=": actual >= threshold,
        "<=": actual <= threshold,
        "==": actual == threshold,
        ">": actual > threshold,
        "<": actual < threshold,
    }[op]


def _verdict(spec: RequirementSpec, result: AnalysisResult) -> RequirementVerdict:
    base = RequirementVerdict(
        requirement_id=spec.id,
        metric_key=spec.metric_key,
        analysis=result.analysis,
        op=spec.op,
        threshold=spec.value,
        units=spec.units,
        severity=spec.severity,
        status="unknown",
    )
    if spec.op is None or spec.value is None or result.error is not None:
        return base
    actual = result.metrics.get(spec.metric_key)
    if not isinstance(actual, int | float) or isinstance(actual, bool):
        return base
    actual_f = float(actual)
    return base.model_copy(
        update={
            "actual": actual_f,
            "margin": _margin(spec.op, spec.value, actual_f),
            "status": "pass" if _check(spec.op, spec.value, actual_f) else "fail",
        }
    )


def run_verification(
    model: Model,
    *,
    model_path: Path | None = None,
    registry: EngineRegistry | None = None,
    timestamp: str | None = None,
    analyses: Sequence[str] | None = None,
) -> VerificationRun:
    """Execute every bound analysis and check the requirements they verify.

    ``analyses`` filters bindings by qualified name. ``timestamp`` is
    caller-supplied (the CLI/MCP layer stamps it) so the library itself stays
    deterministic.
    """
    if registry is None:
        registry = EngineRegistry.discover()
    base_dir = model_path.parent if model_path is not None else Path.cwd()

    bindings = extract_bindings(model)
    if analyses is not None:
        wanted = set(analyses)
        bindings = [b for b in bindings if b.analysis in wanted]

    results: list[AnalysisResult] = []
    engine_versions: dict[str, str] = {}
    for binding in bindings:
        results.append(_run_binding(binding, registry, base_dir, engine_versions))

    by_analysis = {r.analysis: r for r in results}
    verdicts = [
        _verdict(spec, by_analysis[qualified])
        for spec in extract_requirements(model)
        for qualified in spec.verified_by
        if qualified in by_analysis
    ]
    return VerificationRun(
        model_path=str(model_path) if model_path else None,
        timestamp=timestamp,
        engine_versions=engine_versions,
        analyses=results,
        requirements=verdicts,
    )


def _run_binding(
    binding: VerificationBinding,
    registry: EngineRegistry,
    base_dir: Path,
    engine_versions: dict[str, str],
) -> AnalysisResult:
    try:
        engine = registry.get(binding.engine)
        engine_versions.setdefault(binding.engine, registry.version_of(binding.engine))
        payload = build_payload(binding, base_dir)
        metrics = dict(engine(payload))
    except Exception as exc:  # noqa: BLE001 - engines are third-party code; capture, don't crash
        return AnalysisResult(
            analysis=binding.analysis,
            engine=binding.engine,
            config_ref=binding.config_ref,
            error=f"{type(exc).__name__}: {exc}",
        )
    return AnalysisResult(
        analysis=binding.analysis,
        engine=binding.engine,
        config_ref=binding.config_ref,
        metrics=metrics,
    )


def apply_results(model: Model, run: VerificationRun) -> int:
    """Write run results back into the model; returns the element count added.

    Each checked metric becomes an attribute on its analysis (with a
    provenance ``source``); each verdict becomes a ``verificationVerdict``
    metadata on its requirement. Idempotent: prior results of the same names
    are removed first.
    """
    added = 0
    analyses = {model.qualified_name(el): el for el in model.elements.values()}
    for verdict in run.requirements:
        if verdict.status == "unknown" or verdict.actual is None:
            continue
        analysis = analyses.get(verdict.analysis)
        requirement = next(
            (
                el
                for el in model.elements.values()
                if el.declared_short_name == verdict.requirement_id
                or str(el.element_id) == verdict.requirement_id
            ),
            None,
        )
        run_result = next((a for a in run.analyses if a.analysis == verdict.analysis), None)
        if analysis is None or requirement is None or run_result is None:
            continue
        source = (
            f"{_RESULT_SOURCE_PREFIX} {verdict.analysis} "
            f"{run_result.engine}=={run.engine_versions.get(run_result.engine, 'unknown')}"
            + (f" {run.timestamp}" if run.timestamp else "")
        )
        for prior in list(model.owned_by(analysis)):
            if prior.declared_name == verdict.metric_key and _is_written_result(prior):
                model.remove(prior)
        builder.attr(
            model,
            verdict.metric_key,
            verdict.actual,
            owner=analysis,
            unit=verdict.units,
            source=source,
        )
        added += 1
        for prior in list(model.owned_by(requirement)):
            if isinstance(prior, MetadataUsage) and prior.declared_name == VERDICT_NAME:
                model.remove(prior)
        builder.metadata(
            model,
            requirement,
            {
                "status": verdict.status,
                "actual": verdict.actual,
                "margin": verdict.margin if verdict.margin is not None else 0.0,
                "engine": run_result.engine,
                **({"timestamp": run.timestamp} if run.timestamp else {}),
            },
            name=VERDICT_NAME,
        )
        added += 1
    return added


def _is_written_result(element: object) -> bool:
    value = getattr(element, "value", None)
    source = getattr(value, "source", None)
    return isinstance(source, str) and source.startswith(_RESULT_SOURCE_PREFIX)
