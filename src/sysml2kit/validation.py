"""Rule-based model validation.

Rules are registered in a module-level table and identified as ``S2K0NN``.
``validate(model)`` runs them all and returns issues sorted by severity.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sysml2kit.model.base import Element, OpaqueElement, Relationship
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import RequirementUsage
from sysml2kit.model.structure import AttributeUsage, Package
from sysml2kit.units import is_valid_unit

Severity = Literal["error", "warning", "info"]
_ORDER: dict[Severity, int] = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class ValidationIssue:
    """One finding from one rule against one element."""

    rule_id: str
    severity: Severity
    element_id: UUID | None
    message: str


Rule = Callable[[Model], Iterator[ValidationIssue]]
RULES: dict[str, Rule] = {}


def rule(rule_id: str) -> Callable[[Rule], Rule]:
    """Register a validation rule under an ``S2K`` id."""

    def register(fn: Rule) -> Rule:
        RULES[rule_id] = fn
        return fn

    return register


def validate(model: Model) -> list[ValidationIssue]:
    """Run every rule; issues come back sorted errors-first."""
    issues = [issue for fn in RULES.values() for issue in fn(model)]
    return sorted(issues, key=lambda i: (_ORDER[i.severity], i.rule_id))


@rule("S2K001")
def dangling_refs(model: Model) -> Iterator[ValidationIssue]:
    """error: a reference points at an element that is not in the model."""
    for eid, fieldname, missing in model.check_refs():
        yield ValidationIssue(
            "S2K001", "error", eid, f"field '{fieldname}' references missing element {missing}"
        )


@rule("S2K002")
def duplicate_short_names(model: Model) -> Iterator[ValidationIssue]:
    """error: two requirements share a declared short name (requirement id)."""
    counts = Counter(
        el.declared_short_name
        for el in model.iter_elements(kind=RequirementUsage)
        if el.declared_short_name
    )
    for short, n in counts.items():
        if n > 1:
            yield ValidationIssue(
                "S2K002", "error", None, f"requirement id '{short}' is declared {n} times"
            )


@rule("S2K003")
def sibling_name_clash(model: Model) -> Iterator[ValidationIssue]:
    """error: two named siblings clash, which also breaks stable-id hashing."""
    scopes: list[list[Element]] = [
        [model.elements[r] for r in model.roots],
        *([model.owned_by(eid) for eid in model.owned]),
    ]
    for siblings in scopes:
        counts = Counter(el.declared_name for el in siblings if el.declared_name)
        for name, n in counts.items():
            if n > 1:
                yield ValidationIssue(
                    "S2K003", "error", None, f"sibling name '{name}' is used {n} times in one scope"
                )


@rule("S2K004")
def relationship_endpoint_kinds(model: Model) -> Iterator[ValidationIssue]:
    """error: a traceability relationship points at the wrong element kind."""
    expectations: list[tuple[type[Relationship], str, bool]] = [
        (SatisfyRelationship, "target", True),
        (VerifyRelationship, "target", True),
        (DeriveRelationship, "source", True),
        (DeriveRelationship, "target", True),
        (AllocateRelationship, "source", False),
    ]
    for kind, end, must_be_requirement in expectations:
        for rel in model.relationships(kind=kind):
            ref = getattr(rel, end)
            if ref.target not in model.elements:
                continue  # S2K001 reports it
            element = model.resolve(ref)
            is_req = isinstance(element, RequirementUsage)
            if must_be_requirement and not is_req:
                yield ValidationIssue(
                    "S2K004",
                    "error",
                    rel.element_id,
                    f"{type(rel).__name__} {end} must be a requirement, "
                    f"got {type(element).__name__} '{element.label}'",
                )


@rule("S2K005")
def unresolvable_definition(model: Model) -> Iterator[ValidationIssue]:
    """error: a usage's definition ref resolves to nothing.

    A subset of S2K001 kept separate because typing errors deserve their own id.
    """
    for el in model.iter_elements():
        definition = getattr(el, "definition", None)
        if definition is not None and definition.target not in model.elements:
            yield ValidationIssue(
                "S2K005", "error", el.element_id, f"'{el.label}' is typed by a missing definition"
            )


@rule("S2K006")
def unparseable_units(model: Model) -> Iterator[ValidationIssue]:
    """warning: an attribute value carries a unit string pint cannot parse."""
    for el in model.iter_elements(kind=AttributeUsage):
        assert isinstance(el, AttributeUsage)
        if el.value is not None and el.value.unit and not is_valid_unit(el.value.unit):
            yield ValidationIssue(
                "S2K006",
                "warning",
                el.element_id,
                f"attribute '{el.label}' has unparseable unit '{el.value.unit}'",
            )


@rule("S2K007")
def requirement_without_subject(model: Model) -> Iterator[ValidationIssue]:
    """warning: a requirement names no subject and nothing satisfies it."""
    for el in model.iter_elements(kind=RequirementUsage):
        assert isinstance(el, RequirementUsage)
        has_satisfier = bool(model.relationships(kind=SatisfyRelationship, target=el))
        if el.subject is None and not has_satisfier:
            yield ValidationIssue(
                "S2K007",
                "warning",
                el.element_id,
                f"requirement '{el.label}' has no subject and no satisfier",
            )


@rule("S2K008")
def empty_package(model: Model) -> Iterator[ValidationIssue]:
    """info: a package owns nothing."""
    for el in model.iter_elements(kind=Package):
        if not model.owned_by(el):
            yield ValidationIssue("S2K008", "info", el.element_id, f"package '{el.label}' is empty")


@rule("S2K009")
def opaque_share(model: Model) -> Iterator[ValidationIssue]:
    """info: opaque elements are present (fine, but worth knowing)."""
    opaque = sum(1 for el in model.iter_elements(kind=OpaqueElement))
    if opaque:
        yield ValidationIssue(
            "S2K009", "info", None, f"{opaque} element(s) outside the pragmatic profile"
        )


@rule("S2K010")
def fidelity_ladder_shape(model: Model) -> Iterator[ValidationIssue]:
    """error: two bindings on one analysis share a fidelity label; warning: mixed labeling."""
    per_analysis: dict[UUID, list[str | None]] = {}
    for el in model.iter_elements(kind=MetadataUsage):
        assert isinstance(el, MetadataUsage)
        from sysml2kit.verify.binding import is_binding

        if not is_binding(model, el) or el.annotated is None:
            continue
        label = el.values.get("fidelity")
        per_analysis.setdefault(el.annotated.target, []).append(
            str(label) if label is not None else None
        )
    for analysis_id, labels in per_analysis.items():
        if len(labels) < 2:
            continue
        named = [label for label in labels if label is not None]
        duplicates = {label for label in named if named.count(label) > 1}
        if duplicates:
            yield ValidationIssue(
                "S2K010",
                "error",
                analysis_id,
                f"multiple bindings share fidelity label(s) {sorted(duplicates)}",
            )
        if named and len(named) != len(labels):
            yield ValidationIssue(
                "S2K010",
                "warning",
                analysis_id,
                "some sibling bindings declare a fidelity label and some do not",
            )
