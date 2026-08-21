"""Run bound analyses and check requirements against their metrics.

An analysis may carry several bindings at different fidelities (the reserved
``fidelity``/``costSeconds`` metadata keys); the runner's policy decides
which rungs execute:

- ``all`` (default): every binding runs; every requirement gets a verdict
  per rung that produced its metric, with the cross-rung ``spread`` as an
  error bar.
- ``cheapest``: only the lowest-cost rung of each analysis runs.
- ``escalate``: cheapest rungs run first, then the remaining ``budget_s``
  is spent escalating the requirements with the thinnest margins to the
  next rung, thinnest first.

Engine exceptions are captured per rung, never raised. ``apply_results``
writes the highest-fidelity verdict per requirement back into the model
with provenance, idempotently.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import BaseModel

import sysml2kit
from sysml2kit.interop.requirements import Op, RequirementSpec, Severity, extract_requirements
from sysml2kit.model import builder
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.verify.binding import VerificationBinding, build_payload, extract_bindings
from sysml2kit.verify.engines import EngineRegistry

logger = logging.getLogger(__name__)

VERDICT_NAME = "verificationVerdict"
_RESULT_SOURCE_PREFIX = "sysml2kit.verify"

Policy = Literal["all", "cheapest", "escalate"]


class AnalysisResult(BaseModel):
    """Metrics (or the captured error) from one rung of one analysis."""

    analysis: str
    engine: str
    key: str
    fidelity: str | None = None
    config_ref: str | None = None
    metrics: dict[str, float | int | str | bool | None] = {}
    error: str | None = None
    measured_s: float | None = None


class RequirementVerdict(BaseModel):
    """One requirement checked against one rung's metrics."""

    requirement_id: str
    metric_key: str
    analysis: str
    engine: str | None = None
    fidelity: str | None = None
    op: Op | None = None
    threshold: float | None = None
    units: str | None = None
    actual: float | None = None
    margin: float | None = None
    status: Literal["pass", "fail", "unknown"]
    severity: Severity = "must"
    cost_s: float | None = None
    escalated_from: str | None = None
    spread: float | None = None


class VerificationRun(BaseModel):
    """The full result of one verification run."""

    model_path: str | None = None
    timestamp: str | None = None
    sysml2kit_version: str = sysml2kit.__version__
    policy: Policy = "all"
    budget_s: float | None = None
    engine_versions: dict[str, str] = {}
    seconds_by_fidelity: dict[str, float] = {}
    analyses: list[AnalysisResult] = []
    requirements: list[RequirementVerdict] = []

    @property
    def passed(self) -> bool:
        """True when no executed rung errored and every must-verdict passes."""
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
        engine=result.engine,
        fidelity=result.fidelity,
        op=spec.op,
        threshold=spec.value,
        units=spec.units,
        severity=spec.severity,
        status="unknown",
        cost_s=result.measured_s,
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


def _cost_order(binding: VerificationBinding) -> float:
    return binding.cost_s if binding.cost_s is not None else 0.0


def _fidelity_label(item: VerificationBinding | AnalysisResult) -> str:
    return item.fidelity or item.engine


