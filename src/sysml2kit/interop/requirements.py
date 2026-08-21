"""Tool-agnostic requirement extraction: the ``metricKey`` convention.

A requirement usage that owns attributes named ``metricKey``, ``threshold``,
``op`` (one of ``>= <= == > <``), and optionally ``severity`` is machine-
checkable. ``extract_requirements`` turns each into a :class:`RequirementSpec`
with the threshold in both operator form (op + value) and bound form
(minimum/maximum), so downstream tools of either dialect consume it with a
small adapter: an op-form requirements engine maps ``op``/``value`` straight
through, a bound-form one takes ``minimum``/``maximum``. Adapter code lives
in the consuming packages, not here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from sysml2kit.model.container import Model
from sysml2kit.model.requirements import RequirementUsage
from sysml2kit.model.structure import AttributeUsage
from sysml2kit.query import satisfied_by, verified_by

Op = Literal[">=", "<=", "==", ">", "<"]
Severity = Literal["must", "should", "nice"]


class RequirementSpec(BaseModel):
    """One machine-checkable requirement, extracted from a model."""

    id: str
    name: str
    metric_key: str
    op: Op | None = None
    value: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    units: str | None = None
    severity: Severity = "must"
    source_element_id: str
    satisfied_by: list[str] = []
    verified_by: list[str] = []


def _owned_attribute(model: Model, req: RequirementUsage, name: str) -> AttributeUsage | None:
    for child in model.owned_by(req):
        if isinstance(child, AttributeUsage) and child.declared_name == name:
            return child
    return None


def _bounds(op: Op, value: float) -> tuple[float | None, float | None]:
    if op in (">=", ">"):
        return value, None
    if op in ("<=", "<"):
        return None, value
    return value, value  # "=="


def extract_requirements(model: Model) -> list[RequirementSpec]:
    """Extract every requirement that follows the metricKey convention."""
    specs: list[RequirementSpec] = []
    for req in model.iter_elements(kind=RequirementUsage):
        assert isinstance(req, RequirementUsage)
        metric = _owned_attribute(model, req, "metricKey")
        if metric is None or metric.value is None or not isinstance(metric.value.value, str):
            continue
        threshold = _owned_attribute(model, req, "threshold")
        op_attr = _owned_attribute(model, req, "op")
        severity_attr = _owned_attribute(model, req, "severity")

        op: Op | None = None
        value: float | None = None
        units: str | None = None
        minimum: float | None = None
        maximum: float | None = None
        if (
            threshold is not None
            and threshold.value is not None
            and isinstance(threshold.value.value, int | float)
            and op_attr is not None
            and op_attr.value is not None
            and op_attr.value.value in (">=", "<=", "==", ">", "<")
        ):
            op = op_attr.value.value  # type: ignore[assignment]
            value = float(threshold.value.value)
            units = threshold.value.unit
            assert op is not None
            minimum, maximum = _bounds(op, value)

        severity: Severity = "must"
        if severity_attr is not None and severity_attr.value is not None:
            raw = severity_attr.value.value
            if raw in ("must", "should", "nice"):
                severity = raw  # type: ignore[assignment]

        specs.append(
            RequirementSpec(
                id=req.declared_short_name or str(req.element_id),
                name=req.declared_name or "",
                metric_key=metric.value.value,
                op=op,
                value=value,
                minimum=minimum,
                maximum=maximum,
                units=units,
                severity=severity,
                source_element_id=str(req.element_id),
                satisfied_by=[model.qualified_name(el) for el in satisfied_by(model, req)],
                verified_by=[model.qualified_name(el) for el in verified_by(model, req)],
            )
        )
    return specs
