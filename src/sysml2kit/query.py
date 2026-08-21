"""Traceability queries over a Model.

These answer the questions a requirements-driven workflow actually asks:
which requirements are unsatisfied or unverified, what is allocated where,
and how do requirements trace to parts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sysml2kit.model.base import Element
from sysml2kit.model.container import Model
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import RequirementUsage
from sysml2kit.model.structure import PartUsage


def requirements_in(model: Model, scope: Element | None = None) -> list[RequirementUsage]:
    """Return requirement usages, optionally only those under a scope element."""
    if scope is None:
        return list(model.iter_elements(kind=RequirementUsage))  # type: ignore[arg-type]
    out: list[RequirementUsage] = []
    stack = list(model.owned_by(scope))
    while stack:
        el = stack.pop()
        if isinstance(el, RequirementUsage):
            out.append(el)
        stack.extend(model.owned_by(el))
    return out


def parts_of(model: Model, scope: Element | None = None) -> list[PartUsage]:
    """Return part usages, optionally only those under a scope element."""
    if scope is None:
        return list(model.iter_elements(kind=PartUsage))  # type: ignore[arg-type]
    out: list[PartUsage] = []
    stack = list(model.owned_by(scope))
    while stack:
        el = stack.pop()
        if isinstance(el, PartUsage):
            out.append(el)
        stack.extend(model.owned_by(el))
    return out


def satisfied_by(model: Model, requirement: RequirementUsage) -> list[Element]:
    """Return the elements recorded as satisfying this requirement."""
    rels = model.relationships(kind=SatisfyRelationship, target=requirement)
    return [model.resolve(rel.source) for rel in rels]


def verified_by(model: Model, requirement: RequirementUsage) -> list[Element]:
    """Return the analyses/tests recorded as verifying this requirement."""
    rels = model.relationships(kind=VerifyRelationship, target=requirement)
    return [model.resolve(rel.source) for rel in rels]


def derived_from(model: Model, requirement: RequirementUsage) -> list[RequirementUsage]:
    """Return the requirements this one derives from."""
    rels = model.relationships(kind=DeriveRelationship, source=requirement)
    return [el for rel in rels if isinstance(el := model.resolve(rel.target), RequirementUsage)]


def unsatisfied_requirements(model: Model) -> list[RequirementUsage]:
    """Return requirements with no incoming satisfy relationship."""
    return [r for r in requirements_in(model) if not satisfied_by(model, r)]


def unverified_requirements(model: Model) -> list[RequirementUsage]:
    """Return requirements with no incoming verify relationship."""
    return [r for r in requirements_in(model) if not verified_by(model, r)]


def allocation_table(model: Model) -> list[tuple[Element, Element]]:
    """Return (allocated element, part) pairs for every allocate relationship."""
    return [
        (model.resolve(rel.source), model.resolve(rel.target))
        for rel in model.relationships(kind=AllocateRelationship)
    ]


@dataclass
class TraceMatrix:
    """Requirement-by-part grid of satisfy/verify/allocate marks."""

    requirements: list[RequirementUsage] = field(default_factory=list)
    parts: list[PartUsage] = field(default_factory=list)
    #: (requirement_id, part_id) -> set of mark strings ("satisfy", "allocate").
    cells: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    def render(self) -> str:
        """Render as a fixed-width text table."""
        if not self.requirements:
            return "(no requirements)"
        req_labels = [r.declared_short_name or r.label for r in self.requirements]
        part_labels = [p.label for p in self.parts]
        width = max((len(label) for label in req_labels), default=8) + 2
        col = max((len(label) for label in part_labels), default=8) + 2
        header = " " * width + "".join(label.ljust(col) for label in part_labels)
        lines = [header]
        for r, rl in zip(self.requirements, req_labels, strict=True):
            row = rl.ljust(width)
            for p in self.parts:
                marks = self.cells.get((str(r.element_id), str(p.element_id)), set())
                cell = ",".join(sorted(m[0].upper() for m in marks)) if marks else "."
                row += cell.ljust(col)
            lines.append(row)
        lines.append("(S=satisfy, A=allocate; '.'=no link)")
        return "\n".join(lines)


def trace_matrix(model: Model) -> TraceMatrix:
    """Build the requirement-to-part traceability matrix."""
    matrix = TraceMatrix(requirements=requirements_in(model), parts=parts_of(model))
    for rel in model.relationships(kind=SatisfyRelationship):
        source, target = model.resolve(rel.source), model.resolve(rel.target)
        if isinstance(target, RequirementUsage) and isinstance(source, PartUsage):
            matrix.cells.setdefault((str(target.element_id), str(source.element_id)), set()).add(
                "satisfy"
            )
    for rel in model.relationships(kind=AllocateRelationship):
        source, target = model.resolve(rel.source), model.resolve(rel.target)
        if isinstance(source, RequirementUsage) and isinstance(target, PartUsage):
            matrix.cells.setdefault((str(source.element_id), str(target.element_id)), set()).add(
                "allocate"
            )
    return matrix