def run_verification(
    model: Model,
    *,
    model_path: Path | None = None,
    registry: EngineRegistry | None = None,
    timestamp: str | None = None,
    analyses: Sequence[str] | None = None,
    policy: Policy = "all",
    budget_s: float | None = None,
    fidelities: Sequence[str] | None = None,
) -> VerificationRun:
    """Execute bound analyses per the policy and check their requirements.

    ``analyses`` filters bindings by analysis qualified name; ``fidelities``
    by rung label. ``timestamp`` is caller-supplied so the library stays
    deterministic.
    """
    if registry is None:
        registry = EngineRegistry.discover()
    base_dir = model_path.parent if model_path is not None else Path.cwd()

    bindings = extract_bindings(model)
    if analyses is not None:
        wanted = set(analyses)
        bindings = [b for b in bindings if b.analysis in wanted]
    if fidelities is not None:
        wanted_labels = set(fidelities)
        bindings = [b for b in bindings if _fidelity_label(b) in wanted_labels]

    ladder: dict[str, list[VerificationBinding]] = {}
    for binding in bindings:
        ladder.setdefault(binding.analysis, []).append(binding)
    for rungs in ladder.values():
        rungs.sort(key=_cost_order)

    specs = extract_requirements(model)
    run = VerificationRun(
        model_path=str(model_path) if model_path else None,
        timestamp=timestamp,
        policy=policy,
        budget_s=budget_s,
    )

    if policy == "all":
        _execute([rung for rungs in ladder.values() for rung in rungs], registry, base_dir, run)
        run.requirements = _verdicts_for(specs, run.analyses, {})
    elif policy == "cheapest":
        _execute([rungs[0] for rungs in ladder.values() if rungs], registry, base_dir, run)
        run.requirements = _verdicts_for(specs, run.analyses, {})
    else:
        _run_escalation(ladder, specs, registry, base_dir, run, budget_s)

    _annotate_spread(run.requirements)
    return run


def _execute(
    bindings: Sequence[VerificationBinding],
    registry: EngineRegistry,
    base_dir: Path,
    run: VerificationRun,
) -> list[AnalysisResult]:
    executed: list[AnalysisResult] = []
    for binding in bindings:
        result = _run_binding(binding, registry, base_dir, run.engine_versions)
        run.analyses.append(result)
        executed.append(result)
        if result.measured_s is not None:
            label = _fidelity_label(result)
            run.seconds_by_fidelity[label] = (
                run.seconds_by_fidelity.get(label, 0.0) + result.measured_s
            )
    return executed


def _verdicts_for(
    specs: Sequence[RequirementSpec],
    results: Sequence[AnalysisResult],
    base_fidelity: dict[str, str],
) -> list[RequirementVerdict]:
    verdicts: list[RequirementVerdict] = []
    for spec in specs:
        for result in results:
            if result.analysis in spec.verified_by:
                verdict = _verdict(spec, result)
                base = base_fidelity.get(result.analysis)
                if base is not None and _fidelity_label(result) != base:
                    verdict = verdict.model_copy(update={"escalated_from": base})
                verdicts.append(verdict)
    return verdicts


def _run_escalation(
    ladder: dict[str, list[VerificationBinding]],
    specs: Sequence[RequirementSpec],
    registry: EngineRegistry,
    base_dir: Path,
    run: VerificationRun,
    budget_s: float | None,
) -> None:
    first_pass = _execute([rungs[0] for rungs in ladder.values() if rungs], registry, base_dir, run)
    base_fidelity = {r.analysis: _fidelity_label(r) for r in first_pass}
    first_verdicts = _verdicts_for(specs, first_pass, {})

    spent = sum(r.measured_s or 0.0 for r in first_pass)
    remaining = None if budget_s is None else budget_s - spent

    def thinness(verdict: RequirementVerdict) -> float:
        if verdict.margin is None or verdict.threshold in (None, 0):
            return float("inf")
        assert verdict.threshold is not None
        return abs(verdict.margin) / abs(verdict.threshold)

    candidates = sorted(
        (v for v in first_verdicts if v.severity == "must" and v.margin is not None),
        key=thinness,
    )
    executed_keys = {r.key for r in run.analyses}
    for verdict in candidates:
        rungs = ladder.get(verdict.analysis, [])
        next_rungs = [r for r in rungs if r.key not in executed_keys]
        if not next_rungs:
            continue
        rung = next_rungs[0]
        declared = rung.cost_s if rung.cost_s is not None else 0.0
        if remaining is not None and declared > remaining:
            logger.info(
                "budget exhausted; not escalating %s to %s",
                verdict.requirement_id,
                _fidelity_label(rung),
            )
            continue
        (result,) = _execute([rung], registry, base_dir, run)
        executed_keys.add(result.key)
        if remaining is not None:
            remaining -= result.measured_s or 0.0

    run.requirements = _verdicts_for(specs, run.analyses, base_fidelity)


