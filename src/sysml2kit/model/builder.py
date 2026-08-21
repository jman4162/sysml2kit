"""Fluent authoring helpers: the API humans and agents actually type.

Each helper constructs an element, registers it in the model under the given
owner, and returns it. The raw element classes stay the interchange-faithful
layer; nothing here adds state the classes lack.
"""

from __future__ import annotations

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element, Ref
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import RequirementDefinition, RequirementUsage
from sysml2kit.model.structure import (
    AttributeDefinition,
    AttributeUsage,
    ConnectionUsage,
    Package,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
)
from sysml2kit.model.values import AttributeValue


def pkg(
    model: Model, name: str, *, owner: Element | None = None, doc: str | None = None
) -> Package:
    """Create a package."""
    return model.add(Package(declared_name=name, doc=doc), owner=owner)  # type: ignore[return-value]


def part_def(
    model: Model, name: str, *, owner: Element | None = None, doc: str | None = None
) -> PartDefinition:
    """Create a part definition."""
    return model.add(PartDefinition(declared_name=name, doc=doc), owner=owner)  # type: ignore[return-value]


def part(
    model: Model,
    name: str,
    *,
    owner: Element | None = None,
    definition: Element | None = None,
    multiplicity: str | None = None,
    doc: str | None = None,
) -> PartUsage:
    """Create a part usage, optionally typed by a part definition."""
    usage = PartUsage(
        declared_name=name,
        definition=Ref.to(definition) if definition else None,
        multiplicity=multiplicity,
        doc=doc,
    )
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def port_def(
    model: Model, name: str, *, owner: Element | None = None, doc: str | None = None
) -> PortDefinition:
    """Create a port definition."""
    return model.add(PortDefinition(declared_name=name, doc=doc), owner=owner)  # type: ignore[return-value]


def port(
    model: Model,
    name: str,
    *,
    owner: Element | None = None,
    definition: Element | None = None,
) -> PortUsage:
    """Create a port usage on a part."""
    usage = PortUsage(
        declared_name=name,
        definition=Ref.to(definition) if definition else None,
    )
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def connect(
    model: Model,
    source: Element,
    target: Element,
    *,
    owner: Element | None = None,
    name: str | None = None,
) -> ConnectionUsage:
    """Create a connection between two ports (or parts)."""
    usage = ConnectionUsage(declared_name=name, source=Ref.to(source), target=Ref.to(target))
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def attr_def(
    model: Model,
    name: str,
    *,
    owner: Element | None = None,
    unit: str | None = None,
    doc: str | None = None,
) -> AttributeDefinition:
    """Create an attribute definition, optionally with a default unit."""
    return model.add(  # type: ignore[return-value]
        AttributeDefinition(declared_name=name, unit=unit, doc=doc), owner=owner
    )


def attr(
    model: Model,
    name: str,
    value: float | str | bool | None = None,
    *,
    owner: Element | None = None,
    unit: str | None = None,
    definition: Element | None = None,
    source: str | None = None,
) -> AttributeUsage:
    """Create an attribute usage holding a value with optional unit and provenance."""
    usage = AttributeUsage(
        declared_name=name,
        definition=Ref.to(definition) if definition else None,
        value=AttributeValue(value=value, unit=unit, source=source) if value is not None else None,
    )
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def req_def(
    model: Model, name: str, *, owner: Element | None = None, doc: str | None = None
) -> RequirementDefinition:
    """Create a requirement definition."""
    return model.add(RequirementDefinition(declared_name=name, doc=doc), owner=owner)  # type: ignore[return-value]


def req(
    model: Model,
    short_name: str,
    name: str,
    *,
    owner: Element | None = None,
    text: str | None = None,
    subject: Element | None = None,
    definition: Element | None = None,
) -> RequirementUsage:
    """Create a requirement usage; ``short_name`` is the requirement id (e.g. REQ-001)."""
    usage = RequirementUsage(
        declared_short_name=short_name,
        declared_name=name,
        text=text,
        subject=Ref.to(subject) if subject else None,
        definition=Ref.to(definition) if definition else None,
    )
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def analysis_def(
    model: Model, name: str, *, owner: Element | None = None, doc: str | None = None
) -> AnalysisCaseDefinition:
    """Create an analysis case definition."""
    return model.add(AnalysisCaseDefinition(declared_name=name, doc=doc), owner=owner)  # type: ignore[return-value]


def analysis(
    model: Model,
    name: str,
    *,
    owner: Element | None = None,
    subject: Element | None = None,
    objective: str | None = None,
    definition: Element | None = None,
) -> AnalysisCaseUsage:
    """Create an analysis case usage."""
    usage = AnalysisCaseUsage(
        declared_name=name,
        subject=Ref.to(subject) if subject else None,
        objective=objective,
        definition=Ref.to(definition) if definition else None,
    )
    return model.add(usage, owner=owner)  # type: ignore[return-value]


def metadata(
    model: Model,
    annotated: Element,
    values: dict[str, str | float | int | bool],
    *,
    owner: Element | None = None,
    name: str | None = None,
) -> MetadataUsage:
    """Attach a key-value metadata annotation to an element."""
    usage = MetadataUsage(declared_name=name, annotated=Ref.to(annotated), values=dict(values))
    return model.add(usage, owner=owner if owner is not None else annotated)  # type: ignore[return-value]


def _relate(
    model: Model,
    cls: type[SatisfyRelationship | VerifyRelationship | DeriveRelationship | AllocateRelationship],
    source: Element,
    target: Element,
    owner: Element | None,
) -> Element:
    rel = cls(source=Ref.to(source), target=Ref.to(target))
    fallback = model.owner_of(source)
    return model.add(rel, owner=owner if owner is not None else fallback)


def satisfy(
    model: Model, *, source: Element, target: Element, owner: Element | None = None
) -> SatisfyRelationship:
    """Record that ``source`` (a design element) satisfies ``target`` (a requirement)."""
    return _relate(model, SatisfyRelationship, source, target, owner)  # type: ignore[return-value]


def verify(
    model: Model, *, source: Element, target: Element, owner: Element | None = None
) -> VerifyRelationship:
    """Record that ``source`` (an analysis/test) verifies ``target`` (a requirement)."""
    return _relate(model, VerifyRelationship, source, target, owner)  # type: ignore[return-value]


def derive(
    model: Model, *, source: Element, target: Element, owner: Element | None = None
) -> DeriveRelationship:
    """Record that requirement ``source`` derives from requirement ``target``."""
    return _relate(model, DeriveRelationship, source, target, owner)  # type: ignore[return-value]


def allocate(
    model: Model, *, source: Element, target: Element, owner: Element | None = None
) -> AllocateRelationship:
    """Record that ``source`` is allocated to ``target`` (a part)."""
    return _relate(model, AllocateRelationship, source, target, owner)  # type: ignore[return-value]
