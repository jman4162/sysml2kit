"""Structural elements: packages, parts, ports, interfaces, connections."""

from __future__ import annotations

from pydantic import Field

from sysml2kit.model.base import Element, Ref
from sysml2kit.model.values import AttributeValue


class Package(Element):
    """A namespace for other elements; maps to a top-level ``.sysml`` file."""

    imports: list[str] = Field(default_factory=list)


class PartDefinition(Element):
    """A reusable definition of a system component kind."""


class PartUsage(Element):
    """A component occurrence, optionally typed by a :class:`PartDefinition`."""

    definition: Ref | None = None
    multiplicity: str | None = None


class PortDefinition(Element):
    """A reusable definition of an interaction point kind."""


class PortUsage(Element):
    """A port occurrence on a part, optionally typed by a :class:`PortDefinition`."""

    definition: Ref | None = None


class InterfaceDefinition(Element):
    """A definition of how two ports connect."""


class ConnectionUsage(Element):
    """A connection between two port (or part) ends."""

    definition: Ref | None = None
    source: Ref | None = None
    target: Ref | None = None


class AttributeDefinition(Element):
    """A reusable definition of a value kind, e.g. a quantity with a unit."""

    unit: str | None = None


class AttributeUsage(Element):
    """A value occurrence, optionally typed and optionally holding a value."""

    definition: Ref | None = None
    value: AttributeValue | None = None