def _annotate_spread(verdicts: list[RequirementVerdict]) -> None:
    spreads: dict[str, float] = {}
    actuals_by_requirement: dict[str, list[float]] = {}
    for verdict in verdicts:
        if verdict.actual is not None:
            actuals_by_requirement.setdefault(verdict.requirement_id, []).append(verdict.actual)
    for requirement_id, actuals in actuals_by_requirement.items():
        if len(actuals) >= 2:
            spreads[requirement_id] = max(actuals) - min(actuals)
    for index, verdict in enumerate(verdicts):
        spread = spreads.get(verdict.requirement_id)
        if spread is not None:
            verdicts[index] = verdict.model_copy(update={"spread": spread})


def _run_binding(
    binding: VerificationBinding,
    registry: EngineRegistry,
    base_dir: Path,
    engine_versions: dict[str, str],
) -> AnalysisResult:
    start = perf_counter()
    try:
        engine = registry.get(binding.engine)
        engine_versions.setdefault(binding.engine, registry.version_of(binding.engine))
        payload = build_payload(binding, base_dir)
        metrics = dict(engine(payload))
    except Exception as exc:  # noqa: BLE001 - engines are third-party code; capture, don't crash
        return AnalysisResult(
            analysis=binding.analysis,
            engine=binding.engine,
            key=binding.key,
            fidelity=binding.fidelity,
            config_ref=binding.config_ref,
            error=f"{type(exc).__name__}: {exc}",
            measured_s=perf_counter() - start,
        )
    return AnalysisResult(
        analysis=binding.analysis,
        engine=binding.engine,
        key=binding.key,
        fidelity=binding.fidelity,
        config_ref=binding.config_ref,
        metrics=metrics,
        measured_s=perf_counter() - start,
    )


def _best_verdicts(run: VerificationRun) -> dict[str, RequirementVerdict]:
    """Highest-cost (highest-fidelity) checked verdict per requirement."""
    cost_by_key = {r.key: r.measured_s or 0.0 for r in run.analyses}
    best: dict[str, RequirementVerdict] = {}
    for verdict in run.requirements:
        if verdict.status == "unknown" or verdict.actual is None:
            continue
        key = f"{verdict.analysis}#{verdict.fidelity or verdict.engine}"
        current = best.get(verdict.requirement_id)
        if current is None:
            best[verdict.requirement_id] = verdict
            continue
        current_key = f"{current.analysis}#{current.fidelity or current.engine}"
        if cost_by_key.get(key, 0.0) >= cost_by_key.get(current_key, 0.0):
            best[verdict.requirement_id] = verdict
    return best


def apply_results(model: Model, run: VerificationRun) -> int:
    """Write run results back into the model; returns the element count added.

    The highest-fidelity checked verdict per requirement is recorded: each
    metric becomes an attribute on its analysis (with a provenance
    ``source``), each verdict a ``verificationVerdict`` metadata on its
    requirement. Idempotent: prior results of the same names are removed.
    """
    added = 0
    analyses = {model.qualified_name(el): el for el in model.elements.values()}
    for verdict in _best_verdicts(run).values():
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
        if analysis is None or requirement is None or verdict.actual is None:
            continue
        engine = verdict.engine or "unknown"
        source = (
            f"{_RESULT_SOURCE_PREFIX} {verdict.analysis} "
            f"{engine}=={run.engine_versions.get(engine, 'unknown')}"
            + (f" fidelity={verdict.fidelity}" if verdict.fidelity else "")
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
                "engine": engine,
                **({"fidelity": verdict.fidelity} if verdict.fidelity else {}),
                **({"timestamp": run.timestamp} if run.timestamp else {}),
            },
            owner=requirement,
            name=VERDICT_NAME,
        )
        added += 1
    return added


def _is_written_result(element: object) -> bool:
    value = getattr(element, "value", None)
    source = getattr(value, "source", None)
    return isinstance(source, str) and source.startswith(_RESULT_SOURCE_PREFIX)
